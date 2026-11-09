#!/usr/bin/python3
"""Create/reroute an editable divider PCB and check fabrication outputs.

Requires Debian KiCad9 pcbnew SWIG runtime; invoke scripts/run-kicad.sh python.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pcbnew as pcb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from schematic import check as check_schematic
from schematic import uid


def point(x, y):
    return pcb.VECTOR2I(pcb.FromMM(x), pcb.FromMM(y))


def generate(output: Path):
    board = pcb.BOARD()
    board.SetCopperLayerCount(2)
    board.GetDesignSettings().SetBoardThickness(pcb.FromMM(1.6))
    nets = {}
    for name in ["/VIN", "/VOUT", "/GND"]:
        nets[name] = pcb.NETINFO_ITEM(board, name)
        board.Add(nets[name])
    mapping = {
        "R1": {"1": "/VIN", "2": "/VOUT"},
        "R2": {"1": "/VOUT", "2": "/GND"},
        "J1": {"1": "/VIN", "2": "/GND", "3": "/VOUT"},
    }
    for ref, lib, name, pos, value in [
        ("R1", "Resistor_SMD", "R_0805_2012Metric", (16, 8), "10k"),
        ("R2", "Resistor_SMD", "R_0805_2012Metric", (26, 8), "10k"),
        (
            "J1",
            "Connector_PinHeader_2.54mm",
            "PinHeader_1x03_P2.54mm_Vertical",
            (5, 8),
            "VIN_GND_VOUT",
        ),
    ]:
        fp = pcb.FootprintLoad(f"/usr/share/kicad/footprints/{lib}.pretty", name)
        assert fp, name
        fp.SetFPID(pcb.LIB_ID(lib, name))
        fp.SetReference(ref)
        fp.SetValue(value)
        fp.SetPosition(point(*pos))
        path = pcb.KIID_PATH()
        path.push_back(pcb.KIID(uid("sheet")))
        path.push_back(pcb.KIID(uid(ref)))
        fp.SetPath(path)
        board.Add(fp)
        for pad in fp.Pads():
            pad.SetNet(nets[mapping[ref][pad.GetNumber()]])
        # Footprint models are supplied by the official KiCad3D package.
        for model in fp.Models():
            if model.m_Filename.endswith(".wrl"):
                model.m_Filename = model.m_Filename[:-4] + ".step"
    corners = [(0, 0), (40, 0), (40, 25), (0, 25)]
    for a, b in zip(corners, corners[1:] + corners[:1]):
        segment = pcb.PCB_SHAPE()
        segment.SetShape(pcb.SHAPE_T_SEGMENT)
        segment.SetStart(point(*a))
        segment.SetEnd(point(*b))
        segment.SetLayer(pcb.Edge_Cuts)
        segment.SetWidth(pcb.FromMM(0.05))
        board.Add(segment)
    filename = output / "divider-unrouted.kicad_pcb"
    pcb.SaveBoard(str(filename), board)
    assert pcb.ExportSpecctraDSN(board, str(output / "divider.dsn"))
    actual = {}
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            actual.setdefault(pad.GetNetname().removeprefix("/"), set()).add(
                (fp.GetReference(), pad.GetNumber())
            )
    xml = ET.parse(output / "divider.xml")
    expected = {
        net.attrib["name"].removeprefix("/"): {
            (n.attrib["ref"], n.attrib["pin"]) for n in net.findall("node")
        }
        for net in xml.findall("./nets/net")
    }
    assert actual == expected, (actual, expected)
    return board


def check(output):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    check_schematic(output)
    board = generate(output)
    runs = []

    def run(command, timeout=180):
        result = subprocess.run(
            [str(v) for v in command],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        runs.append(
            {
                "command": [str(v) for v in command],
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
        (output / "pcb-commands.json").write_text(json.dumps(runs, indent=2) + "\n")
        if result.returncode:
            raise RuntimeError(json.dumps(runs[-1], indent=2))
        return result

    session = output / "divider.ses"
    session.unlink(missing_ok=True)
    run(
        [
            ROOT / "scripts/run-freerouting.sh",
            "-de",
            output / "divider.dsn",
            "-do",
            session,
            "-mp",
            "8",
            "-mt",
            "2",
        ]
    )
    assert session.stat().st_size > 100
    assert pcb.ImportSpecctraSES(board, str(session)), "SES import failed"
    assert len(list(board.GetTracks())) > 0, "No routing imported"
    target = output / "divider.kicad_pcb"
    pcb.SaveBoard(str(target), board)
    # The fresh process performs the engineering DRC; don't infer validity from export.
    cli = ROOT / "scripts/run-kicad.sh"
    run(
        [
            cli,
            "pcb",
            "drc",
            "--severity-all",
            "--schematic-parity",
            "--exit-code-violations",
            "--format",
            "json",
            "-o",
            output / "drc.json",
            target,
        ]
    )
    drc = json.loads((output / "drc.json").read_text())
    assert not drc.get("violations"), drc.get("violations")
    assert not drc.get("unconnected_items"), drc.get("unconnected_items")
    assert not drc.get("schematic_parity"), drc.get("schematic_parity")
    gerbers = output / "gerbers"
    gerbers.mkdir(exist_ok=True)
    run([cli, "pcb", "export", "gerbers", "-o", str(gerbers) + "/", target])
    run([cli, "pcb", "export", "drill", "-o", str(gerbers) + "/", target])
    run(
        [
            cli,
            "pcb",
            "export",
            "step",
            "--force",
            "--include-tracks",
            "--include-pads",
            "-o",
            output / "divider.step",
            target,
        ]
    )
    run(
        [
            cli,
            "pcb",
            "export",
            "svg",
            "--mode-multi",
            "--layers",
            "F.Cu,B.Cu,Edge.Cuts,F.Silkscreen",
            "-o",
            str(output / "pcb-preview") + "/",
            target,
        ]
    )
    # Reopen native file and independently verify pad connectivity and dimensions.
    reopened = pcb.LoadBoard(str(target))
    assert len(list(reopened.GetFootprints())) == 3
    assert len(list(reopened.GetTracks())) > 0
    bb = reopened.GetBoardEdgesBoundingBox()
    assert abs(pcb.ToMM(bb.GetWidth()) - 40.05) < 0.1
    assert abs(pcb.ToMM(bb.GetHeight()) - 25.05) < 0.1
    assert any(gerbers.glob("*.drl")), "No Excellon drills"
    assert len(list(gerbers.glob("*.gbr"))) >= 2, "Missing copper Gerbers"
    summary = {
        "status": "passed",
        "kicad": pcb.Version(),
        "drc_violations": 0,
        "unconnected_items": 0,
        "footprints": 3,
        "tracks_and_vias": len(list(reopened.GetTracks())),
        "vias": sum(isinstance(t, pcb.PCB_VIA) for t in reopened.GetTracks()),
        "dimensions_mm": [40, 25, 1.6],
        "commands": runs,
    }
    (output / "pcb-result.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output", nargs="?", type=Path, default=ROOT / "artifacts" / "eda"
    )
    print(json.dumps(check(parser.parse_args().output), indent=2))
