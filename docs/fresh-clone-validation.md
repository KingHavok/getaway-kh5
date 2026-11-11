# Fresh remote-clone validation — 11 November 2026

**PASS:** a fresh public clone plus the owner's official L5 and production U18
reconstructed the exact published KH5 image and ran a bounded native regression
set without private helpers, an old emulator or imported NVRAM. No code, oracle
or firmware changes were needed.

The tested public commit was
[`260841b`](https://github.com/KingHavok/getaway-kh5/commit/260841bb00eb898393fc67d946939fb1f7542cc4).
This page publishes that run's results; it does not change the tested commit or
replace the earlier [port-validation](port-validation.md) and historical evidence.
[Numeric outcomes and source/evidence hashes](../evidence/fresh-clone-20261111.json)
identify exactly what ran. Raw receipts remain private.

## Build and isolation

The project was cloned from public GitHub into a new directory. The only supplied
ROM inputs were official L5 U6 and matching production U18, with identities recorded
in the numeric summary. The public `tools/lab.py init` checked them and reconstructed
KH5. Its output matched the complete frozen release identity:

| Property | Rebuilt KH5 |
|---|---|
| Bytes | 524288 |
| CRC32 | `b9ba49b9` |
| SHA1 | `7d65af17fb6297e7e434a6154f96647493c8460c` |
| SHA256 | `e27ce97d13f96510b0a21f0251c314761e66beb417c677f1f1984166fc94bd61` |
| WPC checksum | `0F05` |

The unmodified public build helper fetched upstream PinMAME and checked out
`47ac466023e488e1cbeb19448fa3f56ff9cc8788`, applied the public instrumentation and
compiled a new emulator. No `--local-source` option or pre-existing PinMAME
executable/build objects were used; the compiler cache was disabled. The executable's SHA256 was
`70c1bd0553c4439f05ad81fb3bee42d3aff61f7036a4a9d6e06563732509c513`.

A macOS child-process sandbox denied reads of the original private project
workspace during conversion, compilation and tests. Read-denial probes passed
before and after the run. The processes used a clean environment and child home,
Python user-site loading was disabled, and the two standard system PinMAME
configuration files probed were absent. The normal installed compiler, CMake and SDL3 were available:
this was a fresh-checkout test on macOS 26.6.2/x86-64 with Python 3.15.2, not a
bare-OS installation or a cross-platform verification.

The game OS generated a new NVRAM seed in the isolated workspace. Each gameplay
replay used a fresh emulator process and its own copy of that seed. Seed integrity,
image identity, emulator hash and script/source hashes were checked. The cloned
project's tracked files remained unchanged throughout the run. Shell commands
only sequenced the public tools; no private gameplay/controller code was imported.

## Exactly what passed

All **27 Python checks passed with the owner's L5**, with zero skips. A separate
ROM-free execution passed 25 and skipped the two owned-input integrations. These
are two executions of the same suite, not 52 distinct tests.

Three native checks passed separately from gameplay:

| Check | Passed contract |
|---|---|
| `calibration` | Independent synthetic CPU program: two 1,009-cycle pulses measured approximately 0.0005045 seconds each, nine ordinary/inverted/flipper forced-sensor read combinations and raw-write sequencing. It did **not** execute KH5's game program. |
| `boot` | Actual KH5 native reset checksum computation and success branch at `8D30`, with checksum `0F05` and no checksum bypass. It uses resume/breakpoints, so its zero bounded-frame count does not mean it was skipped. |
| `pwm-unit` | 8,192 native authored stop-hook vectors: 256 output shadows × eight condition-code values × four timer values. CPU fixture only; not gameplay or an interrupt-injection campaign. |

Five KH5 gameplay replays passed their existing memory assertions and published
scalar/native-callback oracles:

| Published case | Frame budget | Memory assertions | Tested sequence |
|---|---:|---:|---|
| `core_a1_cold` | 16270 | 3 | Lock/jackpot multiball sequence and native callback counts; restored red-light display order |
| `core_a9_immediate_expiry` | 19372 | 11 | Drain/saver-expiry race around the pending Redline introduction |
| `core_b3_intro_overlap` | 15034 | 5 | Ordinary-lock admission while the Redline introduction is pending |
| `secret_tilt` | 4972 | 3 | Retained Secret Mania and traffic-light cleanup through the scripted tilt |
| `core_f1_slow` | 5682 | 14 | Native SLOW Game Re-Start path |

The five gameplay budgets total **61,330 emulated frames**. That excludes native
initialization and unit execution and is not an elapsed wall-clock measurement.
The emulated sound CPU was enabled. No oracle was changed or bypassed to obtain
a pass.

A1 also checked a freshly captured DMD recording against the published pixel-mask
hashes. It matched RUN, THE, RED, LIGHT and the complete phrase in that order.
Only the derived match result and frame indices are public; no captured pixels,
fonts or display assets are included.

The fresh clone's public-file/history boundary check passed. Its optional
owner-payload audit passed using L5 and U18 only: zero nontrivial 96-byte game/sound
matches and zero unchanged IPS carrier bytes. No L5C reference was supplied, so
that optional reference-guard comparison was **not** run. The numeric report's
publication file/blob counts describe tested commit `260841b`, not the later
commit adding this page.

## Reproduce the same selection

See the [developer handoff](developer-handoff.md) for prerequisites. Replace the
private example paths; all inputs and outputs must remain outside the repository.
Use new output directories on a repeat run. The core commands below reproduce the
selection; the additional OS isolation wrapper was specific to this verification.

```sh
set -e
git clone https://github.com/KingHavok/getaway-kh5.git
cd getaway-kh5
git checkout 260841bb00eb898393fc67d946939fb1f7542cc4

python3 tools/lab.py init --workspace /private/path/fresh-lab \
  --baseline /private/path/L5.u6 --sound /private/path/u18snd
python3 tools/lab.py build --project /private/path/fresh-lab --jobs 2
KH5_BASELINE=/private/path/L5.u6 python3 -m unittest discover -s tests -v

for smoke_suite in calibration boot pwm-unit; do
  python3 tools/lab.py run --project /private/path/fresh-lab --image kh5 \
    --suite "$smoke_suite" --port 9090 \
    --output "/private/path/fresh-results/$smoke_suite"
done

for smoke_case in core_a1_cold core_a9_immediate_expiry core_b3_intro_overlap secret_tilt core_f1_slow; do
  python3 tools/lab.py replay --project /private/path/fresh-lab --image kh5 \
    --case "$smoke_case" --port 9090 \
    --output "/private/path/fresh-results/$smoke_case"
done
```

## Scope and privacy

This verifies the public reconstruction/build workflow and the **listed eight
native records**, of which five are gameplay replays. The full twelve release
replays, 913 historical specifications, 128 synthetic variants and broader
feature/multiplayer/settings/fault campaigns were not emulated in this check.
Different-hash development candidates and L5C/wpclp reference comparisons were not
part of this run. L5 was the conversion baseline; no official-L5 gameplay negative
control was rerun. The existing firmware and bug dispositions are unchanged.
There is no new physical-hardware qualification or claim of universal bug freedom.

The public record contains selected hashes, counts, outcomes and original prose.
ROMs, generated fixture images, emulator binaries, build objects, NVRAM, RAM/CPU
traces, action/output logs, DMD captures, local paths and the actual sandbox profile
remain private. CPU fixtures are never burn images. Raw evidence was archived
privately after testing; it was not copied into the public repository.
