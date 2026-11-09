# KH5 revision and checksum

The existing revision format allocates a revision letter followed by a hyphen,
then a formatted hexadecimal numeric suffix. KH5 changes only the two character
slots at file `70D5C..70D5D` to `KH`. The formatter and terminating byte stay in
place, and the checksum low byte is `05`. The result is **REV. KH5**, without
moving a string, changing a pointer or adding a second prefix elsewhere.

This is why the requested identity is written KH5, not KH-5. A private native
PinMAME display check observed that exact label; its artwork screenshot is not
published. The observed native byte-sum test computes `0F05` and reaches its
zero-difference success branch. No checksum test is bypassed.

Checksum construction sets the correction/checksum words to their neutral
values, sums all 524288 bytes modulo 65536, selects the revision low byte, then
writes the complementary correction bytes and checksum. `kh5patch/core.py`
contains the complete implementation; it verifies the result independently.
This is the same numeric checksum scheme used by the supported WPC OS.

KH5 is **not byte-identical to G6**: the original-source numeric guard, initials
and checksum differ. `patches/release.json` provides both identities. Historical
G6 results are kept separate from the specific KH5 executions. U18 is unchanged.
