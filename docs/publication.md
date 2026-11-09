# ROM-free publication boundary

The public tree is built from an explicit file allowlist. It is not a Git init or
filtered-history conversion of the private workspace. Before publishing, inspect
both the staged tree and every reachable Git object, not just `.gitignore`.

Allowed material:

- Original converter, added patch source and functional interface addresses.
- Authored gameplay-stage IPS records and byte listings, with provenance.
- SHA/CRC/checksum identities, original research prose and external source links.
- Original test inputs, scalar oracles, numeric measurements and evidence hashes.
- Source-only changes to the openly available emulator, with its separate license.

Excluded material:

- Complete or partial game/sound ROM images, archives, manuals and licence scans.
- DMD frames/video, fonts, graphics, sound data and emulator executables.
- Original-game disassemblies, baseline byte listings and old before/after CSVs.
- RAM, stack, tracepoint, savestate, NVRAM and opaque raw-log dumps. They can contain
  copied game strings, pointers or artwork despite not ending in `.bin`.
- Home-directory paths, credentials, private runtime files and downloadable ROM links.

The gameplay-stage IPS is verified locally against an owned baseline to contain
only authored changes, with no unchanged carrier ranges, LED driver payload or
checksum words. Merely omitting unchanged bytes is insufficient: a full LED IPS
would still embed native instructions relocated to different offsets. Therefore
Python performs that reordering using the owner's existing bytes, and computes
the checksum last. The checked-in IPS alone is not a complete burn conversion. The converter's detailed before/after CSV
is generated locally and kept private. The original Soren trampoline is excluded;
KH5 has original added source for the same functional predicate. wpclp-derived
LED transformation code carries their GPL provenance/credit. No blanket ownership of game or
third-party code is asserted.

This boundary establishes what files and payloads are published. It is not a
legal determination that a game licence permits modification or that every
functional patch is free of third-party rights. The repository licence cannot
grant permission for the generated complete game image.

CI receives no proprietary baseline and runs only public, synthetic tests.
Optional local integration uses a path supplied by the owner. There is no workflow
that uploads arbitrary test outputs, dumps or a generated ROM as a release artifact.
