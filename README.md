# BitNet4 — portable chat + AI Volt Lab integration

## You need the model

The BitNet 4 GGUF model (~1.2 GB) is **not in this repo** — it exceeds
GitHub's file size limit. Download or copy it into a `models/` folder:

```sh
mkdir -p models
# Option A: copy from a machine that has it
#   cp /path/to/BitNet4.gguf models/
# Option B: download the upstream BitNet b1.58 GGUF (the model this package
#   was built around) from Hugging Face:
#   https://huggingface.co/microsoft/BitNet-b1.58-2B-4T-gguf
# then verify against the frozen-runtime notes in README.txt.
```

The launcher, shared libraries, and hashes for them are included.

## Run the chat

```sh
./BitNet4            # interactive chat
./BitNet4 --debug    # with diagnostics
```

## AI Volt Lab files

`aivolt/` contains the AI Volt Lab integration: the Tang Primer 25K /
ADS1115 voltmeter project (`aivolt/aivolt-project/`, including the
FPGA bitstreams and meter Python), plus the Cortex 2.0 bridge scripts
(`aivolt/scripts/`).

Setup on a new machine:

```sh
# 1. put the bridge somewhere handy, e.g.:
mkdir -p ~/.local/bin/bitnet-cortex-2.0
cp -r aivolt/scripts/* ~/.local/bin/bitnet-cortex-2.0/
# 2. the voltmeter project folder the scripts expect:
cp -r aivolt/aivolt-project "$HOME/Desktop/a.i. tang engineering"
# 3. hardware hookup: Tang Primer 25K + ADS1115 on /dev/ttyUSB1
#    (see aivolt-project/AI_VOLT_LAB_HANDOFF.md)
# 4. run:
python3 ~/.local/bin/bitnet-cortex-2.0/aivolt_bridge.py diagnose
```

Note: the aivolt scripts were developed against this user's home
directory layout; the copies in `aivolt/scripts/` use relative paths
where possible, but check `aivolt_bridge.py` for any remaining
hardcoded paths before first use.

`aivolt/aivolt-project/voltage_fingerprints.sqlite3` is the fingerprint
database with saved readings (e.g. the `aaa` battery reference). It is
optional — the scripts recreate the schema automatically — but keep it
if you want the existing fingerprints.
