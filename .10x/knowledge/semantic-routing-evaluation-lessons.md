Status: active
Created: 2026-07-15
Updated: 2026-07-15

# Semantic Routing Evaluation Lessons

## Purpose

Preserve the reusable evaluation lessons from the first representative namespace-routing experiment so future routing work does not repeat its measurement and evidence defects.

## Evaluation rules

### Apply fan-out before metrics

A routing limit defines the returned set, not merely a recall cutoff. Truncate each route ranking before calculating home rank, MRR, or unranked counts. A relevant namespace at rank six is unranked when fan-out is five.

Tests should include required namespaces immediately inside and outside the limit and should verify the stored ranking, home rank, MRR, recall, and unranked count together.

### Separate configured guards from observed activity

A hard-coded zero is not instrumentation. Report:

- which APIs are guarded;
- which environment variables are removed or set;
- which modules were absent;
- whether guarded execution completed without a violation;
- which before/after manifests matched;
- what the controls cannot observe.

Do not describe Python-level guards as proof of all OS-level activity.

### Quantify source-name exposure

A question containing the expected project title or alias mainly tests explicit source attribution. Every routing benchmark should report the number and proportion of questions that reveal their labeled source through complete normalized descriptors.

Report descriptor-free cases separately and inspect them for cross-source ambiguity. Do not infer that alternative namespaces are irrelevant when labels name only the originating corpus.

### Do not fabricate downstream evidence

Home-namespace hits are not comparable cross-namespace results unless the same question was run against every candidate under the same retrieval contract. Route-only experiments must not simulate missing hit lists or claim downstream answer quality.

## First experiment limits

The 2026-07-15 representative experiment found 79 of 90 questions exposed the home title or alias. Its corrected top-five hybrid MRR was `0.927778`, but this remains descriptive source-attribution evidence, not a production promotion result.

Future work needs a separately ratified benchmark or product integration contract. Do not reuse this result as a production threshold.
