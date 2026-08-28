Status: recorded
Created: 2026-08-27
Updated: 2026-08-27
Relates-To: .10x/tickets/cancelled/2026-08-27-profile-sentence-transformers-import-tree.md, .10x/research/2026-08-27-current-provider-free-retriever-construction-findings.md

# Ordinary Sentence Transformers Import Diagnostic

## What was observed

After the governed import-profile campaign failed opaquely, the owner explicitly authorized exactly one ordinary provider-free diagnostic. The parent ran the exact production import statement under the current project environment:

```python
from sentence_transformers import SentenceTransformer
```

The symbol was resolved but never instantiated. Provider credential keys were removed, telemetry was disabled, Hugging Face and Transformers offline flags were set, and Python bytecode writing was disabled. No sandbox or campaign parser wrapped the import beyond Python's standard-library `-X importtime` output.

The one process exited zero. It emitted 3,763 valid importtime rows. The `sentence_transformers` package root reported 1.868 ms self time and 9,444.291 ms cumulative profiler time. This profiler-instrumented cumulative value MUST NOT be treated as equivalent to the prior uninstrumented 7,633.771–7,840.623 ms boundary.

Largest observed exclusive/self rows were:

| Module | Self ms |
| --- | ---: |
| `transformers` | 452.716 |
| `transformers.models` | 382.396 |
| `transformers.utils.import_utils` | 352.583 |
| `torch._C` | 302.875 |
| `scipy.stats._stats_py` | 106.987 |
| `torch._prims` | 92.590 |
| `sympy.polys.polyclasses` | 88.115 |
| `torch._meta_registrations` | 79.639 |
| `transformers.utils.hub` | 70.509 |
| `scipy.stats._continuous_distns` | 63.161 |
| `torch.distributed._functional_collectives` | 55.441 |
| `sentence_transformers.base.modules.transformer` | 55.050 |
| `scipy.stats._morestats` | 47.346 |
| `torch._refs` | 41.848 |
| `torch.fx.experimental.symbolic_shapes` | 40.401 |

No cumulative intervals were summed. The complete raw stderr/stdout lived only in a temporary directory and was deleted by the command's exit trap after sanitized parsing.

## What this supports

The exact production import works in the ordinary current environment. Therefore the prior discarded warm-up's generic nonzero exit is a harness/sandbox execution failure, not evidence that the production import statement is intrinsically broken.

This single diagnostic also shows that broad Transformers import machinery and Torch native/runtime initialization contain the largest individual exclusive rows visible at the top of the profile. It does not establish complete family totals or a stable ordering across runs.

## Limits

This is one profiler-instrumented process, not the failed campaign's five-observation attribution. It does not establish repeatability, family-wide exclusive totals, causal CPU/I/O/device attribution, an optimization target, or authority to change dependencies or lifecycle. No model, retriever, provider, query, encode, retrieval, telemetry/store, build/install, release, or deployment operation occurred.
