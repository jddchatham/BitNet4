#!/usr/bin/env python3
"""BitNet Cortex 2.0 AI Volt chat — fast mode.

Most AI Volt questions are answered directly from a structured knowledge base
so chat is instant. The slow local LLM is only invoked for complex or unknown
questions, and only with a minimal retrieved context.
"""
from __future__ import annotations

import json
import logging
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from cortex2 import Cortex2
from aivolt_kb import find_answer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("cortex2.aivolt_chat")


class Cortex2AIVoltChat:
    """Fast AI Volt chat: KB-first, LLM-only-for-synthesis."""

    def __init__(self):
        self.cortex = Cortex2()
        self.messages: List[Dict[str, str]] = []

    def _llm(self, user_text: str, context: str = "") -> str:
        """Invoke BitNet (with Qwen fallback) for complex questions."""
        system = (
            "You are BitNet Cortex 2.0 AI Volt. Answer briefly using the AI Volt "
            "reference facts below. Do not suggest unsafe voltages.\n\n"
            f"{context}"
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_text},
        ]
        try:
            return self.cortex._request("bitnet", messages, "technical")
        except Exception as exc:
            logger.warning("BitNet failed; trying Qwen fallback: %s", exc)
            if self.cortex._health(self.cortex.endpoints["qwen"]["url"]):
                return self.cortex._request("qwen", messages, "technical")
            raise

    def _bridge(self, args: str) -> str:
        cmd = f"python3 aivolt/scripts/aivolt_bridge.py {args}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        out = result.stdout
        if result.stderr:
            out += "\n[stderr]\n" + result.stderr
        return out.strip()

    def _answer(self, prompt: str) -> str:
        # 1. Direct bridge command.
        if prompt.startswith("/bridge "):
            return self._bridge(prompt[len("/bridge "):].strip())

        # 2. Rule-based fact retrieval — instant.
        direct = find_answer(prompt)
        if direct:
            return direct

        # 3. Fallback to LLM with only a compact context snippet.
        context_path = Path(__file__).resolve().parent / "aivolt_context_compact.md"
        context = context_path.read_text(encoding="utf-8") if context_path.exists() else ""
        return self._llm(prompt, context)

    def show_help(self) -> None:
        print(
            "\nBitNet Cortex 2.0 AI Volt (fast mode)\n"
            "  /exit, /quit     Quit\n"
            "  /bridge <args>   Run aivolt_bridge.py directly\n"
            "  /help            Show this help\n\n"
            "Ask about wiring, pins, UART format, conversion, safety, commands, "
            "assessment, or troubleshooting. Most answers are instant.\n"
        )

    def run(self) -> None:
        self.cortex.start_bitnet_server()
        signal.signal(signal.SIGINT, lambda *_: self.cortex.stop() or sys.exit(0))
        signal.signal(signal.SIGTERM, lambda *_: self.cortex.stop() or sys.exit(0))

        print("BitNet Cortex 2.0 AI Volt ready (fast mode).")
        self.show_help()

        while True:
            try:
                prompt = input("\nYou: ")
            except EOFError:
                break
            prompt = prompt.strip()
            if not prompt:
                continue
            if prompt in {"/exit", "/quit"}:
                break
            if prompt == "/help":
                self.show_help()
                continue

            try:
                answer = self._answer(prompt)
                print(f"\nAssistant:\n{answer}")
                # Keep only the last few turns to avoid context bloat.
                self.messages.append({"role": "user", "content": prompt})
                self.messages.append({"role": "assistant", "content": answer})
                if len(self.messages) > 6:
                    self.messages = self.messages[-6:]
            except Exception as exc:
                print(f"\nError: {exc}")

        self.cortex.stop()


def main() -> int:
    Cortex2AIVoltChat().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
