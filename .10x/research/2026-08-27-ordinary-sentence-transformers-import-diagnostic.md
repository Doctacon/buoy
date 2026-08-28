Status: done
Created: 2026-08-27
Updated: 2026-08-27
Decision: .10x/decisions/provider-free-local-diagnostics-separate-debugging-from-measurement.md
Evidence: .10x/evidence/2026-08-27-ordinary-sentence-transformers-import-diagnostic.md

# Ordinary Sentence Transformers Import Diagnostic

## Question

Does the exact production Sentence Transformers import work in the ordinary current environment, and which individual exclusive import rows are visibly largest in one standard-library import profile?

## Sources and method

At explicit owner request, one current-environment process executed the exact production statement under Python `-X importtime`:

```python
from sentence_transformers import SentenceTransformer
```

The symbol was resolved but never instantiated. Provider credentials were removed, offline flags enabled, telemetry disabled, and bytecode writing disabled. Raw output existed only in a temporary directory through sanitized parsing and was then deleted.

## Findings

The process exited zero and yielded 3,763 valid import rows. The package root reported 9,444.291 ms profiler-instrumented cumulative time. This is not directly comparable to the prior uninstrumented 7,633.771–7,840.623 ms interval.

The largest individual exclusive rows were broad Transformers import machinery (`transformers`, `transformers.models`, and `transformers.utils.import_utils`, each 352.583–452.716 ms) and Torch native/runtime initialization (`torch._C`, 302.875 ms). SciPy statistics, additional Torch machinery, SymPy, and one Sentence Transformers base module contributed smaller top-visible rows.

The exact production import therefore works ordinarily. The earlier opaque warm-up failure belongs to its temporary governed harness/sandbox, not to an intrinsic inability to import the package.

## Conclusion

Current evidence points inside broad Transformers import machinery and Torch native/runtime initialization rather than the Sentence Transformers wrapper or post-import model constructor. One diagnostic is enough to unblock investigation and reject the failed harness as current authority, but not enough to establish stable family totals, repeatability, causality, a performance target, or an implementation choice.

## Limits

One profiler-instrumented process on one host. No model, provider, query, encode, retrieval, telemetry/store, build/install, release, or deployment operation occurred. Cumulative intervals were not summed. Complete raw rows were intentionally not retained, so this record supports top-visible individual contributors rather than exhaustive family accounting.
