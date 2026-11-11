# Developer-lab port validation — 11 November 2026

This change makes the existing authored research controllers portable and adds a
candidate-development workflow. **The qualified KH5 ROM is unchanged.** These are
harness validation results, separate from the historical G6 campaign and the
previously published KH5 release qualification.

The [numeric record index](../evidence/developer-lab-20261111.json) contains 33
completed records: 30 **PASS** and 3 **OBSERVED**. Four records are native boot,
PWM or independent calibration units; the others include overlapping gameplay
checks. These counts are not independent feature coverage or a percentage of
possible machine states. The source ports were validated incrementally; individual
controller, runtime, emulator and image hashes are retained where applicable.
Final whitespace-only source normalization was checked for identical Python ASTs;
the before/after hashes are recorded in `research/provenance.json`.

| Workflow / port | New verification |
|---|---|
| Fresh emulator | Pinned public source and instrumentation compiled using the public build helper; no game download |
| L5 → KH5 | Converter and unchanged-source candidate builder reproduce exact frozen KH5 |
| Different candidate | Private NEVER_BURN fixture with one authored NOP marker in FF fill; different hash compiled into `gw_lab`, native checksum and strict Secret Mania replay passed |
| Same bytes, different driver | Rebuilt KH5 under `gw_lab` passed; caches distinguish driver names even for identical firmware |
| Official L5 A1 control | Observed two multiball initializations, six admissions, no restored effect |
| KH5 A1 | One initialization, three admissions from six arrivals, one restored effect; fresh capture matched RUN / THE / RED / LIGHT / full phrase in order |
| Gameplay and settings ports | Representative device fault, Donut trap, flipper endurance, shared inventory, remaining multiball, ordinary turn, search, pairwise settings, A9, shifter-burst, active Redline trap and entry-sensor repair contracts passed |
| Positive awards | Real Secret Mania extra ball and native video extra ball collected; numeric counters and native award calls checked |
| Menu / cold boot | Kids five-ball, extended timing, free-play and audit-only replay menu profile survived a new process and started play |
| Timers | Native Getaway and Supercharger expiry at supported minimum 10, with the original decrement/cleanup assertions |
| Replay / casual multiplayer | Matched credit-versus-audit replay controls passed; first tournament-off shared-lock contract passed |
| Exact-input ledger | B6 external switch/frame ledger replayed across image identities; observations retained, not a bug-free pass |
| PWM | All 8,192 native stop-hook vectors passed; CPU fixture, not ordinary gameplay |
| Independent instrumentation | Two 1,009-cycle pulses measured at 0.0005045 seconds; nine ordinary/inverted/flipper forced-sensor read checks and raw-write sequencing passed; game firmware not executed by this unit |
| Public-only checkout | ROM-free checks, owner-baseline integration, exact conversion and generation of 913/128 catalogues work without private helper scripts or NVRAM |

The source-only Python suite now contains 27 checks. Two owner-baseline integration
checks are skipped in ROM-free CI; all 27 pass with the owner's verified L5.
The file-boundary scanner checks the explicit staged set and reachable history.
The optional owner-local payload audit also checks native game/sound substrings,
unchanged IPS carrier bytes and, when supplied, the original reference guard.
No proprietary game/sound files, DMD assets, NVRAM or debugger dumps are published.

## Retained setup failures and corrections

Failed attempts remain in private evidence rather than being replaced with new
passes. They exposed portable-harness issues, not additional game defects:

- Binary DMD responses needed a binary route instead of JSON decoding.
- A cache keyed only by image hash confused identical images under two drivers.
  The key now includes driver and hash.
- The shared-lock port initially omitted its owner-local lamp map, and its auditor
  assumed one owner-return snapshot shape. Both adapters were corrected.
- Concurrent first preparation could refuse an in-progress directory. A project
  lease now serializes mutable build, registration and test operations.
- One new timer fixture requested 1. The native game used its supported minimum,
  10, so the fixture failed correctly. Default generation now selects 10/20/99;
  the original assertions were retained and both minimum-timer follow-ups passed.

Ordinary runs now reject PinMAME checksum/length catalogue warnings. Expected
catalogue mismatches are confined to explicitly labelled CPU fixtures. All accepted
ordinary records were checked for those warnings, including records produced
before that additional runtime check was added.

## Evidence limits and audit bookkeeping

The 913 historical specifications and 128 generated variants are now runnable,
but **were not all rerun in this developer-port work**. Publishing a generator is
not a new pass. Settings coexistence, exact timer expiry, positive awards,
continuous ordinary games and fault recovery are separate contracts. The broad
historical outcomes keep their original firmware identity.

A4 permanent ramp lockout and separate A10 gear-loss reports remain unreproduced.
B6 remains closed as inferred expected Getaway/RPM gating. Digital coil commands
and CPU fixtures do not establish physical mechanism force, current or temperature.

A fixed-output private payload-audit helper reused an older summary filename during
this work. That file held derived publication checks: ROM identities, patch and
native-payload checks, permitted G6-to-KH5 differences, PASS status and a scanned-byte
total. It held no switch sequences, CPU traces, coil measurements or DMD captures.
The historical public findings, raw native test evidence and ROMs remain intact.

The [reconstructed audit record](../evidence/audit-reconstruction-20261111.json)
now revalidates those findings against the exact pre-handoff public commit
[`54db070`](https://github.com/KingHavok/getaway-kh5/commit/54db0704b8a435b9d62d838626e020c78f48c09e).
The retained original audit algorithm was rerun using the unchanged owner-local
reference images. Only the scanned-tree location and output destination changed.
All checks passed, and every one of the 11 audit fields retained in that commit's
public evidence matches the reconstruction.

The reconstruction scanned **1,517,647 bytes**. This figure belongs specifically
to that committed snapshot; it is not the original lost run's verified byte total
or the current repository size. The original summary's exact bytes and its precise
working-tree state remain unverified. This is a post-hoc reconstruction, not a
restored contemporaneous record. No gameplay evidence needed to continue testing
was lost, and this recovery adds no new gameplay qualification claim.

The published record contains numeric findings, hashes and explanatory prose only.
The private source archive, reference images and raw evidence remain outside the
repository. KH5 and its patch are unchanged. The public owner-local audit accepts
an explicit output path and refuses overwriting an existing report, so future
contributors do not need the old helper or its fixed destination.
