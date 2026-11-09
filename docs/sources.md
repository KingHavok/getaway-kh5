# Sources and provenance

## Tools

| Project | Pinned source |
|---|---|
| PinMAME | https://github.com/vpinball/pinmame/tree/47ac466023e488e1cbeb19448fa3f56ff9cc8788 |
| wpclp | https://github.com/Pwedge/wpclp/tree/b0dcc64845847ebbdf8f5c39733dce7869ab13d4 |
| f9dasm | https://github.com/Arakula/f9dasm/tree/ba842910cab9b343cb299fe74380950f22f04b70 |

The private instrumented PinMAME executable's SHA256 was
`16b037b58443cbafa2a42ec5cfdac4a458a80248b47857622b4aa6082d80b19b`.
A rebuild with a different compiler can have a different executable hash; retain
that identity and calibrate instrumentation rather than assuming identical timing.
The source-only instrumentation patch is separate from the proprietary game.

## Community leads and technical descriptions

- [Keith Johnson's Start/restart explanation and multiball discussion](https://pinside.com/pinball/forum/topic/hs2-getaway-is-in-the-house-multiball-bug).
- [Kevin Martin, Sigma's Guide, 3 March 1994](https://pinball.org/rules/getaway.html).
  It describes older rules and uncertain revision/operator differences; it is not
  proof that a report occurs in L5.
- Pinside: “Getaway: High Speed II - What ROM set should I use?” — Soren's patch
  notes and baseline SHA1, plus later owner reports.
- Tilt Forums: “Seeking knowledge on The Getaway quirkiness and oddities” —
  Johnson/Soren explanations and owner sequences, 2017–2022.
- rec.games.pinball: “Getaway ROM versions comparison”, April 2005 — initial
  version matrix and single-report leads; treat second-hand entries cautiously.
- [PinMAME Getaway simulator/source](https://github.com/vpinball/pinmame/blob/47ac466023e488e1cbeb19448fa3f56ff9cc8788/src/wpc/sims/wpc/full/gw.c)
  and its WPC hardware implementation define the emulated interfaces.

Thread titles without a verified canonical URL are left as titles rather than
inventing links or copying posts. Hashes identify privately checked inputs;
this project provides no download mirror for a game ROM, sound ROM, L5C or manual.
