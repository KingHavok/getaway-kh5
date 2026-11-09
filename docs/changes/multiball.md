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

## Direct comparison with Soren's numeric guard

On 9 November 2026, an additional native 6809 differential test compared the
rewritten routine with the 28-byte reference extracted locally from an owner's
hash-verified L5C image. No reference routine or fixture ROM is distributed.

All 256 qualification-byte values were crossed with all 256 live-ball-byte
values, including high-bit values, zero, and the decrement's signed-overflow and
wraparound boundaries. Eight caller-D/CC/native-phase profiles produced
**524,288 passing comparisons**. A further **196,608 comparisons** put both
numeric implementations behind the same KH5 wrapper, with absent, pending-F2
and running-F3 task states. Both sets passed with no mismatches.

The comparison checks admission against the reference and an independent
predicate, CC, D, DP, X, Y, U, stack pointer, and the accepted saved-D frame. It
retains the real native `6EC6` predicate and, for wrapper tests, the real task
lookup. Synthetic inputs are read back before execution. A deliberately broken
candidate is detected at qualified=1/live=1, proving the comparator flags an
admission mismatch. [Numeric evidence](../../evidence/guard-equivalence.json)
records the exact scope and input/fixture/tool hashes.

This establishes the tested functional contract, not cycle identity. From the
pinned 6809 core's cycle table and push/pull byte costs, the rewrite adds two
cycles on admission and saves fifteen on either numeric rejection path. At
2 MHz those differences are +1 microsecond and -7.5 microseconds respectively.
Unused stack bytes and internal return addresses also differ. IRQ/FIRQ are
masked in these isolated fixtures, the caller uses normal DP=0, and the eight
register/flag profiles do not enumerate every CPU state or interrupt arrival.

The pending-F2 exclusion is an intentional KH5 addition. Comparing both guards
behind that same wrapper tests the rewrite's compatibility with it; it does not
claim that KH5 and unmodified L5C have identical rules in every state.

To repeat the differential test, supply your own KH5, L5C reference and U18:

```sh
python3 tools/compare_guards.py --emulator /private/path/sdl3pinmame \
  --rom /private/path/getaway_kh5.bin --reference /private/path/getaway_l5c.bin \
  --sound /private/path/u18snd --output /private/path/guard-comparison
```

Use `--pending-wrapper` in a fresh output directory for the task-state comparison,
or `--negative-control` for the deliberate-fault check. All generated fixtures
are private **UNIT_ONLY_NEVER_BURN** images; they are not playable releases.

## Interrupt safety investigation

The original counter matrix masks IRQ/FIRQ. A separate investigation on
9 November 2026 tested interruptions explicitly and found no failure requiring
a change to the released ROM. [Evidence](../../evidence/guard-interrupts.json)
records **700 KH5 cases and 748 reference cases**, all passing. The reference uses
Soren's numeric routine behind the same pending-mode wrapper; its extra
instructions account for the different number of injection points.

The numeric guard does not change the IRQ/FIRQ mask bits. The additional two
cycles on admission are ordinary CPU work, not an added critical section.
Interrupts are taken at instruction boundaries, so a push/pull instruction is
not interrupted halfway through a register transfer. Even the gap between the
rewrite's `PULS D` and `PSHS D` has a valid caller return address on the stack.
That gap is included in the tests.

The initialized native IRQ path saves the full CPU context and returns through
RTI. The active DMD FIRQ path explicitly saves A, which the rewrite temporarily
uses for its comparisons. The default high-resolution timer FIRQ callback
acknowledges its source and returns. The inspected IRQ paths service I/O,
switch buffers, flippers and PWM, then return; they do not dispatch another
gameplay task. No guard-input changes were observed in the tested paths.

The unit fixtures first boot the native OS and establish the ordinary code-bank
shadow as well as the ASIC bank before entering the real hook. The native IRQ
restores that shadow; a fixture that sets only the ASIC bank would not model the
caller's bank contract correctly. The tests check the actual selected bank and
its visible guard bytes after each interrupt.

At every visited instruction boundary in the hook, wrapper, numeric guard,
shared phase predicate and task-lookup interface, four cases execute:

1. IRQ asserted through the debugger's CPU pending-line state.
2. DMD FIRQ asserted the same way.
3. Timer FIRQ raised by the actual emulated WPC high-resolution timer.
4. IRQ followed by a nested DMD FIRQ before the IRQ handler proceeds.

The unmodified CPU core builds each interrupt frame; entry vector and frame size
are checked before the unmodified native handler runs. Return must preserve
PC, SP, D, DP, X, Y, U, all non-E CC bits, guard inputs and code bank. E is the
6809 hardware frame-format flag: IRQ forces it set in the saved frame and FIRQ
clears it. This expected difference is normalized; arithmetic flags and interrupt
mask bits are checked exactly against the requested pre-interrupt state.

The eight scenarios include zero qualification, zero/two live balls, the signed
overflow boundary, high-bit/max qualification, pending F2 and running F3. They
also exercise inactive and active native PWM timer values. Final admission,
caller D and the continuation/return stack contract must remain correct.

These are isolated CPU fixtures, not played games or hardware trials. Scheduler
search internals execute normally between the tested lookup-interface points.
The tests cover the initialized normal IRQ, DMD and timer callbacks, not every
arbitrary callback configuration, NMI, corrupted pointer or interrupt/device
combination. They complement the IRQ/FIRQ-enabled KH5 gameplay regressions.

To reproduce, provide your own qualified KH5, U18 and optional L5C reference:

```sh
python3 tools/test_guard_interrupts.py --emulator /private/path/sdl3pinmame \
  --rom /private/path/getaway_kh5.bin --sound /private/path/u18snd \
  --reference /private/path/getaway_l5c.bin --output /private/path/guard-interrupts
```

All generated fixture images remain private and are **UNIT_ONLY_NEVER_BURN**.
