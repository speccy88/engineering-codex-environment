#!/usr/bin/env python3
"""Export a Fritzing project with the actual engine in a fresh private directory.

This validates file structure and native export diagnostics, not electrical design.
"""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import sqlite3
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def checked_xml(data):
    if b"<!ENTITY" in data.upper():
        raise ValueError("XML entity declarations are not supported")
    return ET.fromstring(data)


def inspect_project(source):
    """Reject missing modules before Fritzing silently omits them from its render."""
    data = Path(os.environ.get("FRITZING_DATA_DIR", ROOT / ".local/sysroot/usr/share/fritzing"))
    parts = Path(os.environ.get("FRITZING_PARTS_DIR", data / "parts"))
    database = parts / "parts.db"
    if not database.is_file():
        database = parts.parent / "parts.db.distrib"
    if not database.is_file():
        raise ValueError("Missing parts database; run setup/install-fritzing.sh first")
    with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
        available = {row[0] for row in connection.execute("SELECT moduleID FROM parts")}
    # The packaged DB can omit obsolete/custom library parts that native Fritzing
    # still loads from disk. Inspect definitions as well as the DB index.
    for category in ("core", "obsolete", "contrib", "user"):
        for definition in (parts / category).glob("*.fzp"):
            try:
                available.add(checked_xml(definition.read_bytes()).get("moduleId", ""))
            except (OSError, ET.ParseError, ValueError):
                continue
    bundled = set()
    if source.suffix.lower() == ".fzz":
        with zipfile.ZipFile(source) as archive:
            entries = archive.infolist()
            if sum(item.file_size for item in entries) > 100 * 1024 * 1024:
                raise ValueError("FZZ uncompressed contents exceed 100 MiB")
            names = [item.filename for item in entries]
            if len(names) != len(set(names)):
                raise ValueError("FZZ contains duplicate member names")
            for name in names:
                path = PurePosixPath(name)
                if path.is_absolute() or len(path.parts) != 1 or ".." in path.parts or "\\" in name:
                    raise ValueError(f"Unsafe FZZ archive member: {name}")
            sketches = [name for name in names if name.lower().endswith(".fz")]
            if len(sketches) != 1:
                raise ValueError("FZZ must contain exactly one .fz sketch")
            sketch = checked_xml(archive.read(sketches[0]))
            for name in names:
                if not name.lower().endswith(".fzp"):
                    continue
                if not name.startswith("part."):
                    raise ValueError(f"Exporter requires canonical part.*.fzp bundle members: {name}")
                part = checked_xml(archive.read(name))
                module_id = part.get("moduleId")
                if not module_id or module_id in bundled:
                    raise ValueError(f"Missing or duplicate custom moduleId: {name}")
                bundled.add(module_id)
                for layers in part.findall("./views/*/layers"):
                    image = layers.get("image", "")
                    svg_name = "svg." + image.replace("/", ".")
                    if svg_name not in names:
                        raise ValueError(f"Custom part {name} is missing bundled SVG {svg_name}")
                    svg = checked_xml(archive.read(svg_name))
                    if svg.tag.rsplit("}", 1)[-1] != "svg":
                        raise ValueError(f"Custom part image is not SVG: {svg_name}")
    else:
        sketch = checked_xml(source.read_bytes())
    available |= bundled
    references = {node.get("moduleIdRef", "") for node in sketch.findall("./instances/instance")}
    if not references:
        raise ValueError("Sketch has no part instances")
    # Recognize only source-defined parametric families; Fritzing still needs to
    # construct them successfully. They are explicitly deferred, never reported
    # as already resolved. Other unknown modules must be bundled in the FZZ.
    factory = re.compile(r"^(?:generic_ic_dip_\d+_\d+mil|generic_sip_\d+_\d+mil|mystery_part_(?:sip|dip)_\d+_\d+mil|generic_(?:male|female|rounded_female|shrouded)_pin_header_\d+_\d+mil|screw_terminal_\d+_\d+mil|\d+\.\d+(?:Perfboard|Stripboard|Stripboard2)ModuleID)$")
    deferred = {module for module in references - available if factory.fullmatch(module)}
    missing = sorted(references - available - deferred)
    if missing:
        raise ValueError("Unresolved parts; include their .fzp/SVG files in the .fzz: " + ", ".join(missing))
    return {"module_count": len(references), "bundled_module_count": len(bundled), "factory_modules_deferred_to_native": sorted(deferred)}


def run_logged(command, output, label, timeout, evidence):
    log_path = output / f"{label}.log"
    with log_path.open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        timed_out = False
        try:
            returncode = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            returncode = 124
    evidence.append({"command": command, "exit_code": returncode, "timed_out": timed_out, "log": log_path.name})
    if returncode:
        raise RuntimeError(f"{label} failed with exit code {returncode}; see {log_path}")
    return log_path.read_text(errors="replace")


def validate_svg(path):
    tree = checked_xml(path.read_bytes())
    if tree.tag.rsplit("}", 1)[-1] != "svg":
        raise ValueError(f"Not an SVG: {path}")
    viewbox = tree.get("viewBox")
    if viewbox:
        dimensions = [float(x) for x in re.split(r"[ ,]+", viewbox.strip())]
        if len(dimensions) != 4 or not all(math.isfinite(x) for x in dimensions) or min(dimensions[2:]) <= 0:
            raise ValueError(f"Invalid SVG viewBox: {path}")
    else:
        for key in ("width", "height"):
            value = re.match(r"[\d.]+", tree.get(key, ""))
            if not value or float(value.group()) <= 0:
                raise ValueError(f"Missing SVG dimensions: {path}")
    drawable = {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "text", "image", "use"}
    if not any(node.tag.rsplit("}", 1)[-1] in drawable for node in tree.iter()):
        raise ValueError(f"Empty SVG: {path}")


def read_ipc_nets(path):
    """Read upstream IPC-D-356A fixed columns; return primary pin membership."""
    text = path.read_text()
    if "IPC-D-356A" not in text or not text.rstrip().endswith("999"):
        raise ValueError(f"Invalid IPC-D-356A header/terminator: {path.name}")
    nets = {}
    for line in text.splitlines():
        if line[:3] not in {"317", "327", "307"}:
            continue
        if len(line) < 57 or line[26] != "-":
            raise ValueError(f"Malformed IPC test record: {path.name}")
        net, reference, pin = line[3:17].strip(), line[20:26].strip(), line[27:31].strip()
        if not net or not reference or not pin:
            raise ValueError(f"Missing IPC net/reference/pin: {path.name}")
        nets.setdefault(net, set()).add(reference + "." + pin)
    if not nets:
        raise ValueError(f"IPC netlist has no electrical test records: {path.name}")
    return {net: sorted(pins) for net, pins in sorted(nets.items())}


def stage_project(source, output):
    if source.suffix.lower() == ".fzz":
        copied = output / (source.stem + ".fzz")
        shutil.copy2(source, copied)
        return copied
    # Fritzing 1.0.1's --all replaces '.fzz' in filenames when writing IPC.
    # Normalize plain XML to an archive, so --all cannot overwrite the staged FZ.
    originals = output / "source"
    originals.mkdir()
    shutil.copy2(source, originals / source.name)
    copied = output / (source.stem + ".fzz")
    with zipfile.ZipFile(copied, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(source, source.name)
    return copied


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--format", choices=("svg", "gerber", "all"), default="all")
    parser.add_argument("--png", action="store_true", help="Also rasterize native SVG exports with QtSvg")
    parser.add_argument("--timeout", type=int, default=120, help="Maximum seconds per native command")
    args = parser.parse_args()
    source = args.project.resolve()
    output = args.output.resolve()
    if not source.is_file() or source.suffix.lower() not in {".fz", ".fzz"}:
        parser.error("project must be an existing .fz or .fzz file")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        parser.error("--output must be a new or empty directory (stale exports are never reused)")
    if args.png and args.format == "gerber":
        parser.error("--png requires SVG export")
    output.mkdir(parents=True, exist_ok=True)
    report = {"status": "failed", "source": str(source), "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "native_drc": "not_run_no_supported_batch_command", "manufacturing_ready": False,
              "scope": "native export and file integrity only", "network": "denied_by_seccomp", "commands": [], "outputs": []}
    try:
        report["project"] = inspect_project(source)
        copied = stage_project(source, output)
        report["staged_project"] = copied.name
        launcher = str(ROOT / "scripts/run-fritzing.sh")
        report["version"] = run_logged([launcher, "--version"], output, "version", args.timeout, report["commands"]).strip()
        services = ("svg", "gerber") if args.format == "all" else (args.format,)
        for service in services:
            # Fritzing 1.0.1 --all exports fabrication, BOM and IPC, but not SVG.
            native_service = "all" if service == "gerber" and args.format == "all" else service
            log = run_logged([launcher, "--" + native_service, str(output)], output, service, args.timeout, report["commands"])
            if native_service == "all":
                # Fritzing can infer custom through-hole parts as SMT here.
                # Omit that unvalidated assembly output rather than hand it out.
                report["skipped_unvalidated"] = []
                for placement in output.glob("*_pnp.xy"):
                    report["skipped_unvalidated"].append({"file": placement.name, "reason": "Native mounting-type inference for custom parts is not validated; file omitted"})
                    placement.unlink()
            # Upstream creates a separate schematicText layer (view2, layer10)
            # without electrical connectors; that exact diagnostic is benign.
            errors = [line for line in log.splitlines()
                      if re.search(r"svgidlayer fail|missing renderer for|Unable to (?:load|unzip|open|export)|svg matching fz path .* not found", line, re.I)
                      and not re.search(r"svgidlayer fail .* vid:2 vlid:10(?: |$)", line)]
            if errors:
                report["native_errors"] = errors
                raise RuntimeError(f"Native {service} reported invalid parts or failed operations; see {service}.log")
        stem = source.stem
        if "svg" in services:
            for view in ("breadboard", "schematic", "pcb"):
                path = output / f"{stem}_{view}.svg"
                if not path.is_file():
                    raise ValueError(f"Native renderer did not produce {path.name}")
                validate_svg(path)
                if args.png:
                    png = path.with_suffix(".png")
                    run_logged(["/usr/bin/python3", str(ROOT / "scripts/fritzing-offline.py"), "/usr/bin/python3", str(ROOT / "scripts/fritzing-rasterize.py"), str(path), str(png)], output, f"png-{view}", args.timeout, report["commands"])
                    if not png.is_file() or png.stat().st_size < 100:
                        raise ValueError(f"Empty PNG: {png.name}")
        if "gerber" in services:
            for suffix in ("_contour.gm1", "_drill.txt"):
                path = output / (stem + suffix)
                if not path.is_file() or path.stat().st_size < 20:
                    raise ValueError(f"Native Gerber export is missing or empty: {path.name}")
                content = path.read_text(errors="replace")
                expected = "M48" if suffix.endswith(".txt") else "%FS"
                if expected not in content:
                    raise ValueError(f"Unexpected fabrication file contents: {path.name}")
                if suffix.endswith(".txt"):
                    holes = re.findall(r"^X[+-]?[\d.]+Y[+-]?[\d.]+", content, re.M)
                    if "M30" not in content or (holes and not re.search(r"^T\d+C[\d.]+", content, re.M)):
                        raise ValueError(f"Drill file lacks tool records or terminator: {path.name}")
                    report["drill_coordinate_count"] = len(holes)
                elif "M02*" not in content or not re.search(r"D0?[13]\*", content):
                    raise ValueError(f"Gerber lacks draw/flash records or terminator: {path.name}")
            copper = []
            for suffix in ("_copperBottom.gbl", "_copperTop.gtl"):
                path = output / (stem + suffix)
                if path.is_file():
                    content = path.read_text(errors="replace")
                    if "%FS" not in content or "M02*" not in content:
                        raise ValueError(f"Invalid copper Gerber: {path.name}")
                    if re.search(r"D0?[13]\*", content):
                        copper.append(path.name)
            if not copper:
                raise ValueError("Native Gerber export has no copper draw/flash records on either layer")
            report["copper_layers_with_geometry"] = copper
        if args.format == "all":
            ipc = output / (stem + ".ipc")
            report["native_ipc_nets"] = read_ipc_nets(ipc)
            bom = output / (stem + "_bom.csv")
            with bom.open(newline="") as stream:
                rows = list(csv.reader(stream, delimiter=";"))
            if not rows or rows[0][:2] != ["Label", "Part Type"] or len(rows) < 2:
                raise ValueError("Native BOM has no component records")
        for path in sorted(output.iterdir()):
            if path.suffix in {".svg", ".png", ".gbl", ".gtl", ".gto", ".gbo", ".gts", ".gbs", ".gm1", ".ipc", ".csv"} or path.name.endswith("_drill.txt"):
                report["outputs"].append({"file": path.name, "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        report["status"] = "passed"
    except (OSError, ValueError, RuntimeError, sqlite3.Error, zipfile.BadZipFile, ET.ParseError) as error:
        report["error"] = str(error)
        print(f"Fritzing export failed: {error}", file=sys.stderr)
    finally:
        (output / "export-report.json").write_text(json.dumps(report, indent=2) + "\n")
    if report["status"] == "passed":
        print(f"Native Fritzing exports: {output}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
