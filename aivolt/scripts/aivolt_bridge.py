#!/usr/bin/env python3
"""BitNet Cortex 2.0 bridge for AI Volt.

This module lets Cortex 2.0 understand, control, and interpret the Tang
Primer 25K / ADS1115 voltmeter without modifying the original AI Volt files.
It imports from the copied `aivolt/ai_volt_meter.py` and adds a non-interactive
API on top.
"""
from __future__ import annotations

import json
import os
import subprocess
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import measurement primitives from the copied (non-modified) AI Volt script.
sys.path.insert(0, str(Path(__file__).resolve().parent / "aivolt"))
import ai_volt_meter as avm

PROJECT_DIR = Path.home() / "Desktop" / "a.i. tang engineering"
PROVEN_BITSTREAM = PROJECT_DIR / "ai_volt_meter.fs"
AUTORANGE_BITSTREAM = PROJECT_DIR / "ai_volt_meter_autorange.fs"
DB_PATH = PROJECT_DIR / "voltage_fingerprints.sqlite3"


def project_dir() -> Path:
    return PROJECT_DIR


def load_bitstream(name: str = "autorange") -> Dict[str, Any]:
    """Load an FPGA bitstream into SRAM."""
    bitstream = AUTORANGE_BITSTREAM if name == "autorange" else PROVEN_BITSTREAM
    if not bitstream.exists():
        return {"ok": False, "error": f"bitstream not found: {bitstream}"}

    try:
        result = subprocess.run(
            ["openFPGALoader", "-b", "tangprimer25k", str(bitstream)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return {
            "ok": result.returncode == 0,
            "bitstream": name,
            "path": str(bitstream),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def diagnose() -> Dict[str, Any]:
    """Check whether the AI Volt hardware stack appears present."""
    out: Dict[str, Any] = {
        "project_dir": str(PROJECT_DIR),
        "project_dir_exists": PROJECT_DIR.exists(),
        "proven_bitstream": str(PROVEN_BITSTREAM),
        "proven_bitstream_exists": PROVEN_BITSTREAM.exists(),
        "autorange_bitstream": str(AUTORANGE_BITSTREAM),
        "autorange_bitstream_exists": AUTORANGE_BITSTREAM.exists(),
        "serial_device": avm.SERIAL_DEVICE,
        "serial_device_exists": os.path.exists(avm.SERIAL_DEVICE),
        "db_path": str(DB_PATH),
        "db_exists": DB_PATH.exists(),
        "ftdi_present": False,
        "jtag_detect": None,
    }
    try:
        usb = subprocess.run(["lsusb"], capture_output=True, text=True, timeout=5)
        out["ftdi_present"] = "0403:6010" in usb.stdout
    except Exception as exc:
        out["ftdi_error"] = str(exc)

    try:
        jtag = subprocess.run(
            ["openFPGALoader", "--detect"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        out["jtag_detect"] = {
            "ok": jtag.returncode == 0,
            "stdout": jtag.stdout,
            "stderr": jtag.stderr,
        }
    except Exception as exc:
        out["jtag_detect"] = {"ok": False, "error": str(exc)}

    return out


def take_reading(profile: str = "wide", identity: str = "cortex-test") -> Dict[str, Any]:
    """Take a non-interactive voltage reading and return a fingerprint dict."""
    if profile not in ("low", "medium", "automotive", "wide"):
        return {"ok": False, "error": f"unknown profile: {profile}"}

    if profile == "automotive":
        # Safety: automotive requires explicit disconnect confirmation.
        return {
            "ok": False,
            "error": "automotive profile requires human confirmation; use ai_volt_meter.py directly",
        }

    if not os.path.exists(avm.SERIAL_DEVICE):
        return {"ok": False, "error": f"{avm.SERIAL_DEVICE} not found"}

    try:
        samples = avm.collect_window(avm.SERIAL_DEVICE)
        fp = avm.build_fingerprint(samples)
        status, note = avm.assessment(profile, fp["average_voltage"])
        prior = avm.save(identity, profile, fp, status, note)
        return {
            "ok": True,
            "profile": profile,
            "identity": identity,
            "fingerprint": fp,
            "status": status,
            "note": note,
            "recent_history": [
                {
                    "measured_at": r[0],
                    "average_voltage": r[1],
                    "status": r[2],
                    "sample_count": r[3],
                    "stability": r[4],
                }
                for r in prior
            ],
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def interpret(volts: float, profile: str = "wide") -> Dict[str, str]:
    """Interpret a voltage value using AI Volt's assessment rules."""
    status, note = avm.assessment(profile, volts)
    return {"status": status, "note": note, "profile": profile, "volts": f"{volts:.4f}"}


def query_db(identity: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """Query the fingerprint database."""
    if not DB_PATH.exists():
        return []
    sql = (
        "SELECT id, measured_at, identity, kind, volts, spread, status, note, "
        "sample_count, average_voltage, stability FROM fingerprints "
    )
    params: List[Any] = []
    if identity:
        sql += "WHERE identity = ? "
        params.append(identity)
    sql += "ORDER BY id DESC LIMIT ?"
    params.append(limit)

    with sqlite3.connect(DB_PATH) as db:
        rows = db.execute(sql, params).fetchall()

    cols = [
        "id", "measured_at", "identity", "kind", "volts", "spread",
        "status", "note", "sample_count", "average_voltage", "stability",
    ]
    return [dict(zip(cols, row)) for row in rows]


def stream_raw(duration: float = 5.0) -> Dict[str, Any]:
    """Stream raw ADC values for a short duration and return parsed samples."""
    import re
    import select
    import termios

    device = avm.SERIAL_DEVICE
    if not os.path.exists(device):
        return {"ok": False, "error": f"{device} not found"}

    fd = os.open(device, os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK)
    try:
        avm.configure_serial(fd)
        samples: List[Dict[str, Any]] = []
        buffer = ""
        tagged = re.compile(r"^([LMW]):([0-9A-Fa-f]{4})$")
        legacy = re.compile(r"^([0-9A-Fa-f]{4})$")
        deadline = time.monotonic() + duration
        while time.monotonic() < deadline:
            ready, _, _ = select.select([fd], [], [], 0.5)
            if not ready:
                continue
            buffer += os.read(fd, 256).decode("ascii", "ignore")
            lines = re.split(r"[\r\n]+", buffer)
            buffer = lines.pop()
            for line in lines:
                line = line.strip()
                m = tagged.match(line)
                if m:
                    code = avm.signed16(int(m.group(2), 16))
                    samples.append({
                        "raw": line,
                        "scale": m.group(1),
                        "adc_v": code * avm.SCALE[m.group(1)],
                        "input_v": code * avm.SCALE[m.group(1)] * avm.DIVIDER_RATIO,
                    })
                else:
                    m = legacy.match(line)
                    if m:
                        code = avm.signed16(int(m.group(1), 16))
                        samples.append({
                            "raw": line,
                            "scale": "M",
                            "adc_v": code * avm.SCALE["M"],
                            "input_v": code * avm.SCALE["M"] * avm.DIVIDER_RATIO,
                        })
        return {"ok": True, "count": len(samples), "samples": samples}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        os.close(fd)


def main() -> int:
    """CLI for quick bridge tests."""
    import argparse

    parser = argparse.ArgumentParser(description="AI Volt bridge for BitNet Cortex 2.0")
    parser.add_argument("action", choices=["diagnose", "load", "read", "query", "interpret"])
    parser.add_argument("--profile", default="wide")
    parser.add_argument("--identity", default="cortex-test")
    parser.add_argument("--bitstream", default="autorange")
    parser.add_argument("--volts", type=float)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    if args.action == "diagnose":
        print(json.dumps(diagnose(), indent=2))
    elif args.action == "load":
        print(json.dumps(load_bitstream(args.bitstream), indent=2))
    elif args.action == "read":
        print(json.dumps(take_reading(args.profile, args.identity), indent=2))
    elif args.action == "query":
        print(json.dumps(query_db(identity=args.identity, limit=args.limit), indent=2))
    elif args.action == "interpret":
        if args.volts is None:
            print("--volts required")
            return 1
        print(json.dumps(interpret(args.volts, args.profile), indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
