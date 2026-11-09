# Getaway KH5

**KingHavok's improved L5 game-ROM patch for Williams The Getaway: High Speed II.**
The machine displays **KH5**: the two initials replace the old revision letter and
hyphen in the existing field. This is an unofficial project, not a Williams/PPS release.

This repository distributes a converter, a small IPS patch, added patch source,
original research notes and numeric test summaries. **It contains no game or sound
ROM, DMD artwork, audio, emulator executable, NVRAM image or debugger RAM dump.**
You must obtain and retain your own authorized official L5 U6 image.

## Build locally

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

## Changes

- Prevent ordinary multiball from restarting on jackpot/Hideout arrivals.
- Protect pending Redline startup from an immediate drain and a competing third lock.
- Keep **Secret Mania**, including its nine-target extra-ball challenge; protect its
  first traffic-light backup and restore it through native tilt cleanup.
- Fix the Start-button edge that prevented native **SLOW Game Re-Start**.
- Restore the resident **Run the Red Light** effect; no L2 graphics/code are imported.
- Apply the supported **LED lamp-matrix ordering** correction.
- Stop the Supercharger diverter PWM timer and high-power latch atomically.
- Allow a zero minimum for the existing Burn Rubber multiball percentage adjustment.

L5's independent right flippers, capped single-ball Supercharger rule, ordinary
Getaway/lock behavior and U18 sound are retained. No arbitrary Super Jackpot cap
is added. [Technical change index](docs/changes.md) links each change to its
cause, reproduction, addresses, assembly and tests.

## Evidence and limits

Read [testing](docs/testing.md), [the complete bug catalogue](docs/bugs.md),
[history](docs/history.md) and [machine-readable evidence](evidence/summary.json).
A [direct comparison with freshly compiled wpclp 1.4](evidence/led-equivalence.json)
confirmed identical LED-only output and zero differences in KH5's lamp-driver region.
The large historical campaign ran on the private G6 predecessor. KH5 changes its
numeric guard implementation and branding; **historical G6 runs are not counted
as executions of KH5**. The release metadata and summary distinguish those runs
from KH5's native checksum, guard and targeted gameplay tests.

Emulation does not establish real ramp clearance, driver condition, current,
temperature, physical LED ghosting or audible sound. No hardware trial is claimed.
A separate permanent-lockout report remains unreproduced. The reproduced temporary
third-gear pause was closed as **inferred expected Getaway/RPM-gate behavior**,
not as proof that every historical third-gear report has been explained.

## Development and publication

```sh
python3 -m unittest discover -s tests -v
python3 tools/check_public_tree.py
```

An optional local integration test uses `KH5_BASELINE=/private/path/GETAW_L5.ROM`.
CI has no ROM secret, never fetches game ROMs and never uploads game artifacts.
[Publication policy](docs/publication.md) explains the allowlist and the limits of
what a ROM-free repository establishes. [Credits and licenses](NOTICE.md) identify
Soren, John Honeycutt/wpclp, PinMAME and the distinction between project code and
the proprietary game. Repository licensing grants no rights to the game ROM.
