# Restore Run the Red Light

L2 owners described the words appearing separately, then the combined phrase,
with native sound requests before multiball. Initial work looked for a port from
L2. The corresponding effect already survives in official L5 at bank `2B:537A`.

The standard multiball introduction is effect `36`. Its table pointer at file
`76A37..76A38` is redirected to that resident routine. Effect priority, flags,
bank, lifecycle and ball-release sequencing remain those of the original entry.
No L2 binary range, animation, font, text table or sound ROM is copied into the patch.

Third-lock replay traces distinguish the requested resident effect from the old
short intro. Private ordered-pixel captures verified the word progression and
whole phrase. Such captures contain game artwork and are deliberately not public.
KH5's A1 replay rechecks native effect entry and existing gameplay assertions.
Sound CPU execution is distinct from audible listening on the actual machine.
