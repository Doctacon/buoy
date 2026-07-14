Status: recorded
Created: 2026-07-14
Updated: 2026-07-14
Target: .10x/tickets/done/2026-07-14-benchmark-open-embedding-backends.md
Verdict: pass

# Open Embedding Backend Bake-off Review

## Findings

Independent review confirmed the roster is complete for the ratified in-process/drop-in scope, successful-lane arithmetic and corpus hashes are correct, and the null-promotion conclusion is supported. Review initially found inconsistent warm/cold wording, ambiguous top-10 semantics, and overclaimed reproducibility/termination details. Repairs aligned the ticket with three warm runs plus one cold load, defined exact ordered top-10 equality, retained setup/invocation capture without claiming byte-identical historical regeneration, and narrowed failed-lane facts to operator-attested observations.

The final review found one remaining use of “killed” where canonical evidence supported only “terminated”; both summary occurrences were changed mechanically. No material finding remains.

## Verdict

Pass. Retain Torch/MPS for the measured Apple Silicon workload; promote no candidate backend.

## Residual risk

One host, one corpus slice, one query, one batch size, and no CUDA/Linux comparison. FastEmbed and CoreML failures lack original retained process logs and are intentionally reported only as bounded operator observations.
