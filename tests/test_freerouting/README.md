# Autorouting acceptance

The real acceptance test is `scripts/run-kicad.sh python tests/test_kicad/board.py`.
It creates an unrouted board, exports DSN using pcbnew, calls the standalone
Freerouting wrapper with GUI and analytics disabled, imports the fresh SES,
checks that copper was actually added, then runs KiCad DRC with all severities,
unconnected checks and schematic parity. A successful process or SES file alone
never counts as a valid routed PCB.

Commands, stdout/stderr and exit statuses are recorded in
`artifacts/eda/pcb-commands.json`; the actual DSN/SES/native PCB are retained.
The current fixture routes on both copper layers and contains a through via.
Freerouting may choose different equivalent routes on another CPU/version.

Standalone use (any independent KiCad project):

```sh
scripts/run-freerouting.sh -de input.dsn -do output.ses -mp 8 -mt 2
```

Import that SES into its original board before running real DRC. DSN/SES do not
replace the editable KiCad project. Two routing threads and a 2 GiB Java heap
fit this cloud machine without monopolizing other tasks.
