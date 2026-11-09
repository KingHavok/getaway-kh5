# C2: keep Secret Mania and preserve its backup

## Reproduction

During the second-lock three-police-cars scene, make repeated quick shifter pulls.
The first native preparation copies the traffic lights, clears shared mode state,
and starts Secret Mania. Later preparations can overwrite that first backup with
cleared lights. Separately, hold TILT during the gameplay task or result task.
The native cleanup predicate looked for unrelated task IDs, so it could skip backup
restoration before gameplay tasks were killed.

## Fix, instruction by instruction

The hook at file `296C6` enters `secret_guard` at `2A:7000`.
`PSHS D,X` preserves the original inputs. Two native task lookups test `0138`
(the actual gameplay/preparation task) and `0139` (the result task). Finding either
returns via `PULS D,X,PC` without resetting the backup. On a first preparation,
`LDX #08E2` establishes the native accumulator pointer and `JMP 56CB` resumes the
resident prologue with its expected saved-register stack frame.

At `5AAD7` and `5AADE`, correct the native tilt-cleanup task identifiers to
`0138` and `0139`. The resident cleanup at `2A:5776` performs the actual restore.
There is no replacement native display, scoring, timeout or nine-target routine.
Task `0137` is a short shifter timer; treating it as the whole mode was an earlier
research mistake and is not the implementation.

## Feature preservation and tests

Secret Mania is **enabled**. A discarded earlier private build removed it; that
choice was reversed at the owner's request. Four pulls, normal timeout, nine-target
progression, held tilt during gameplay/result and multiplayer restoration have
matched predecessor evidence. The final G6 positive case also collected the lit
extra ball in the tunnel and observed the native counters increment. KH5 repeats
selected Secret Mania paths; the exact run list is in [testing](../testing.md).
Tournament mode forces the three-car trigger in deterministic challenge fixtures.
That does not prove every non-tournament entry timing or random scene selection.
