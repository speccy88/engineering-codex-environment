#!/usr/bin/env python3
"""Generate and validate editable Fritzing projects from declarative JSON."""
import argparse
import json
import sys
from pathlib import Path
from fritzing_workflow.project import generate, validate


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="command",required=True)
    gen=sub.add_parser("generate");gen.add_argument("design",type=Path);gen.add_argument("--output",required=True,type=Path)
    val=sub.add_parser("validate");val.add_argument("project",type=Path);val.add_argument("--report",type=Path)
    args=parser.parse_args()
    try:
        if args.command=="generate":report=generate(json.loads(args.design.read_text()),args.output)
        else:report=validate(args.project)
        if args.command=="validate" and args.report:
            args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,indent=2)+"\n")
        print(json.dumps(report,indent=2))
        return 0 if report["passed"] else 1
    except (ValueError,OSError,TypeError) as exc:
        print(f"Fritzing workflow error: {exc}",file=sys.stderr);return 2


if __name__=="__main__":sys.exit(main())
