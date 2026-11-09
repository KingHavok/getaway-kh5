# Bug and rule catalogue

Status distinguishes an observed cause from a community lead. A related symptom
is not automatically a separate fix. The original research brief included reports
from several versions and inconsistent second-hand tables. The rows below are
original summaries; see [sources](sources.md) and [testing](testing.md).

| ID | Finding / affected versions | KH5 disposition |
|---|---|---|
| A1 | L5 ordinary multiball re-enters every third Hideout arrival | Numeric and pending-mode gates; matched control and targeted replays |
| A2 | Roughly 256-second Free Ride in L2/possibly L3; L1 mechanical-fault reports | Already corrected in L5; Burn Rubber regression, not a new claimed L5 fix |
| A3 | Redline converted/demoted by third arrival | Demonstrated A1 manifestation; preserved mode and progression |
| A4 | Lit locks but ramp permanently unavailable; versions unclear | Selected longer sequences tested; permanent all-player lockout remains unreproduced, report's version unconfirmed |
| A5 | Ramp oscillates on right orbit, reported L1 | Single earlier-version lead; no speculative L5 patch |
| A6 | Another player's locks released unexpectedly | Shared physical inventory/virtual-credit interactions traced and exercised; not every historical report shown to be a distinct software fault |
| A7 | Ball ends with saver apparently lit and two locks | Empty-trough travel/registration timing; fixture constraint, not a patch target |
| A8 | Supercharger Mode plus third-lock conflict, P-B | Prototype-specific; no earlier code imported |
| A9 | Drain while Redline introduction is pending crosses a ball/player boundary | Demonstrated pending-F2 omission; saver predicate corrected |
| A10 | Gear-five/Redline progress lost after a drain | A9 accounts for demonstrated races; separate reports remain unresolved |
| A11 | Restart loop also contributes RPM/Supercharger overlap | A1-dependent exploit; admission gate targets its prerequisite |
| A12 | Last-chance Redline jackpot/qualified lock starts regular multiball | Expected single-ball behavior; retained and tested in directed sequences |
| A13 | Late super-jackpot/grace inconsistencies | Some are A1 manifestations; all exact grace/payout variants not established |
| A14 | Supercharger opto reversals/diverter failure alter loop counting | Native design with mechanical dependencies; not rewritten |
| B1 | Lit Redline apparently awards ordinary multiball | Reported; probable overlap with A1, not every trigger independently reproduced |
| B2 | Older Redline revisions erase existing locks | Version/rule difference, not imported into L5 |
| B3 | Interacting Redline/ordinary modes lose lock/light progress | Demonstrated pending-intro overlap fixed; separate causes not assumed solved |
| B4 | Freeway extra ball cannot be lit again after Redline | Native Freeway collect state; expected behavior |
| B5 | Shift prompt after red-light multiball, L2 | Cosmetic earlier-version report |
| B6 | Rare L5 third-gear stall report | Reproduced temporary pause on L5/G6; closed as inferred expected RPM gate/Getaway behavior, not a proven permanent jam |
| B7 | Fourth-gear shift waits for Supercharger Mode to end | Expected; tests wait for mode cleanup |
| C1 | Earlier Secret Mania loses lights/locks and may affect other players | Earlier-version family; no blanket claim covering every L1/L2 defect |
| C2 | L5 repeated prep overwrites backup; tilt misses cleanup | Keep Secret Mania, guard preparation, correct gameplay/result task IDs |
| D1 | Uncapped single-ball Supercharger in early versions | Keep L5's 10M cap; separate from progressive super jackpots |
| D2 | Early ROM blamed for Supercharger driver failure | Disputed hardware/report lead, not treated as verified code cause |
| D3 | Supercharger display flicker in L1/L2 | Earlier-version report; keep L5 behavior |
| D4 | Old Supercharger total accumulates/wraps incorrectly | Cosmetic report, version scope uncertain; not claimed fixed |
| D5 | Speed Bonus can display zero after fifth gear | Native speed reset; no change |
| D6 | Loop Champion accounting during Supercharger Mode | Reported, version unknown; not claimed fixed |
| D7 | Reports disagree on super-jackpot caps | Preserve progressive behavior after admission fix; no new cap or claim every payout checked |
| E1 | P7 inlane inserts fail to light in gameplay | Prototype incompleteness; no speculative import |
| E2 | P7 ramp lockout after Redline | Earlier-version report; not evidence of permanent L5 lockout |
| E3 | Prototype instant multiball, long video mode and missing options | Different rules, outside KH5 scope |
| E4 | P-B Supercharger/lock conflict | Same prototype family as A8 |
| E5 | P-C differences without a precise defect | Research lead only |
| F1 | L5 native SLOW Game Re-Start checks a released button | Start edge corrected; native options retained |
| F2 | Free Ride is on/off rather than freely time-adjustable | Native design; no new saver adjustment claimed |
| F3 | Independent right flippers introduced in L5 | Retained; native-output checks and simulator input calibration |
| F4 | Video-mode extra ball absent in L1 | Earlier-version rule; L5 video award retained |
| F5 | Earlier Special availability across players | Version/report unresolved; not claimed fixed |
| F6 | Stoplight completion hides Burn Rubber award display | Cosmetic overlap; reward can still occur; no speculative patch |
| F7 | Video-mode safe position | Reported version-dependent exploit; not treated as a patch target |
| F8 | Nine targets sometimes give no extra ball | May reflect configured limit; directed positive award tested, not every limit path |
| F9 | Tunnel omits award on L5C tournament four-ball game | Single unconfirmed report; no blanket fix |
| F10 | Free Ride display/callout during multiball | Cosmetic report, sometimes consistent with A1 restarts |
| F11 | Burn Rubber percentage and tournament sequencing | Native rule; zero-minimum option retained, selected casual and fifth-award paths tested |
| F12 | Three Donut Heaven cars in tournament mode | Native design, used for deterministic Secret Mania entry |
| PWM | Cancelling timer can leave diverter high-power output latched | Found during project qualification; atomic timer/shadow/latch stop |

## B6 closure

The original 2005 account does not specify a complete shot history or duration.
Twenty-four exact-input L5/G6 replay pairs over 22 histories/offset/profile cases
all eventually advanced to fourth. During Getaway, ordinary RPM can be gated
before gear selection. Cleanup itself can update the tested RPM from 110 to 120;
a no-orbit control rules out assuming that a final orbit was merely queued.

The owner's disposition is **inferred expected behavior**: isolate ordinary
gear awards while multiball/Getaway is active. That design rationale is an
inference, not a quotation or confirmation from the original programmer.
No patch was made for B6 and no universal absence-of-jams claim follows.

## Mechanical cases kept separate

Trough/lock switch faults, balls wedged beneath the rear ramp, ramp feedback,
phantom optos, Supercharger tuning, missing balls and a damaged switch matrix
can imitate rule faults. Historical emulator fault tests include persistent
switch states, failed mechanisms, search recovery and repeated trapped-under-ramp
releases. They do not establish the condition of an owner's physical mechanism.
