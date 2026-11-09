# Baseline environment report

Measured on 2026-11-09 before workbench installation. Raw commands and exit codes: `artifacts/baseline/commands.json` (generated, not committed).

- Debian GNU/Linux 13.6 (trixie), Linux x86_64, AMD EPYC 9V74 virtual CPU, 5 cores. SSE4, AVX2 and AVX512 available.
- RAM 33 GiB total, approximately 32 GiB available; no swap. Overlay disk 63 GiB, approximately 60 GiB available.
- Agent Python 3.12.14, system Python 3.13.5. uv 0.13.5. System-native FreeCAD and KiCad bindings require system Python, not the agent Python.
- Existing packages: FreeCAD 1.0.0+dfsg-8+deb13u3, KiCad 9.0.2+dfsg-1, Blender 4.3.2+dfsg-2, OpenSCAD 2021.01-8, OCCT 7.8.1, Java 21.0.13.
- Mesa 25.0.7, EGL/GLX/OpenGL/GLU, Qt5 and PySide2 available. GPU hardware is not assumed; test offscreen Qt and CPU rendering.
- Runs as unprivileged `agent` (uid 1000); no sudo or cloud-agent-packages helper. System paths are not writable. APT/dpkg and uv available. Missing native packages can be installed under a workspace prefix from signed Debian repository metadata; no signature, checksum or TLS checks may be bypassed.
- Docker client exists; no container is required for this native workbench. Docker daemon availability has not been exercised.
- Git 2.52.0, GitHub CLI 2.46.0, Codex CLI 0.167.0-alpha.4 present. No nested Codex process or extra CLI installation is needed.
- Restricted outbound proxy policy is enforced, package-manager domain preset enabled, no custom domains or secrets. GitHub read access succeeded. Keep inherited proxy and CA trust. Any blocked release CDN requires a focused policy addition, not unrestricted access.
- Codex publication snapshots installed filesystem and dependency caches. It does not preserve live processes. Save Install and Start configuration, then review/save/publish via environment settings. No persistent services or exposed ports are required.

See `test-matrix.md` and `versions.lock` for measured final capabilities and versions.

## Post-install resource measurement

After verified installation and removal of downloaded DEB installers: overlay63GiB total,8.3GiB used,52GiB available. RAM33GiB total, approximately1.0GiB in use and32GiB available; no swap. Workspace native prefix4.9GiB, engineering+IPC environments1.8GiB, retained uv cache1.7GiB, generated acceptance outputs about9.5MiB. `uv cache prune` found no unused entries. No expensive source builds or containers were required; modeling/meshing/rendering use two worker threads.
