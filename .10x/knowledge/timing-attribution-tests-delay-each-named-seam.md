Status: active
Created: 2026-08-23
Updated: 2026-08-23

# Timing Attribution Tests Must Delay Each Named Seam

A fixed fake clock can prove timestamp enclosure and exact arithmetic, but it
does not independently prove that real work at a named phase is attributed to
the intended duration column. When acceptance requires controlled delay at a
list of seams, every named seam needs its own baseline-versus-delay observation.

For command/pipeline timing validation:

- capture the command entry timestamp before the earliest seam under test;
- inject one bounded delay at exactly one seam per subprocess;
- compare zero-delay and delayed observations from the same local-fake path;
- read authoritative command and pipeline duration columns directly;
- never infer a total by summing nested span durations;
- for pre-pipeline and post-pipeline seams, require command duration to increase
  while pipeline duration remains effectively unchanged;
- for pipeline work, require both command and authoritative pipeline duration
  to increase;
- when needed, inspect the named phase span separately to prove that the delay
  landed at that seam rather than merely somewhere outside the pipeline;
- retain exact raw values, unrounded calculations, process order, host/runtime,
  and a bounded tolerance; and
- keep provider, model, network, credentials, and real user state behind local
  fakes so startup/cache variability does not become semantic evidence.

Passing fixed-clock assertions and adjacent phase delays does not satisfy an
acceptance criterion that explicitly names an untested seam.
