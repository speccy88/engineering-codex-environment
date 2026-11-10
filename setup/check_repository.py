"""Dependency-free checks suitable for ordinary CI; no CAD tools installed."""

import ast
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    files = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    count = 0
    for name in files:
        path = ROOT / name
        if path.suffix == ".py":
            ast.parse(path.read_text(), filename=name)
            count += 1
        elif path.suffix == ".sh":
            subprocess.run(["bash", "-n", str(path)], check=True)
            assert path.stat().st_mode & 0o111, f"Not executable: {name}"
            count += 1
        elif path.suffix == ".json":
            json.loads(path.read_text())
            count += 1
    for path in (ROOT / "skills").glob("*/SKILL.md"):
        text = path.read_text()
        assert text.startswith("---\n"), path
        frontmatter = text.split("---", 2)[1]
        assert re.search(r"^name: .+", frontmatter, re.MULTILINE), path
        assert re.search(r"^description: .+", frontmatter, re.MULTILINE), path
        count += 1
    packages = json.loads((ROOT / "setup/native-extras.json").read_text())["packages"]
    packages.extend(
        json.loads((ROOT / "setup/pyspice-native.json").read_text())["packages"]
    )
    packages.extend(
        json.loads((ROOT / "setup/fritzing-native.json").read_text())["packages"]
    )
    packages.append(json.loads((ROOT / "setup/freerouting.json").read_text()))
    for package in packages:
        assert re.fullmatch(r"[0-9a-f]{64}", package["sha256"])
        assert package["url"].startswith("https://")
    for name in ["requirements.lock", "kicad-ipc.lock"]:
        text = (ROOT / "setup" / name).read_text()
        assert "--hash=sha256:" in text and "==" in text, name
    print(
        f"PASS: {count} Python, shell, JSON and skill checks; native downloads and Python locks validated."
    )


if __name__ == "__main__":
    main()
