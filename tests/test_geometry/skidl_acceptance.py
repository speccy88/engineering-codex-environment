"""Use stock KiCad 9 symbols to produce an electrically checked divider netlist."""

import json
import os
from pathlib import Path


def main(out=Path("artifacts/python/skidl")):
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").unlink(missing_ok=True)
    previous = Path.cwd()
    os.chdir(out)
    try:
        # Import after entering the artifact directory: SKiDL logs there by design.
        from skidl import (
            ERC,
            KICAD9,
            Net,
            Part,
            generate_netlist,
            reset,
            set_default_tool,
        )

        set_default_tool(KICAD9)
        reset()
        from builtins import default_circuit

        default_circuit.tag = "divider"
        top = Part(
            "Device",
            "R",
            value="10k",
            ref="R1",
            tag="R1",
            footprint="Resistor_SMD:R_0805_2012Metric",
        )
        bottom = Part(
            "Device",
            "R",
            value="10k",
            ref="R2",
            tag="R2",
            footprint="Resistor_SMD:R_0805_2012Metric",
        )
        connector = Part(
            "Connector_Generic",
            "Conn_01x03",
            ref="J1",
            tag="J1",
            footprint="Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
        )
        vin, vout, ground = Net("VIN_5V"), Net("VOUT"), Net("GND")
        vin += top[1], connector[1]
        vout += top[2], bottom[1], connector[2]
        ground += bottom[2], connector[3]
        ERC()
        # Logger count is the actual SKiDL ERC diagnostic count, not a custom rule.
        from skidl.logger import active_logger, erc_logger

        errors = erc_logger.error.count + erc_logger.bare_error.count
        warnings = erc_logger.warning.count + erc_logger.bare_warning.count
        assert errors == 0, f"SKiDL ERC errors: {errors}"
        generate_netlist(file_="divider.net", tool=KICAD9, do_backup=False)
        netlist_errors = active_logger.error.count + active_logger.bare_error.count
        netlist_warnings = (
            active_logger.warning.count + active_logger.bare_warning.count
        )
        assert netlist_errors == 0, f"SKiDL netlist errors: {netlist_errors}"
        text = Path("divider.net").read_text()
        for expected in ("VIN_5V", "VOUT", "GND", "R1", "R2", "J1", "10k"):
            assert expected in text, f"Missing expected netlist data: {expected}"
        result = {
            "status": "passed",
            "skidl_erc_errors": errors,
            "skidl_erc_warnings": warnings,
            "symbol_backend": "KICAD9",
            "netlist_errors": netlist_errors,
            "netlist_warnings": netlist_warnings,
            "netlist": str(out / "divider.net"),
            "scope": "SKiDL netlist/ERC only; KiCad schematic ERC is a separate acceptance test",
        }
        Path("result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result))
    finally:
        os.chdir(previous)


if __name__ == "__main__":
    main()
