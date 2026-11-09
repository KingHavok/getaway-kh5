# Contributions

Keep ROMs, captures, disassembly, original-byte logs, NVRAM and opaque debugger
payloads private. A PR may include original patch source, deterministic test
inputs, scalar results, hashes and a new cause/reproduction explanation.

A new firmware hash needs its own validation. Preserve old failures and distinguish
an invalid fixture from an observed game defect. Do not change an oracle merely
to turn a flag green. State the exact driver, image, settings, physical inventory,
CPU/sound configuration, input/frame order and assertions in a reproduction.

Any added public file must be reviewed and explicitly added to `PUBLIC_FILES.txt`.
Run the public scanner against the staged tree and reachable history. Do not use
`git add .` from a private ROM workspace, upload raw test folders or create a release
containing a built game image. Do not post raw buffers in GitHub issues.

Prefer a precise patch with unchanged native lifecycle/scoring over speculative
rule changes. Unreproduced A4/A10 reports remain leads; B6's expected-behavior
classification is an inference with a documented boundary.
