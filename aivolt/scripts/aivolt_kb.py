#!/usr/bin/env python3
"""Structured AI Volt knowledge base for fast, rule-based answers.

This keeps Cortex 2.0 AI Volt chat fast by answering common factual questions
directly instead of loading the full context into the slow BitNet model.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple


@dataclass
class Fact:
    tags: Tuple[str, ...]
    answer: str
    check: Optional[Callable[[str], bool]] = None


WIRING_ADS1115 = """ADS1115 to Tang wiring:
- Tang 3V3  -> ADS1115 VDD
- Tang GND  -> ADS1115 GND and ADS1115 ADDR (selects I2C address 0x48)
- Tang K11  -> ADS1115 SDA
- Tang L11  -> ADS1115 SCL

Divider to ADS1115:
- Divider S  -> ADS1115 A0
- Divider -  -> ADS1115 GND
- Divider +  -> leave disconnected

Measured source:
- Source positive (+) -> divider screw-terminal VCC
- Source negative (-) -> divider screw-terminal GND"""


PINS = """Key Tang pins:
- 50 MHz clock: E2
- READY LED:    E8
- I2C SDA:      K11
- I2C SCL:      L11
- UART TX:      C3

Middle PMOD header (underside labels):
Top:    A11  E11  K11  L5  GND  3V3
Bottom: A10  E10  L11  K5  GND  3V3"""


UART_FORMAT = """UART output on /dev/ttyUSB1 at 115200 8N1 raw:
- Fixed bitstream: four hex digits, e.g. 1334
- Autorange bitstream: L:/M:/W: prefix + four hex digits
  L = +/-0.512 V scale (0.00003125 V/count)
  M = +/-1.024 V scale (0.0000625 V/count)
  W = +/-2.048 V scale (0.000125 V/count)"""


CONVERSION = """Voltage conversion:
1. Parse hex as signed 16-bit two's complement.
2. ADC voltage = signed_raw * scale
3. Input voltage = ADC voltage * 5.035 (divider ratio)

Example: raw 1334 hex = 4916 decimal
ADC = 4916 * 0.0000625 = 0.30725 V
Input = 0.30725 * 5.035 ≈ 1.547 V"""


SAFETY = """Safety limits for this prototype:
- Maximum 15 V quiet, protected bench DC
- Never mains voltage
- Never a running vehicle or alternator
- Disconnect USB before changing wiring
- Unplug the measured source before moving its wires
- Confirm polarity with a multimeter first"""


COMMANDS = """Common commands:
Detect FPGA:     openFPGALoader --detect
Load proven:     openFPGALoader -b tangprimer25k ai_volt_meter.fs
Load autorange:  openFPGALoader -b tangprimer25k ai_volt_meter_autorange.fs
Run logger:      python ai_volt_meter.py
Configure UART:  stty -F /dev/ttyUSB1 115200 cs8 -cstopb -parenb raw -echo
Stream raw:      cat /dev/ttyUSB1
Query DB:        sqlite3 voltage_fingerprints.sqlite3 SELECT * FROM fingerprints;"""


BRIDGE = """Cortex 2.0 AI Volt bridge commands:
  python aivolt/scripts/aivolt_bridge.py diagnose
  python aivolt/scripts/aivolt_bridge.py load --bitstream autorange
  python aivolt/scripts/aivolt_bridge.py read --profile wide --identity aaa
  python aivolt/scripts/aivolt_bridge.py query --identity aaa --limit 5
  python aivolt/scripts/aivolt_bridge.py interpret --volts 12.6 --profile automotive"""


ASSESSMENT = """Voltage assessment rules:
- < -0.05 V   -> POLARITY/WIRING ERROR
- > 15 V      -> OVER LIMIT
- Automotive:
  < 1.0  -> CHECK CONNECTION
  < 10.5 -> CRITICALLY LOW
  < 12.0 -> LOW
  < 12.4 -> PARTIALLY CHARGED
  12.4-12.9 -> NORMAL RESTING RANGE
  > 12.9 -> CHARGING/RECENTLY CHARGED
- Near 0 V (<0.02) -> CHECK CONNECTION
- Otherwise -> IN EXPECTED RANGE or OUTSIDE EXPECTED RANGE"""


TROUBLESHOOTING = """Troubleshooting order:
1. Measure source with a multimeter.
2. Measure divider S-to-GND (1.5 V AAA -> ~310 mV).
3. Measure ADS1115 A0-to-GND; should match divider S.
4. Check /dev/ttyUSB1 exists after USB reconnect.
5. Reload the bitstream if power was cycled.
6. Run openFPGALoader --detect if JTAG fails."""


OVERVIEW = """AI Volt is a Tang Primer 25K FPGA + ADS1115 16-bit I2C ADC auto-ranging voltmeter with a SQLite fingerprint database.

Signal path: source -> 5.035:1 divider -> ADS1115 A0 -> I2C -> Tang FPGA -> UART -> /dev/ttyUSB1

Project folder: ~/Desktop/a.i. tang engineering/
Launchers: ~/.local/bin/aivolt (linear) and ~/.local/bin/aivolt-lab (dashboard)
Cortex 2.0 bridge: aivolt/scripts/aivolt_bridge.py"""


FACTS: List[Fact] = [
    Fact(("what is", "overview", "ai volt", "project"), OVERVIEW),
    Fact(("wiring", "ads1115", "tang", "connect", "wire"), WIRING_ADS1115),
    Fact(("pin", "pins", "fpga", "k11", "l11", "e2", "c3", "pmod"), PINS),
    Fact(("uart", "serial", "ttyusb1", "format", "hex", "115200"), UART_FORMAT),
    Fact(("convert", "conversion", "voltage", "formula", "1334", "scale", "divider"), CONVERSION),
    Fact(("safety", "limit", "15v", "mains", "vehicle", "danger"), SAFETY),
    Fact(("command", "commands", "openfpgaloader", "load", "stty", "sqlite"), COMMANDS),
    Fact(("bridge", "aivolt_bridge"), BRIDGE),
    Fact(("assess", "assessment", "status", "automotive", "low", "normal"), ASSESSMENT),
    Fact(("troubleshoot", "debug", "zero", "silent", "fix"), TROUBLESHOOTING),
]


def find_answer(query: str) -> Optional[str]:
    """Return a direct answer if the query matches a known fact pattern."""
    q = query.lower()
    # Bridge command requests
    if any(x in q for x in ("bridge", "aivolt_bridge")):
        return BRIDGE
    # Exact tag matching
    best: Optional[Tuple[int, str]] = None
    for fact in FACTS:
        score = sum(1 for tag in fact.tags if tag in q)
        if score and (best is None or score > best[0]):
            best = (score, fact.answer)
    if best:
        return best[1]
    return None


