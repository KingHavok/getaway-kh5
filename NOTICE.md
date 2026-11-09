# Credits and licensing scope

Original converter, patch assembly, Python tests and project prose are supplied under
GPL-3.0-or-later; see [LICENSE](LICENSE). This grant covers project contributions,
not Williams/PPS game software, trademarks, sound, display assets or a generated
complete ROM. A patch-only distribution is not a claim of legal clearance to
modify or redistribute someone else's software. Use your own authorized input.

- **Soren, L5C / bc43:** identified the ordinary-multiball numeric guard and
  Secret Mania state defects. Earlier private G6 research used his 28-byte guard.
  KH5 supplies a new 25-byte implementation of the documented predicate, with a
  different register/stack arrangement. That ported 28-byte code and L5C image are
  not included. We credit the diagnosis and comparison, not ownership of his work.
- **John Honeycutt, wpclp 1.4:** the LED transformation code reproduces its supported
  V2 lamp-driver transformation. Its published source is GPL-3.0-or-later.
  No original-driver signature arrays or full driver implementation are bundled.
  Source: https://github.com/Pwedge/wpclp at
  `b0dcc64845847ebbdf8f5c39733dce7869ab13d4`. The upstream notices name
  Copyright (C) 2010 John Honeycutt. The GPL license and these credits accompany
  the derived LED transformation. Other wpclp versions/drivers are not claimed supported.
- **vpinball/PinMAME:** emulator used for native 6809 execution and game tests.
  Its source has file-specific BSD-3-Clause and inherited old-MAME licensing;
  it is not relicensed by this repository. No emulator binary is distributed.
- **Arakula/f9dasm:** private disassembly investigation tool. No disassembly of
  the original game is published here.
- **Keith Johnson and other community reporters:** reproduced descriptions and
  analyses informed the bug catalogue. Original posts remain with their authors;
  this repository uses original summaries and links, not copied forum archives.

Source revisions and primary links: [docs/sources.md](docs/sources.md).

The new C emulator instrumentation contributions have the separate BSD-3-Clause
notice in `tools/pinmame/CONTRIBUTIONS-LICENSE.txt`, to accompany the source-only
PinMAME patch. Upstream patch context retains PinMAME's file-specific licenses.
