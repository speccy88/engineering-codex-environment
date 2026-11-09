# Codex Cloud environment lifecycle

## Architecture and installation

This is native Debian 13 amd64, not a Docker deployment. The base filesystem already provides FreeCAD, KiCad, Blender, OpenSCAD, Java, FFmpeg, ImageMagick, Git, GitHub CLI, uv and Codex CLI. `setup/environment-report.md` records the pre-install baseline. Another Codex installation or nested execution adds no useful capability.

The current user cannot write system package directories and has no sudo or scoped package helper. Missing native packages were downloaded with APT against signed Debian archive metadata, hash-verified, and extracted to `.local/sysroot`; their runtime dependencies were checked. `setup/native-extras.json` preserves exact versions, URLs and authenticated SHA256 digests. Freerouting's official GitHub release has a retained digest in `setup/freerouting.json`; it records a TLS-verified download, not an independent upstream signature.

The complete KiCad 9 3D library occupies approximately4.8GiB, selected by `KICAD9_3DMODEL_DIR` in the wrapper. Prefix packages are not registered in the system dpkg database. Python 3.12 scientific packages and the isolated optional IPC client live in `.venvs/`. Native FreeCAD/KiCad and Blender keep their compatible Python 3.13 runtimes.

## Install, Start, and publication

- **Install**: `setup/cloud-install.sh` changes to the checkout and runs `setup/install.sh`. Tested here, including repeat refresh. It hash-syncs Python packages and installs missing prefix assets; retained large assets are skipped using versioned markers. It does not rewrite source or locks.
- **Start**: `setup/start-skill.md` reads agent instructions, runs quick probes, and selects only needed tools. No download, persistent service, or exposed port. TechDraw starts a temporary Xvfb display with TCP disabled and cleans it up.
- **Acceptance**: `bash setup/verify.sh --full` writes fresh timestamped commands, exit codes and logs in `artifacts/verification/`. Quick probes do not validate project engineering behavior.

The environment draft has Install and Start fields saved. Saving does not execute scripts, apply network changes, publish, or prove restoration. Review and save in environment settings, then **Publish** when offered. Publication retains the prepared filesystem and dependencies, not live processes. No localhost preview is required.

## Rebuild boundary

The Install script refreshes this **prepared image**, not every Debian application on an arbitrary host without privileges. The native inventory is pinned in `setup/versions.lock`. A new Debian 13 amd64 base needs an administrator/supported image builder to install the prerequisites from authenticated distribution repositories:

```sh
# Image-building/admin context only, not ordinary cloud tasks.
apt-get update
apt-get install freecad kicad kicad-symbols kicad-footprints blender openscad \
  openjdk-21-jre-headless ffmpeg imagemagick git gh curl ca-certificates
```

Use exact inventory versions where offered and Debian snapshot archives for historical reconstruction. Do not replace hashes or disable checks when artifacts move. The installer reports missing native prerequisites instead of assuming privileges. Python 3.12 and uv are also needed; `WB_PYTHON312` selects a compatible executable. Python locks include hashes; updates require explicit resolution and retesting.

Republish after changing system packages, prefix files, Python environments, wrappers or retained installation state. A project commit alone does not update the published snapshot or other tasks. Fresh-task restoration has not been claimed as tested.

## Network and credentials

Runtime initially enforces the package-manager preset, including Debian/PyPI/GitHub release and Git transport destinations. No engineering operation needs a cloud API key, persistent service, or exposed port. Preserve inherited proxy and CA settings.

`api.github.com` was added to the draft for GitHub CLI PR operations after CONNECT returned403. It must be applied in environment settings before API access works. Git transport uses existing platform authentication; no personal access token was requested. User network changes are checked with fresh runtime status and a new connection.

## Future tasks

1. Select the published workbench environment and desired project repository.
2. Follow Start instructions and quick readiness checks.
3. Request only the desired tool/workflow. Preserve native sources and run actual engineering checks.
4. Exchange committed native files and versioned interfaces through branches/PRs; separate tasks do not share uncommitted files.
5. Download the sources and exports as a ZIP or continue through the project repository.
