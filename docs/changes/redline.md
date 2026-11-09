# A9 and B3: pending Redline startup

## Reproduction

A9: complete fifth gear, qualify/start Redline with the Supercharger shot, then
drain while the introduction is still waiting. Official L5 can enter bonus and
later initialize multiball across a ball/player boundary. B3: arrange two locks
and overlap the third Hideout arrival with that same pending Redline introduction.
Test both Redline-first and ordinary-multiball-first sequences; also tilt/restart.

## Cause

The native drain/saver predicate duplicated an E2 task test but omitted pending
Redline task F2. Running Redline is subsequently renamed F3 by native startup.
A long pending introduction and a third lock can therefore compete for different
mode starts. Simply blocking all F3 activity would break intended single-ball
locks during Getaway Time.

## Change

At file `299FC`, replace the redundant predicate operand with F2. This protects a
ball during pending startup; it is not a permanent extra saver for running Redline.
The added routine at `2A:6FD0` saves D, calls the native task lookup with inline
word `00F2`, rejects while that task exists, otherwise restores D and delegates
to the numeric guard. Native lookup consumes the following inline two-byte task
identifier; those bytes are data, not two instructions. A clear carry means present.

Actual tilt and native restart cancel pending startup through native lifecycle
handling. KH5 does not replace that system with custom task deletion. Running F3
plus one live ball can still reach the numeric guard when lock qualification permits.

## Evidence and limits

Matched control research established the cross-boundary race. Immediate/later
startup drains, pending overlap, after-grace lock admission, multiplayer, tilt and
restart were tested on predecessors. KH5 reruns the affected named cases on its
own image. See [testing](../testing.md). Separate rare A4/A10 reports are not
claimed solved merely because this confirmed race is fixed.
