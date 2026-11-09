#!/usr/bin/python3
"""Generate and check an editable KiCad 9 resistor divider fixture.

This optional test fixture uses official installed symbol libraries and checks the
exported XML netlist against the intended circuit; zero ERC alone is insufficient.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAMESPACE = uuid.UUID("df0ae8d5-ea79-4acc-b937-cdd0fc2fb4ef")


def uid(name: str) -> str:
    return str(uuid.uuid5(NAMESPACE, name))


def extract_symbol(library: str, name: str) -> str:
    source = Path("/usr/share/kicad/symbols", library + ".kicad_sym").read_text()
    needle = f'(symbol "{name}"'
    start = source.index(needle)
    depth = 0
    quoted = escaped = False
    for index in range(start, len(source)):
        char = source[index]
        if escaped:
            escaped = False
        elif quoted and char == "\\":
            escaped = True
        elif char == '"':
            quoted = not quoted
        elif not quoted:
            depth += (char == "(") - (char == ")")
            if depth == 0:
                return source[start : index + 1].replace(
                    needle, f'(symbol "{library}:{name}"', 1
                )
    raise ValueError(f"Unbalanced symbol {library}:{name}")


def prop(name: str, value: str, x: float, y: float, hidden: bool = False) -> str:
    return f'(property "{name}" "{value}" (at {x:g} {y:g} 0) (effects (font (size 1.27 1.27)){" (hide yes)" if hidden else ""}))'


def component(
    ref: str,
    libid: str,
    value: str,
    footprint: str,
    x: float,
    y: float,
    pins: int,
    project: str,
) -> str:
    properties = "\n".join(
        [
            prop("Reference", ref, x + 4, y - 1.5),
            prop("Value", value, x + 4, y + 1.5),
            prop("Footprint", footprint, x, y, True),
            prop("Datasheet", "~", x, y, True),
        ]
    )
    pin_ids = "\n".join(
        f'(pin "{p}" (uuid "{uid(ref + str(p))}"))' for p in range(1, pins + 1)
    )
    return f'''(symbol (lib_id "{libid}") (at {x:g} {y:g} 0) (unit 1)
    (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)
    (uuid "{uid(ref)}") {properties} {pin_ids}
    (instances (project "{project}" (path "/{uid("sheet")}" (reference "{ref}") (unit 1)))))'''


def wire(a: tuple[float, float], b: tuple[float, float], name: str) -> str:
    return f'(wire (pts (xy {a[0]:g} {a[1]:g}) (xy {b[0]:g} {b[1]:g})) (stroke (width 0) (type default)) (uuid "{uid(name)}"))'


def label(net: str, x: float, y: float, name: str) -> str:
    return f'(label "{net}" (at {x:g} {y:g} 0) (effects (font (size 1.27 1.27)) (justify left bottom)) (uuid "{uid(name)}"))'


def generate(output: Path) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    project = "divider"
    parts = [
        f'''(kicad_sch (version 20250114) (generator "engineering-workbench")
    (uuid "{uid("sheet")}") (paper "A4")
    (title_block (title "5 V resistor divider; VIN=5 V, VOUT=2.5 V unloaded") (rev "1"))
    (lib_symbols {extract_symbol("Device", "R")} {extract_symbol("Connector_Generic", "Conn_01x03")})'''
    ]
    for ref, y in [("R1", 60.96), ("R2", 86.36)]:
        parts.append(
            component(
                ref,
                "Device:R",
                "10k",
                "Resistor_SMD:R_0805_2012Metric",
                101.6,
                y,
                2,
                project,
            )
        )
    parts.append(
        component(
            "J1",
            "Connector_Generic:Conn_01x03",
            "VIN_GND_VOUT",
            "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
            66.04,
            71.12,
            3,
            project,
        )
    )
    # The symbol library uses Cartesian y; sheet coordinates invert the sign.
    connections = [
        ("R1-1", "VIN", (101.6, 57.15), (101.6, 50.8)),
        ("R1-2", "VOUT", (101.6, 64.77), (101.6, 71.12)),
        ("R2-1", "VOUT", (101.6, 82.55), (101.6, 76.2)),
        ("R2-2", "GND", (101.6, 90.17), (101.6, 96.52)),
        ("J1-1", "VIN", (60.96, 68.58), (50.8, 68.58)),
        ("J1-2", "GND", (60.96, 71.12), (50.8, 71.12)),
        ("J1-3", "VOUT", (60.96, 73.66), (50.8, 73.66)),
    ]
    for name, net, start, end in connections:
        parts.extend(
            [wire(start, end, name + "-wire"), label(net, *end, name + "-label")]
        )
    parts.append('(sheet_instances (path "/" (page "1"))) (embedded_fonts no))')
    schematic = output / "divider.kicad_sch"
    schematic.write_text("\n".join(parts) + "\n")
    # KiCad will expand project defaults when opening the editable project.
    (output / "divider.kicad_pro").write_text(
        json.dumps({"meta": {"filename": "divider.kicad_pro", "version": 1}}, indent=2)
        + "\n"
    )
    return schematic


def check(output: Path) -> dict:
    output = output.resolve()
    schematic = generate(output)
    env = os.environ.copy()
    for name, folder in [
        ("XDG_CONFIG_HOME", "config"),
        ("XDG_CACHE_HOME", "cache"),
        ("XDG_DATA_HOME", "share"),
    ]:
        path = ROOT / ".local" / folder
        path.mkdir(parents=True, exist_ok=True)
        env[name] = str(path)
    # Keep library lookup explicit so ERC compares embedded symbols with installed
    # official libraries even in a freshly provisioned, headless user profile.
    kicad_profile = Path(env["XDG_CONFIG_HOME"]) / "kicad" / "9.0"
    kicad_profile.mkdir(parents=True, exist_ok=True)
    table = kicad_profile / "sym-lib-table"
    if not table.exists():
        table.write_text(
            "(sym_lib_table (version 7)\n"
            + "\n".join(
                f'(lib (name "{lib}") (type "KiCad") (uri "/usr/share/kicad/symbols/{lib}.kicad_sym") (options "") (descr ""))'
                for lib in ["Device", "Connector_Generic"]
            )
            + ")\n"
        )
    runs = []
    commands = [
        [
            "kicad-cli",
            "sch",
            "erc",
            "--severity-all",
            "--exit-code-violations",
            "--format",
            "json",
            "-o",
            str(output / "erc.json"),
            str(schematic),
        ],
        [
            "kicad-cli",
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "-o",
            str(output / "divider.xml"),
            str(schematic),
        ],
        [
            "kicad-cli",
            "sch",
            "export",
            "svg",
            "-o",
            str(output / "schematic-preview"),
            str(schematic),
        ],
        [
            "kicad-cli",
            "sch",
            "export",
            "bom",
            "--fields",
            "Reference,Value,Footprint",
            "--labels",
            "Reference,Value,Footprint",
            "-o",
            str(output / "bom.csv"),
            str(schematic),
        ],
    ]
    for command in commands:
        result = subprocess.run(
            command, check=False, env=env, capture_output=True, text=True
        )
        runs.append(
            {
                "command": command,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
        (output / "schematic-commands.json").write_text(
            json.dumps(runs, indent=2) + "\n"
        )
        if result.returncode:
            raise RuntimeError(json.dumps(runs[-1], indent=2))
    xml = ET.parse(output / "divider.xml")
    actual = {
        net.attrib["name"].removeprefix("/"): {
            (node.attrib["ref"], node.attrib["pin"]) for node in net.findall("node")
        }
        for net in xml.findall("./nets/net")
    }
    expected = {
        "VIN": {("J1", "1"), ("R1", "1")},
        "VOUT": {("J1", "3"), ("R1", "2"), ("R2", "1")},
        "GND": {("J1", "2"), ("R2", "2")},
    }
    assert actual == expected, (actual, expected)
    with (output / "bom.csv").open(newline="") as stream:
        bom = list(csv.DictReader(stream))
    assert {row["Reference"] for row in bom} == {"J1", "R1", "R2"}, bom
    report = json.loads((output / "erc.json").read_text())
    violations = [
        v for sheet in report.get("sheets", []) for v in sheet.get("violations", [])
    ]
    assert not violations, violations
    summary = {
        "status": "passed",
        "erc_violations": len(violations),
        "netlist": {net: sorted(pins) for net, pins in actual.items()},
        "commands": runs,
    }
    (output / "schematic-result.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output", nargs="?", type=Path, default=ROOT / "artifacts" / "eda"
    )
    args = parser.parse_args()
    print(json.dumps(check(args.output), indent=2))
