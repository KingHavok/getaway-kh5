# Test methodology, reproduction and results

The authoritative image identities are in `patches/release.json`. Evidence is
split into **KH5 executions**, **historical G6 executions**, **official controls**
and **inferences**. A prior pass is never silently relabelled with a new ROM hash.
See `evidence/summary.json` for completed counts and current release status.

## KH5 release checks

| Group | What is checked |
|---|---|
| Conversion | Exact baseline identity, minimal IPS, annotated-source reconstruction, output identity, stored/native checksum, every changed offset |
| LED equivalence | Fresh pinned wpclp 1.4 on official L5: whole LED-only image identical with matched reference metadata; KH5 driver region 139/139 bytes identical; [evidence](../evidence/led-equivalence.json) |
| Native boot | Actual WPC sum loop reaches its zero-difference success branch; private display observation reads REV. KH5 |
| Native guard | 48 isolated 6809 cases: 4 qualification counts × 4 live counts × absent/F2/F3 task state; D and caller/continuation stack checked |
| Direct numeric-guard differential | All 256 × 256 counter pairs in eight D/CC/native-phase profiles: 524,288 comparisons; plus 196,608 behind the same pending-mode wrapper; negative control detects a broken guard; [scope and evidence](changes/multiball.md#direct-comparison-with-sorens-numeric-guard) |
| A1/A3 | Lock/jackpot/super sequences; native entry counters reject repeated starts, preserve running Redline |
| A9/B3 | Immediate startup drain, after-grace admission, actual intro/third-lock overlap and extended timings |
| A12/F1 | Intended later one-ball lock/ordinary start, SLOW Start hold and pending-intro restart |
| Secret Mania | Four-pull guard, tilt cleanup, nine-target challenge/result progression, feature retained |

The 12 named gameplay inputs are in `tests/scenarios.json` and
`tests/scenarios/*.json`. `tests/oracles.json` contains only scalar states and
selected native callback counts. Embedded memory assertions are small numeric
phase/player/ball/gear/setting checks, not original ROM instruction assertions.

A native unit test is **not a played game**. It deliberately writes synthetic
scheduler records and CPU registers on a disposable local fixture. Gameplay tests
use normal switches/simulator inputs; only documented operator CMOS setup writes
are allowed. A reset is not used to teleport inventory mid-game.

## Reproduce locally

Supply your own authorized L5 and U18. No test tool downloads either.
A compiler, CMake, Git and SDL3 development installation are required to build
the research emulator; consult the pinned PinMAME project's platform instructions.
The helper targets macOS/Linux x64 and refuses an existing destination directory:

```sh
python3 tools/build_pinmame.py /private/path/pinmame-kh5
python3 convert.py /private/path/GETAW_L5.ROM /private/path/getaway_kh5.bin
python3 tools/replay.py \
  --emulator /private/path/pinmame-kh5/build/sdl3pinmame \
  --rom /private/path/getaway_kh5.bin --sound /private/path/u18snd \
  --output /private/path/kh5-tests --case core_a1_cold
```

Use `--case all` for the named suite. The runner owns fresh processes, refuses
an occupied debugger port, creates a native initialized seed through the game's
own first-boot acknowledgement, and copies that immutable seed into each case.
It enables the emulated sound CPU (`-nosound -fakesound`); no audible test is inferred.
The fixed emulated RTC is recorded in source. Frames are requested in bounded
budgets and must finish rather than halt early at a breakpoint.

Every raw capture, native trace, RAM snapshot and staged ROM stays under the
private output path. The runner compares public scalar/count oracles and embedded
assertions, and writes a compact numeric `summary.json`. Raw outputs are not safe
to publish simply because they are debugger files. An oracle mismatch is a flag
to investigate, not permission to update the expected result automatically.

```sh
python3 tools/run_guard_tests.py \
  --emulator /private/path/pinmame-kh5/build/sdl3pinmame \
  --rom /private/path/getaway_kh5.bin --sound /private/path/u18snd \
  --output /private/path/kh5-unit-tests
```

The unit helper creates `UNIT_ONLY_NEVER_BURN.bin` locally. It is intentionally
not the registered playable image, has a private bootstrap in unused space, and
must never be programmed into U6. No such fixture image is distributed here.

## Historical G6 campaign

The numeric, ROM-free `evidence/historical-g6-cases.json` records the 913 accepted
records and their settings/specifications, including official controls. The main
configuration coverage was 720 multiball rows plus three slow variants, 74 device
fault records, 56 Donut-ramp records and 60 endurance records. Other predecessor
evidence includes 1200 ordinary/continuous turns, operator boundary/countdown
checks, replay/no-knocker controls, sound-CPU paths and 8192 PWM-stop unit vectors.
Configuration rows are not a percentage of every possible state or shot order.

The later bounded G6 gate had 12 accepted contracts: continuous two- and four-player
sessions, Secret Mania extra-ball collection, eight-tunnel Special collection,
two casual Burn Rubber selections, two native menu profiles plus cold boots,
video completion and video extra-ball collection. The four-player profile used
five balls and extended timings. These positive award checks were not inferred
from ordinary drain-only turns with extra balls disabled.

The emulator fault interface can hold a switch open/closed and suppress a mechanism
response independently of the ROM's commanded output. Tests require proof that the
native code reads the injected state, then restore the peripheral and require
subsequent play/lock recovery. Raw CPU latch writes, not smoothed display values,
measure pulse intervals. The seven simulator slots are distinguished from the
three actually installed balls. Independent upper-right flipper input was also
calibrated in the model before interpreting flipper tests.

Under-Donut-ramp scenarios included fast/slow passages, repeated passages, locks,
multiball and ten-minute failed-lift/search controls. They check momentary release,
ball-search retries, inventory recovery and no opposing ramp commands. An actual
physical clearance/current/heat measurement cannot follow from that model.

## Failures and corrections retained

- Reusing a G6 seed for KH5 initially left the game at a native initialization
  prompt. Initialization was acknowledged and a fresh KH5 seed used; failed starts
  and runtime collisions were not counted as gameplay passes.
- An early G6 mixed-game oracle stopped at attract before returning a ball released
  from a physical lock. Its correction adds an ordinary drain and checks all three
  trough positions, rather than deleting/resetting a ball.
- A Secret Mania award helper wrongly required one live ball for a tunnel shot;
  the corrected case follows actual inventory and proves real extra-ball credit.
- Video controller attempts could crash or miss the adaptive target. Completion
  and actual extra-ball collection have separate positive controls; an attempted
  mode entry is not an award pass.
- An initial final coil comparison selected only a factory-matched subset. A
  reviewed correction used the complete already qualified G6 campaign, with the
  same margin and unchanged native output paths. No ROM edit or widened thermal
  threshold was used to hide that comparison mistake.
- A long-soak floating-clock residual was reviewed against an equal-frame CPU
  control. It is not permission to widen output-edge or physical safety limits.

The public summaries are derived measurements and commitments to retained private
artifacts. The raw dumps intentionally are not downloadable from this repo, so
those historical runs cannot be independently reconstructed from a hash alone.
The provided source, inputs and scalar oracles support fresh local execution with
an owner's own binaries. They do not claim exhaustive coverage, all historical
reports fixed, every monetary jackpot total checked, or a hardware-tested release.
