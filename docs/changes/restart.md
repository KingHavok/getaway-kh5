# F1: native SLOW Game Re-Start

Official L5's Start callback is entered on release. Its SLOW restart handler then
checks whether Start is still held, after the release has already happened.
The confirmed defect is narrower than the claim that no restart option ever works.

Reproduction: enable native SLOW Game Re-Start (A.1 33), reach ball two or later,
hold Start for the native interval, and observe whether a new game begins.
A first-ball press must still add players; short SLOW presses must not restart.

File `7516E` is a switch-handler flag byte. The patch selects the close/press edge
instead of the open/release edge while preserving the native phase-eligibility
bits. All timing, player-addition, pricing and restart handling remain native.
There is no Start-plus-flipper reboot feature.

Historical SLOW/short/FAST/OFF/priced/player-add tests pass on G5/G6. KH5 specifically
reruns SLOW and the pending-intro restart scenario; other historical cases are
listed as inherited evidence rather than new KH5 runs. See [testing](../testing.md).
