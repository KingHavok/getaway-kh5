# The Getaway: High Speed II — KH5

**Fixing reproduced bugs, restoring original features and adding LED support to
Williams' 1992 Getaway, built on official L5.**

The aim of KH5 is to bring together the most complete and reliable version of the
original Getaway experience: L5's later improvements, the missing **Run the Red
Light** sequence, **Secret Mania** with its confirmed state bugs corrected, and
fixes for multiball interactions that can reset progress or steal a mode. The original
rules, scoring progression, artwork, music and sound remain at the heart of it.

This started with research into decades of owner reports, ROM-version differences
and earlier community fixes. We worked through those reports, attempted to
reproduce them against official ROMs in PinMAME, traced demonstrated failures in
the 6809 code, and tested the fixes against the same scenarios. That process also
separated actual defects from normal rules, mechanical faults and reports we
could not reproduce. The [bug catalogue](docs/bugs.md) records the outcome for
each lead; the [technical notes](docs/changes.md) explain what changed and why.

## What KH5 improves

- **Multiball stays in progress.** Prevent repeated Hideout arrivals from starting
  ordinary multiball again and resetting jackpot/super-jackpot progression.
- **Protect Redline Mania startup.** Correct the drain-during-introduction race
  and exclude a competing ordinary-multiball start while Redline is pending.
  Preserve intended single-ball Getaway Time locks afterward.
- **Restore Run the Red Light.** Bring back the original word-by-word display and
  sound sequence using the routine still present in L5.
- **Keep Secret Mania working.** Retain the full mode and its nine-target
  extra-ball challenge; protect the traffic-light backup from repeated shifter
  pulls and restore it through tilt cleanup.
- **Restore native SLOW Game Re-Start.** Correct the Start-button edge so the
  existing hold-to-restart option can work.
- **Support matrix LEDs.** Apply wpclp's standard V2 anti-ghosting transformation,
  verified byte-for-byte against freshly compiled wpclp 1.4.
- **Correct diverter PWM cancellation.** Clear the timer and high-power latch
  together, addressing a defect found during the mechanism and coil investigation.
- **Allow Burn Rubber multiball to be disabled.** Permit zero as the minimum for
  the existing multiball-percentage adjustment, without changing its default.

L5's independent upper and lower right flippers, capped single-ball Supercharger
award and corrected Free Ride behaviour are retained. U18 sound is unchanged.
[Every patch is documented](docs/changes.md), including its addresses, cause,
reproduction and added assembly.

## Research and testing

The development campaign exercised
multiplayer lock ownership, different balls-per-game and timing settings,
interleaved multiballs, extra balls, tilt and restart, missing balls, stuck
switches, failed mechanisms, ball search and slow balls trapped beneath the
Donut Shop ramp. It also measured commanded coil pulses and checked recovery
after injected faults were removed.

| Test group | Completed coverage | Image / scope |
|---|---|---|
| Multiball and settings matrix | 720 configuration rows plus 3 slow variants | G6 predecessor and official controls |
| Device faults | 74 records | G6 predecessor and official controls |
| Under-Donut-ramp recovery | 56 records | G6 predecessor and official controls |
| Endurance | 60 records, plus separate evidence covering 1,200 ordinary/continuous turns | Predecessor campaign |
| Final feature and settings gate | 12 accepted contracts, including multiplayer, five-ball extended timings, extra balls, Specials and video awards | G6 predecessor |
| KH5 gameplay regressions | 12 targeted replays with the emulated sound CPU enabled | Exact KH5 release |
| KH5 native guard checks | 48 cases covering admission, pending/running Redline, D and stack | Exact KH5 code in unit fixtures |
| Direct guard comparison | 524,288 counter/register/flag vectors, plus 196,608 with the pending-mode wrapper | Native unit fixtures comparing KH5 code with the L5C numeric guard |
| Guard interrupt checks | 1,448 injected IRQ/FIRQ cases, including nested interrupts and the emulated WPC timer | 700 KH5 cases and 748 reference cases in native unit fixtures |
| LED equivalence | Complete LED-only output identical to wpclp; zero differences in KH5's 139-byte driver region | Exact KH5 release |
| Boot and conversion | Native ROM checksum passes; baseline, source reconstruction and final image hashes verified | Exact KH5 release |

The 913 records in the main historical campaign are [listed individually](evidence/historical-g6-cases.json).
G6 is the private predecessor to KH5. Its results retain the tested image
identity; the current KH5 checks are listed separately. See the
[test methodology](docs/testing.md) and [results summary](evidence/summary.json)
for the scope, controls, failures investigated and reproduction tools.

All listed release checks pass in emulation. Hardware validation is still pending.
The separate permanent-lockout report and some gear-loss reports remain
unreproduced; the reproduced temporary third-gear pause was closed as inferred
expected Getaway/RPM-gate behaviour. These are recorded openly in the catalogue.

## Build your own image

You supply your own authorized **official L5 U6 ROM**. The repository provides the
converter, authored patch, source and documentation; game and sound ROMs are not
distributed here.

Python 3.10 or newer; standard library only. Unzip your own raw U6 first:

```sh
python3 convert.py /private/path/GETAW_L5.ROM /private/path/getaway_kh5.bin
```

The converter checks the complete baseline identity, the IPS digest, an independent
build from the annotated source, the final image hash and the native WPC checksum.
Wrong, already patched, LED-only, prototype, truncated and ZIP inputs are refused.
It does not download a ROM, execute the input, or overwrite an existing output.

| Identity | Official L5 input | KH5 output |
|---|---|---|
| Bytes | 524288 | 524288 |
| CRC32 | `b97f3d62` | `b9ba49b9` |
| SHA1 | `c87c36a2327561c50b37d587d3bd0782acf8860d` | `7d65af17fb6297e7e434a6154f96647493c8460c` |
| WPC byte-sum / stored checksum | `4905` | `0F05` |

Full SHA256 identities and IPS SHA256 are in [patches/release.json](patches/release.json).
The checked-in IPS is the **gameplay stage only**, not a standalone burn patch.
Use the converter: it applies that stage, transforms the owner's LED driver
locally, and computes the checksum last. This avoids publishing native
instructions relocated by the LED correction. Only the verified final image is written.

For a PRIVATE, exhaustive before/after byte log generated from your own ROM:

```sh
python3 convert.py /private/path/GETAW_L5.ROM /private/path/getaway_kh5.bin \
  --log /private/path/kh5-byte-changes.csv
```

Do not upload that generated image or log. The public
[authored gameplay-byte table](patches/changed-bytes.csv) and
[added assembly](patches/kh5.asm) explain the published edits without shipping the
baseline's original byte ranges. LED relocation and checksum operations are
explained in [the LED notes](docs/changes/led.md) and converter source; every final
changed byte, including those operations, appears in the locally generated log.

## Revision and provenance

**KH5** identifies KingHavok's improved L5 project. The existing revision field
shows `REV. KH5`; the native checksum is `0F05`. This is an unofficial release.
The field-format detail is in [the branding notes](docs/changes/branding.md).

The public source includes [annotated assembly](patches/kh5.asm), an
[authored byte table](patches/changed-bytes.csv), original research notes and
reproducible test inputs. The detailed before/after log is generated locally from
the owner's ROM. [Credits and licences](NOTICE.md) identify Soren,
John Honeycutt/wpclp, PinMAME and the other work that informed this project.

## Development and publication

```sh
python3 -m unittest discover -s tests -v
python3 tools/check_public_tree.py
```

An optional local integration test uses `KH5_BASELINE=/private/path/GETAW_L5.ROM`.
CI has no ROM secret, never fetches game ROMs and never uploads game artifacts.
The [publication policy](docs/publication.md) describes the audited file boundary.
No DMD captures, audio, emulator executables, NVRAM or debugger dumps are included.
Repository licensing grants no rights to the proprietary game ROM.
