# Runnable test catalogue

Use `tools/lab.py plan` to inspect a suite and `run` to execute it. All listed
counts are **generated cases**, not a claim they were all rerun on KH5. Historical
passes are recorded separately in [testing.md](testing.md) and the original
[evidence](../evidence/summary.json). Fresh port checks are documented in
[port-validation.md](port-validation.md).

| Suite | Cases | Contract / controller |
|---|---:|---|
| `calibration` | 1 | Independent 1,009-cycle waveform, nine forced sensor reads, raw-write sequencing; synthetic CPU fixture, no game firmware executed |
| `boot` | 1 | Real CPU checksum computation and success branch |
| `historical` | 913 | Published historical specifications, newly executed on explicitly selected images |
| `devices` | 74 | Stuck-open/closed sensors, failed mechanisms, fault observed by native code, repair and later lock |
| `donut` | 56 | Slow/fast passage beneath rear ramp, trap/search/lift, unchanged virtual locks, later collection |
| `endurance` | 60 | Flipper EOS faults, firing switches, hold/tilt/slam/restart shutdown and raw outputs |
| `multiball` | 723 | Shared inventory, regular/Burn Rubber/Redline, player ownership, lock counts and endings |
| `shared` | 80 | Regular shared-lock drain subset of `multiball` |
| `remaining` | 643 | Other 640 multiball combinations and 3 slow boundary variants |
| `shared-casual` | 12 | Shared-lock drain contracts with tournament explicitly off |
| `replay-awards` | 2 | Matched replay-threshold sequence, positive credit/knocker versus audit-only, five-ball/free-play |
| `features` | 12 | Mixed modes, positive Secret Mania extra ball, Special, casual awards, native menus/cold boot and video awards |
| `variants` | 128 | Authored deterministic replay variations: 34 canonical, 32 A9 boundaries, 21 shifter bursts, 25 B3 spacings, 16 seeded A1 timings |
| `ordinary` | 80 | 1–10 balls × 1–4 players × reference/extended timings, ordinary turns |
| `soak` | 1 | Forty continuous games alternating reference one-player and extended five-ball four-player; no emulator reset between games |
| `settings` | 23 | Published pairwise configuration rows through regular multiball; selected values read back |
| `countdowns` | 6 | Native Getaway/Supercharger countdown at selected 10/20/99 settings, expiry and cleanup |
| `search` | 9 | 0/1/2 virtual locks × missing-ball search stages 1/3/5, native recovery |
| `active-traps` | 2 | Trap during regular/Redline multiball, release and later lock after native grace |
| `entry-faults` | 4 | Right-passage sensor 17/18 forced open/closed, repair requires model lift before return contacts |
| `donut-long` | 3 | Long failed-lift/feedback trap and repair observations |
| `flippers` | 9 | Three flippers × normal/open/closed EOS, stroke/hold outputs |
| `b6` | 22 | State-aware third-gear histories/probes; observation only, can emit exact-input replay ledger |
| `pwm-unit` | 1 | 8,192 native vectors for the authored atomic stop routine; unit fixture, never burn |

These suites overlap. Do not add their row counts together as independent
coverage. `historical` is exactly `devices + donut + endurance + multiball`.
The 913 rows include official controls; a selected target replaces predecessor
candidate roles, while explicit official roles remain L5.

## What was exported

`research/` contains authored historical controller functions/classes and their
assertions, with private launchers removed. The source-hash provenance is in
[provenance.json](../research/provenance.json). Shared runtime adapters replace
private emulator paths and NVRAM dependencies. Lamp mapping, video trajectories
and other native data are read **locally from the owner's verified L5**, not
serialized into test fixtures. Native display checks use hashes only.

`lab/variants.py` ports the deterministic stimulus design. Published JSON contains
cabinet/switch inputs, frame budgets, small scalar assertions and numeric oracles;
large native buffer assertions were replaced by observations and explicit semantic
contracts. `6091` arrival-count differences are observations where the port
retains that established exception; mode-entry and owner-state requirements are
still checked. These exports are source ports, not byte-identical copies of old
private working directories.

`campaign_contracts.py` audits the 913 families independently of the controller:
image, emulator, seed and source hashes; bounded frames; allowed operator CMOS
writes; physical inventory; exercised faults; repair; actual mode entries;
owner return and raw coil edges. `release_contracts.py` checks positive feature
awards. Other suites retain controller assertions plus frame/output accounting.
The boot/PWM paths are explicitly CPU units; B6 completion is explicitly not a
proof of absence of a third-gear fault.

## How to extend

Choose the narrowest relevant suite and add a named deterministic specification.
Preserve input/frame order when comparing a race across images. Use independent
qualifiers for the consequence that matters; merely reaching the last controller
line is insufficient. A simulated mechanism fault must actually change a native
read, and a ball must pass model/return contacts after repair. One ordinary game
cannot prove an extra-ball award or extended timer works.

A new case should state initial settings, physical/virtual inventory, admission
and lifecycle predicates, mode/award assertions, cleanup and output observations.
Do not seed private gameplay RAM, write CPU state or reset mid-game to fabricate
success. Operator CMOS writes are allowed and logged; the native-menu cases use
actual cabinet inputs instead, and cold-boot persistence is a separate process.

Pulse reports retain digital command durations. The analyzer rejects opposing
ramp commands; matched summary comparison flags increases beyond an explicit
margin. Neither observation certifies physical coil energy or heat. Preserve and
investigate a timing flag rather than loosening bounds automatically.

The existing guard-equivalence, interrupt and LED-equivalence tools remain in
`tools/`. Their reference comparisons require owner-supplied images and/or a local
wpclp source build; see [testing.md](testing.md). The broad lab does not pretend
that an omitted external reference was tested.
