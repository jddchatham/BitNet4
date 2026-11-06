BitNet 4 portable chat
======================

Run:
  ./BitNet4

Debug diagnostics:
  ./BitNet4 --debug

Normal mode disables runtime logging so the terminal shows the interactive
conversation only. The frozen BITC4 diagnostics remain available in debug
mode.

This package contains the frozen Phase 20B.2 runtime, its shared libraries,
and the BitNet 4 GGUF model. It is intended for a compatible 64-bit Linux
machine with the required runtime libraries and CPU support.

The launcher keeps the external tied-weight and single-buffer transformer
configuration enabled. It does not include or use the experimental
two-buffer Phase 22C build.

Frozen runtime hashes:
  llama-cli  67b0d64cbb8e39b6995755ec6d7c2c1a81bb0b02eb0e86ce14a15573b1142d15
  libllama  5a87e6020a099ebc3344a937a05a2122eb82ef383e40a601ba11ce877c9d2c4c

The model file is BitNet4.gguf. The original model is not modified.
