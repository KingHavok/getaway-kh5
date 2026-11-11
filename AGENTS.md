# Project handoff for coding agents

Read `docs/developer-handoff.md`, `docs/test-catalogue.md` and
`docs/technical-map.md` before changing firmware or tests. These guides and the
repository's research/evidence are the handoff; no prior chat is required.

- Preserve Secret Mania, its challenge, original rules and native lifecycle.
  Research demonstrated defects before making speculative changes.
- Official L5 and frozen KH5 identities are pinned. Use `tools/lab.py` and a
  private workspace for candidates; never relax release checks to accept a build.
- ROMs, sound, NVRAM, DMD assets, debugger dumps, disassembly and original-byte logs
  remain private. No ROM downloads. Only authored source, inputs, numeric results
  and hashes belong here. LED/native data is transformed or read owner-locally.
- Tests bind results to actual images/settings/source. Keep failures; don't update
  expected results to hide a difference. Historical G6 passes are not KH5 passes.
- A4 permanent ramp lockout and separate A10 gear-loss reports remain unresolved.
  B6's temporary Getaway/RPM gate is closed as inferred expected behaviour.
- Run appropriate ROM-free checks plus owner-local directed native tests when
  inputs are available. Missing U18 or external references must be stated plainly.
  Never burn unit fixtures. Digital coil timing is not a physical thermal test.
- Review new public files explicitly through `PUBLIC_FILES.txt`, then run the
  publication scanner against the staged tree and reachable history.
