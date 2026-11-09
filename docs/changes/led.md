# LED lamp-matrix sequencing

The project uses the supported **V2** change in John Honeycutt's wpclp 1.4, not a
new generic patcher for every WPC OS. The accepted L5 baseline identifies exactly
the driver layout used here. The edit parameters and credit are in
[NOTICE](../../NOTICE.md); upstream source is pinned in [sources](../sources.md).

The driver must blank the relevant matrix output before changing the next
row/column selection and enabling it. The transformation changes the ordering
and register/source selection of existing matrix writes to ASIC registers
`3FE4` and `3FE5`. Its changed operands fall within file `7DCF5..7DD5B`.
The supported V2 operation is an in-place transformation; this release does not
silently search for free space and transplant another game's driver.

The implementation is [kh5patch/led.py](../../kh5patch/led.py). All offsets below
are relative to file `7DCF5`:

1. Verify the four indexed displacements at instruction offsets 31, 36, 42 and
   46 are below 128. Change indexed encoding to an 8-bit displacement and shift
   following owner-supplied bytes left once per instruction, freeing four bytes.
2. Change the final stores at relative offsets 97, 99, 100 and 102 to write
   the rows before columns.
3. Move relative positions 67 through 96 down three bytes, copying backwards
   so overlapping source bytes survive.
4. At relative 60, insert the seven-byte blanking sequence `CLRB; STB $3FE5;
   STB $3FE4`. This is the supported standard-delay V2 operation; the optional
   extra-delay variant is not used.

The public gameplay IPS and byte CSV intentionally exclude the LED driver.
Even a changed-byte-only full IPS would contain relocated native instructions.
Those instructions are read from the owner's ROM at conversion time instead.
The complete final before/after CSV can be generated privately with `--log`.
The original-driver signature arrays and full original routine are not published.
The converter then computes the final checksum only after all gameplay, LED and
branding edits. It does not accept an already LED-patched input.

ROM identity, native checksum and matrix/controller regressions were checked.
Actual ghosting depends on real LEDs, wiring and drivers, so physical LED behavior
remains a hardware check. The LED change itself does not modify DMD artwork/code;
this project separately changes the red-light effect pointer and revision label.
