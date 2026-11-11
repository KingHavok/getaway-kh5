# Technical map for continuing research

These are numeric interfaces used by the L5-derived test adapters, not an export
of the Williams OS or a complete reverse-engineered source tree. Verify a new
candidate still implements them before applying the old oracle.

## ROM and bank translation

U6 is 512 KiB. The CPU's `4000..7FFF` window is bank selected by `3FFC`; the
fixed `8000..FFFF` region is the final 32 KiB (`78000..7FFFF` in the file). For the
logical game bank `2A`, the window maps to file `28000..2BFFF`. For example,
`2A:6091` is file `2A091`, and the authored guard at `2A:6F98` is `2AF98`.
Do not multiply a logical bank ID by 16 KiB without accounting for the WPC bank
mask. Consult the pinned PinMAME `src/wpc/wpc.c` for actual selection semantics.

`patches/kh5.asm` contains only the project's added 6809 routines.
`patches/edits.json` names each hook/data edit and why it exists.
`assembly-listing.json` and `changed-bytes.csv` describe the frozen authored
stage. The Python assembler is intentionally small and bank-2A-only. Unsupported
instructions/modes must fail; extend it with encoding/range tests or use a reviewed
external assembler. An FF-filled hole is a required check, not proof it is
unreferenced. Investigate references, bank boundaries and interrupt behaviour
before placing additional code.

The public IPS contains authored gameplay changes only. Building a complete image
then applies the owner-local LED transformation and native checksum. Final
before/after bytes can be logged locally; never publish that baseline-byte log.
The baseline and release identities remain pinned in `patches/release.json`.

## Observed RAM interfaces

| CPU address | Meaning used by the controllers |
|---|---|
| `040F`, `0410` | Current player and ball |
| `0411..0412` | Extra-ball state/counters used by directed award checks; interpret with their native call traces |
| `0416` | Playfield validation |
| `008C..008E` | Ball/bonus/tilt phase bytes; normal play is three zeroes in these adapters |
| `0805`, `0806` | Qualified-lock state and live-ball count |
| `0809` | Current RPM target observed by gear probes |
| `0903 + 0x36*p` | Player record, zero-based player index `p` |
| `0928 + 0x36*p` | Player's virtual lock credits |
| `092B + 0x36*p`, `092C + 0x36*p` | Player RPM and gear |
| `08E0..08E7` | Secret Mania flags/backup observations; use the existing traffic-light assertions |
| `0366`, `0371` | Task-chain heads used by inspection; next pointer at record start, task ID at offset `11` |
| `007C` | Low-power-bank output shadow; diverter-high is bit 0 |
| `00E6..00E7` | Native diverter PWM timer |

The player-record stride is 54 decimal bytes (`0x36`); CPU addresses in this
map are hexadecimal. The adapters traverse task chains with bounds/cycle checks. Lamp indices are
translated through the owner's native map at file `7E5FB`; no map table is bundled.
Video controllers similarly inspect owner-local native data rather than embedding
sprites or trajectory arrays. See the actual code for exact field interpretation.

## Named native entry points

| Bank:CPU | Observed role / use |
|---|---|
| `2A:6091`, `2A:6098` | Arrival path and admitted forced-lock continuation |
| `2A:6253` | Ordinary multiball initialization |
| `2A:6A88`, `2A:6AD4`, `2A:6ADF` | Redline entry, initialization and pending-to-running transition |
| `2A:59EA` | Saver/drain predicate containing the pending-Redline correction |
| `2A:56CB`, `56F3`, `5730`, `5776` | Secret Mania prep/game/result/cleanup observations |
| `2B:537A` | Surviving native Run the Red Light effect |
| fixed `86BF` | Native task lookup; consumes an inline task word; carry clear when found |
| fixed `8D29`, `8D30` | Boot checksum result and zero-difference success-branch checks |

`F2` is pending Redline, `F3` running Redline. The numerical one-ball/qualified-lock
guard plus pending-F2 guard retain the later single-ball Getaway lock path.
Secret Mania gameplay/result tasks `0138`/`0139` own the saved traffic lights;
repeated preparation must not overwrite their backup. The authored code preserves
caller register/stack contracts. Read the individual change explanations before
adding another guard, particularly if it could alter carry, interrupt masks,
continuation stack or `3FFC` bank state.

## Cabinet, simulator and fault inputs

The source of truth for switch numbers, input-port masks and mechanism IDs is the
pinned upstream `src/wpc/sims/wpc/full/gw.c`, plus the project's instrumented
`tools/pinmame/getaway_test.c`. Common controller inputs are Start mask `200`,
service Escape mask `10`, launcher port 1 mask `8000`, shifter port 4 mask `400`,
lock/ramp port 4 mask `6`, and orbit port 4 mask `12` (mask strings are hexadecimal).
These are simulator controls, not arbitrary writes to gameplay variables.

Direct numbered switch edges use `input`; simulated shots use `input/port`.
Do not assume directly toggling an opto also moves a physical simulator ball.
Physical Hideout/trough/launcher contacts and virtual lock credits must be observed
separately. The fault API can force sensor reads or model responses; clean sessions
assert no forced state at entry. Repair tests require native recovery and later
play, not merely removal of a fault flag.

## Operator settings used by tests

The authored `readiness_pairwise.CMOS` map names supported configuration words.
Important ones are balls/game `1B1F`, replay award `1B39`, tournament `1B51`,
restart `1B5F`, free play `1B9D`, Getaway timer `1BCB`, multiball percentage `1BD3`
and Supercharger timer `1BD5`. The common adapter sets the CMOS-write unlock at
`3FFD` to `B4`, writes aligned big-endian two-byte operator words, then relocks
with zero and reads back. No gameplay-variable writes are allowed in ordinary
qualification sessions. Native-menu/persistence tests cover the cabinet UI path
separately. Selected ranges are test vectors, not a complete replacement for the
manual's adjustment descriptions.

This map is sufficient to reproduce the existing controllers and start a directed
trace. It is not a full symbol map for rendering, audio or every scheduler entry.
When a feature needs an unmapped interface, trace it locally from the owner's ROM,
record a numeric calling contract and add positive controls; do not invent an OS
API from FreeWPC documentation or publish a Williams disassembly.
