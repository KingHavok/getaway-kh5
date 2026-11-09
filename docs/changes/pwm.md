# Atomic Supercharger diverter stop

## What testing found

A cancellation during the PWM on portion could clear the native timer without
clearing the actual high-power latch. Investigation of the predecessor observed
an approximately 819 ms high interval in the affected path. A timer reaching zero
is not proof that the output bit has gone low. This was found during the project's
hardware-oriented fault/coil work, separate from the older community bug catalogue.

## Patch contract

The call at file `2ACC8` invokes `pwm_stop` at `2A:7040`. The added routine saves CC,
masks IRQ and FIRQ, clears timer E6/E7, clears only bit 0 of shadow `007C`, writes
that shadow to hardware latch `3FE1`, restores CC, then establishes the native
return D=0 and N/Z/V effects. It preserves original interrupt masks and carry;
seven unrelated output bits remain unchanged. Clearing only the timer or only
the software shadow would be incomplete.

The assembly source explains every instruction. The complete PWM routine bytes
are unchanged between tested G6 and KH5; the independent private delta audit
limits KH5's gameplay-code difference to the new numeric multiball guard.

## Evidence and physical limits

The predecessor's native unit fixture checked 8192 combinations of shadow bits,
CC masks and timer values. Additional phase controls exercised cancellation in
high/low slices and checked raw latch writes. The historical campaign also covered
stuck switches, failed mechanisms, ball-search and trapped-under-ramp recovery.
These are original-image emulation tests, not measurements of coil current,
thermal rise, physical ramp force, mechanical clearance or worn drivers.
