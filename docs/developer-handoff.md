# Developer handoff

A fresh checkout plus your own official L5 U6 is enough to reconstruct KH5 and
inspect every authored edit. Native tests additionally need your own matching
production U18. No conversation history, private NVRAM, extracted banks or old
emulator binary is required. This guide is the entry point for continuing bug
research or creating a new candidate; [the test catalogue](test-catalogue.md)
explains which generators to choose.

A [fresh remote-clone check](fresh-clone-validation.md) verified exact KH5
reconstruction, a new public-source emulator build and the listed short regression
set using only L5/U18 as supplied ROM inputs, with private-workspace reads blocked.
Its scope and numeric results are recorded separately from historical campaigns.

## Start with a private lab

Use Python 3.10+, Git, CMake, a C/C++ compiler and SDL3 development headers/library.
The tested build is macOS; the build helper also selects Linux. Windows is not
supported by the lab's POSIX process and workspace-lock helpers. macOS dependencies
can be installed with `brew install cmake sdl3`; use your platform's compiler tools.
The pinned PinMAME source is fetched from its upstream Git repository, never a ROM
site. An existing local Git clone can be supplied for an offline source build.
Run commands from the repository root. Replace the example private paths.

```sh
python3 tools/lab.py init --workspace /private/path/getaway-lab \
  --baseline /private/path/GETAW_L5.ROM --sound /private/path/u18snd
python3 tools/lab.py build --project /private/path/getaway-lab --jobs 2
# Optional offline source: append --local-source /private/path/pinmame-git
python3 tools/lab.py status --project /private/path/getaway-lab
```

`init` verifies the complete L5 identity and builds the exact KH5 release with the
same converter used by `convert.py`. It copies both U6 images and optional U18
into private inputs. U18 must have SHA1
`e6b7ccef250db0c801e3dd8ebf93522b466ca1ec` (CRC32 `37bbe485`). If omitted initially:

```sh
python3 tools/lab.py sound --project /private/path/getaway-lab \
  --file /private/path/u18snd
```

Static conversion/planning needs no sound. Emulation refuses to run without it.
A failed or interrupted initial emulator build can be resumed with `build` once
its owned-source marker exists; failures before that marker require a new private
workspace or removal of that incomplete source directory. Never remove a ROM
original. Native initialization creates an image/driver-specific NVRAM seed from
the actual game OS. Each test starts a fresh emulator and copies that seed; it
never imports a private development NVRAM image.

## First verify KH5 and the official control

```sh
python3 tools/lab.py run --project /private/path/getaway-lab --suite calibration \
  --output /private/path/instrumentation-calibration
python3 tools/lab.py run --project /private/path/getaway-lab --suite boot \
  --image kh5 --output /private/path/kh5-boot
python3 tools/lab.py replay --project /private/path/getaway-lab --image kh5 \
  --case all --output /private/path/kh5-release-replays
python3 tools/lab.py replay --project /private/path/getaway-lab --image l5 \
  --case core_a1_cold --observe --output /private/path/l5-a1-control
```

`boot` stops the real CPU at the native ROM-test calculation and success branch;
it does not bypass the checksum. The twelve release replays use published
assertions and scalar/count oracles. The cold A1 case also checks the five-part
red-light word sequence against hashes of locally captured pixel masks. No fonts
or DMD images are bundled. Official L5 runs are labelled **OBSERVED**: a known
control is not required to pass KH5's fixed-behaviour oracle.

The driver is `gw_l5` for the official control, `gw_kh5` for the frozen release,
and `gw_lab` for development. Candidate CRC/SHA1 metadata is compiled into the
owned source before testing. The input hash is checked again for each session.
Prepared input caches include both driver and image SHA256: identical firmware
under two driver names still has different filenames and NVRAM names.

## Build and test a development candidate

The frozen `convert.py` deliberately rejects a changed release build. Do not
change `patches/release.json` or relax its identity check to develop new code.
Use a separate authored-source directory instead:

```sh
mkdir /private/path/my-patch-source
cp patches/kh5.asm patches/edits.json /private/path/my-patch-source/
# Edit these two private source files; document each new reason and reproduction.
python3 tools/lab.py build-candidate --project /private/path/getaway-lab \
  --patch-dir /private/path/my-patch-source --name candidate \
  --output /private/path/my-candidate.bin
python3 tools/lab.py run --project /private/path/getaway-lab --image candidate \
  --suite boot --output /private/path/candidate-boot
python3 tools/lab.py replay --project /private/path/getaway-lab --image candidate \
  --case all --output /private/path/candidate-release-regressions
```

Omit `--patch-dir` to rebuild unchanged reviewed source: it must produce the exact
KH5 hash. Candidate output includes a source-hash/identity build report, an
**authored gameplay-stage** IPS and a private exhaustive before/after CSV. The
owner-local LED transformation and checksum follow the gameplay stage. Existing
outputs are never overwritten. The default numeric suffix remains 5; `--revision`
changes that byte for private experiments. The `KH` prefix is the separate authored
branding edit. A new identity is **UNQUALIFIED**, regardless of a valid checksum.

Alternatively register an already built raw image:

```sh
python3 tools/lab.py candidate --project /private/path/getaway-lab \
  --name trial --rom /private/path/trial.bin
```

Registration checks size and native checksum, then pins the full identity. It does
not prove that an arbitrary image shares L5's memory layout. The supplied adapters
assume an L5-derived candidate with the documented routines/state in place. A
feature that moves these interfaces needs a new layout adapter and its own
assertions, not silently reused addresses.

## Select and run directed campaigns

Inspect generated plans before starting a long run. These commands do not launch
an emulator or require U18 until `run`:

```sh
python3 tools/lab.py plan --project /private/path/getaway-lab --suite multiball \
  --image candidate --output /private/path/multiball-plan.json
python3 tools/lab.py run --project /private/path/getaway-lab \
  --work /private/path/multiball-plan.json --output /private/path/candidate-multiball
python3 tools/lab.py run --project /private/path/getaway-lab --suite devices \
  --image candidate --limit 1 --output /private/path/device-smoke
python3 tools/lab.py run --project /private/path/getaway-lab --suite features \
  --image candidate --case persist_kids --output /private/path/kids-menu-and-coldboot
```

`--work` contains explicit image names per case. Those names win over `--image`;
regenerate the plan when changing target. Historical official-control rows stay
on L5. Edit a private plan to select or extend a documented specification; it is
saved with the new results. Settings coexistence tests are not a substitute for
measuring timer expiry or positively collecting an award.

A project is leased exclusively during builds, registration and tests. Use a
separate private workspace and distinct `--port` for parallel workers. Do not
retarget a running emulator's candidate catalogue or edit test source mid-run.
Default port is 9070; HTTP is loopback only. The emulator is run with the emulated
sound CPU enabled, fixed RTC, bounded frame requests, raw output-edge tracing and
neutral fault instrumentation. Wall-clock duration is not emulated duration.

Every failed attempt is retained. New output directories must not exist.
`summary.json`, `qualification.json`, `launch.json` and `result.json` bind outcomes
to actual inputs, emulator, controller source, seed and frames. Raw traces, DMD,
RAM reads, NVRAM and generated fixtures stay private. Status means:

- **PASS:** the selected explicit contract completed and its assertions passed.
- **FLAGGED:** execution, fixture or contract needs investigation; not automatically
  a new game bug. Inspect the retained failure and raw evidence.
- **OBSERVED:** an official control or investigative run, not a bug-free claim.
- **EXPLORATION:** interactive debugging, with mutation permitted; never a gameplay
  qualification pass.

The PWM and guard CPU fixtures are unit tests. Their altered reset vectors and
`UNIT_ONLY_NEVER_BURN` images must never be programmed into a machine.

## Continue a bug investigation

Start with [bugs.md](bugs.md), the individual [change explanations](changes.md),
[research sources](sources.md) and [the technical map](technical-map.md). Preserve
Secret Mania and its nine-target challenge, native scoring/lifecycle, independent
right flippers, and the intended Getaway Time lock path. Normal free-play and
multiplayer use, five-ball children's games, extended timings and replay-award
disabling are important profiles; they do not replace testing other settings.

A useful reproduction names image/hash, settings, player/ball, physical ball
inventory, shot order and exact frame gaps. Demonstrate the failure on official
L5, preserve its inputs, trace the competing tasks/branches and explain the cause
before changing code. Use the same inputs on the candidate and add a positive
follow-up: a lock should work after repair; an award must actually be collected;
a timer must expire; a mode must really have started.

For a raw scripted extension use `replay --script /private/path/scenario.json`.
Actions match `tests/scenarios/*.json`: `frames`, API calls and small
`assert_memory` observations. A custom script without an oracle or assertions is
only observed. `--expect` accepts a private scalar/count oracle; never update it
merely because a candidate differs. For state-aware tests add a controller and
independent contract rather than copying private buffers into JSON.

```sh
python3 tools/debug_lab.py --project /private/path/getaway-lab --image l5 \
  --output /private/path/exploration
```

The console accepts JSON lines such as
`{"path":"debugger/memory","params":{"addr":"0805","size":2}}`,
`{"path":"debugger/tracepoints","params":{"cmd":"add","addr":"6253","bank":"2A"}}`,
`{"frames":120}` and `{"finish":true}`. The tracepoint buffer holds 512 entries;
a full buffer requires a shorter window, not acceptance of a truncated trace.
All output remains private. See the
pinned emulator's `src/remote_debug/api_handler.c` for route and breakpoint
schemas; inspect its source instead of guessing request parameters.

The `b6` suite emits an external-input `stimulus.json`. Replay the exact stimulus
on another image rather than allowing a state-aware controller to choose new shot
timings:

```sh
python3 tools/lab.py run --project /private/path/getaway-lab --image l5 \
  --suite b6 --case b6-baseline --output /private/path/l5-b6
python3 tools/lab.py replay --project /private/path/getaway-lab --image candidate \
  --ledger /private/path/l5-b6/b6-baseline/stimulus.json \
  --output /private/path/candidate-b6-exact
```

B6 is closed as **inferred expected Getaway/RPM gating**, not a verified permanent
jam or a new fix. Permanent ramp lockout A4 and separate A10 gear-loss reports
remain leads. New evidence may reopen them; do not advertise them as solved.

For pulse comparisons, run identical case IDs/specifications on reference and
target, then use `tools/compare_lab.py --reference .../summary.json --target
.../summary.json --output /private/path/comparison.json`. It flags failed or
unmatched contracts and observed maxima beyond the explicit margin (default
10 microseconds). Raw latch edges and physical-current measurements answer
different questions. Never widen a margin to hide a flag. No emulator test
certifies physical ramp force, coil current or temperature.

## Publish a reviewable change

Add the reproduction, cause, authored patch, regression inputs and numeric outcome.
Keep imported historical passes attributed to their original image; published
generators alone do not establish fresh KH5 or candidate passes. See
[test-catalogue.md](test-catalogue.md) and [port-validation.md](port-validation.md).

```sh
python3 -m unittest discover -s tests -v
# Optional owner-local integration, never CI secrets:
KH5_BASELINE=/private/path/GETAW_L5.ROM python3 -m unittest discover -s tests -v
python3 tools/check_public_tree.py
python3 tools/audit_owned_payload.py --baseline /private/path/GETAW_L5.ROM \
  --sound /private/path/u18snd --output /private/path/new-payload-audit.json
# Optional owned reference check: append --l5c /private/path/GETAW_L5C.ROM
```

Review every added file and update `PUBLIC_FILES.txt` explicitly before staging.
The scanner checks the file boundary, authored IPS and reachable Git blobs. The
optional owner-local audit additionally rejects unchanged IPS carrier bytes and
nontrivial native game/sound substrings; an owned L5C adds a guard-payload check.
Its output path is explicit and never overwritten. It is
one layer, not a licence determination: also review source/fixtures for native
byte arrays, artwork, sound, NVRAM, private paths and original-byte logs. Retain
only source we can publish, numeric observations and hashes. The LED driver is
reconstructed from the owner's image locally; no relocated Williams routine is
distributed. Original Soren routine bytes likewise remain outside the repository.
