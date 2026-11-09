# A1: multiball admission and progressive awards

## Reproduction and observed failure

On official L5: lock three balls, collect jackpot, then two super jackpots. Every
third subsequent Hideout arrival can enter ordinary multiball again: balls return,
saver restarts, jackpot/loop state resets. A related control locks two balls,
starts Redline, then shoots the jackpot: the third arrival can demote the mode.
These are A1 and the A3 manifestation; not every B1/B3/A13 report is automatically
classified as the same cause.

## Cause and contract

L5's lock-arrival path can admit ordinary multiball during an already active
multiball. The numeric gate is: a lock must be qualified (`0805 != 0`) and exactly
one ball must be live (`0806 == 1`). A separate pending-F2 test protects startup.
Do not reject every running Redline/Getaway task: a qualified single-ball
last-chance lock is intended to permit an ordinary multiball (A12).

## Implementation

The hook at file `2A091` jumps to `2A:6FD0`, which checks pending F2 and then
enters `numeric_guard` at `2A:6F98`. KH5's **new** numeric routine uses A for the
loads and decrement, while saving D once. A reject restores D and returns to the
original caller. An accepted path restores D, establishes the displaced native
saved-D stack frame, calls resident `6EC6`, then continues at `6096`.

Each load/decrement has the same N/Z/V effects as the B-register form previously
studied. Carry is not changed by those instructions. Native CPU tests check both
admission and the D/stack contract. This is not a verbatim copy of L5C's trampoline.
The last three bytes of that formerly used 28-byte slot stay baseline `FF`.

The adjustment edit at `7621A` changes only the minimum of A.2 13 Multiball
Percent to zero; its default remains 20. This supports intentionally excluding
multiball from casual Burn Rubber selection without imposing that choice.

## Evidence and bounds

Historical matched L5 controls reproduce the restart; predecessor fixes reject
repeated entries. KH5 has separate native guard and A1/A3/B3/A12 replay evidence.
[Testing](../testing.md) identifies the exact image and case names. The historical
720-row multiplayer matrix belongs to G6, not KH5. Progressive super jackpots are
retained; no new arbitrary scoring cap is imposed. The final mixed G6 tests verify
award progression and no restart, not every monetary payout under every setting.
