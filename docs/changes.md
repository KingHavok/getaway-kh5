# Technical change index

All file offsets are zero-based in a 512 KiB raw U6. Bank values are the logical
values written to the WPC bank register. For bank `2A`, CPU `4000..7FFF` maps to
file `28000..2BFFF`. Fixed CPU `8000..FFFF` maps to file `78000..7FFFF`.
A CPU address without its bank can refer to a different physical byte.

| Change | File offsets / new routine | Detailed explanation |
|---|---|---|
| A1/A3 numeric admission | hook `2A091`; code `2AF98` / `2A:6F98` | [Multiball guard](changes/multiball.md) |
| B3 pending-mode exclusion | code `2AFD0` / `2A:6FD0` | [Redline races](changes/redline.md) |
| A9 drain during Redline introduction | predicate operand `299FC` | [Redline races](changes/redline.md) |
| C2 repeated prep / tilt | hook `296C6`; code `2B000`; IDs `5AAD7`, `5AADE` | [Secret Mania](changes/secret-mania.md) |
| F1 Start edge | switch table `7516E` | [Restart](changes/restart.md) |
| Red-light display restoration | effect pointer `76A37..76A38` | [Display](changes/display.md) |
| Burn Rubber zero minimum | adjustment field `7621A` | [Multiball guard](changes/multiball.md) |
| LED matrix | owner-local transformation within `7DCF5..7DD5B` | [LED](changes/led.md) |
| Diverter PWM stop | call `2ACC8`; code `2B040` / `2A:7040` | [PWM](changes/pwm.md) |
| KH5 identity/checksum | `70D5C..70D5D`, `7FFEC..7FFEF` | [Branding](changes/branding.md) |

`patches/kh5.asm` contains every newly added instruction with inline explanations.
`patches/assembly-listing.json` maps each instruction to its encoding and address.
`patches/edits.json` describes authored hook/data replacements.
`patches/changed-bytes.csv` enumerates authored gameplay-stage bytes only.
`kh5patch/led.py` specifies the owner-local driver transformation;
`kh5patch/core.py` computes the final checksum. `convert.py --log` generates
every final before/after change locally, including relocated native bytes.

The converter reconstructs this source and separately applies the checked-in IPS,
then refuses to emit an output unless those two paths and the expected release
hash agree. It also verifies that each added routine occupies actual `FF` fill in
that exact baseline. No broad search for apparently free space or relocation is attempted.
