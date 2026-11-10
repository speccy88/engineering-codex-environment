#!/usr/bin/env python3
"""Search installed Fritzing parts and inspect exact connector IDs and SVGs."""

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parts_directory(value=None):
    override = value or os.environ.get("FRITZING_PARTS_DIR")
    if override:
        if not Path(override).is_dir():
            raise ValueError(f"Parts directory does not exist: {override}")
        return Path(override).resolve()
    candidates = [ROOT / ".local/sysroot/usr/share/fritzing/parts",
                  Path("/usr/share/fritzing/parts")]
    for candidate in candidates:
        if candidate and Path(candidate).is_dir():
            return Path(candidate).resolve()
    raise ValueError("No parts library found; run setup/install-fritzing.sh or set FRITZING_PARTS_DIR")


def read_part(path, directory):
    node = ET.parse(path).getroot()
    result = {
        "path": str(path), "module_id": node.get("moduleId"),
        "title": node.findtext("title", ""),
        "description": " ".join("".join(node.find("description").itertext()).split())
            if node.find("description") is not None else "",
        "author": node.findtext("author", ""),
        "properties": {p.get("name"): p.text or "" for p in node.findall("properties/property")},
        "tags": [t.text or "" for t in node.findall("tags/tag")],
        "views": {}, "connectors": [],
    }
    for view in node.findall("views/*"):
        layers = view.find("layers")
        if layers is None:
            continue
        image = layers.get("image", "")
        assets = [directory / "svg" / library / image for library in ("core", "contrib", "user")]
        asset = next((p for p in assets if p.is_file()), None)
        result["views"][view.tag] = {
            "image": image, "asset": str(asset) if asset else None,
            "layers": [p.get("layerId") for p in layers.findall("layer")],
        }
    for connector in node.findall("connectors/connector"):
        result["connectors"].append({
            "id": connector.get("id"), "name": connector.get("name"),
            "type": connector.get("type"),
            "description": connector.findtext("description", ""),
            "views": {view.tag: [dict(p.attrib) for p in view.findall("p")]
                      for view in connector.findall("views/*")},
        })
    result["buses"] = [{"id": bus.get("id"),
                        "connectors": [member.get("connectorId") for member in bus.findall("nodeMember")]}
                       for bus in node.findall("buses/bus")]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parts-dir", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    search = sub.add_parser("search", help="Case-insensitive AND search over part metadata")
    search.add_argument("query", nargs="+")
    search.add_argument("--limit", type=int, default=30)
    inspect = sub.add_parser("inspect", help="Exact module ID or .fzp file path")
    inspect.add_argument("part")
    args = parser.parse_args()
    try:
        directory = parts_directory(args.parts_dir)
        if args.command == "inspect" and Path(args.part).is_file():
            print(json.dumps(read_part(Path(args.part).resolve(), directory), indent=2))
            return 0
        matches = []
        for path in sorted(directory.rglob("*.fzp")):
            try:
                part = read_part(path, directory)
            except (ET.ParseError, OSError):
                continue
            if args.command == "inspect":
                if part["module_id"] == args.part:
                    print(json.dumps(part, indent=2))
                    return 0
            else:
                searchable = json.dumps({key: part[key] for key in
                    ("module_id", "title", "description", "properties", "tags")}).casefold()
                if all(term.casefold() in searchable for term in args.query):
                    matches.append({key: part[key] for key in ("module_id", "title", "path", "properties")})
        if args.command == "inspect":
            raise ValueError(f"Part not found: {args.part}")
        if args.limit < 1:
            raise ValueError("--limit must be positive")
        print(json.dumps({"total": len(matches), "results": matches[:args.limit]}, indent=2))
        return 0
    except (ValueError, OSError, ET.ParseError) as error:
        print(f"fritzing-parts: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
