Status: recorded
Created: 2026-06-20
Updated: 2026-06-20
Relates-To: .loom/evidence/2026-06-20-turbopuffer-billing-cost-signal.md, .loom/tickets/2026-06-20-minimize-turbopuffer-rag-cost-plan.md, .loom/knowledge/turbopuffer-cost-model.md

# Turbopuffer launch minimum billing analysis

## What was observed

The user supplied an additional turbopuffer pricing calculator screenshot stored at:

- `.loom/evidence/.storage/2026-06-20-turbopuffer-cost-calculator-minimum.png`

The screenshot shows:

- Launch plan selected.
- Estimated usage cost lines near zero for the displayed small usage settings.
- Footer text: `Estimated cost (min $16/mo for launch plan)`.

The current invoice screenshot showed `$5.87` for billing period `Jun 20-Jul 1`, i.e. about 11 days.

Calculation:

```text
$16 / 30 days * 11 days = $5.866...
```

This matches the observed `$5.87` invoice almost exactly.

## Procedure

- Read the new screenshot from the temporary clipboard path supplied by the user.
- Copied it into `.loom/evidence/.storage/`.
- Compared the displayed Launch-plan minimum with the observed billing period and invoice total.

No turbopuffer API calls, credential access, writes, queries, or deletes were performed.

## What this supports or challenges

This strongly supports that the observed `$5.87` current invoice is primarily the prorated Launch-plan minimum, not direct usage from the Jellyfish RAG indexing/query workload.

It also reframes the prior cost concern:

- The MVP may still have avoidable usage inefficiencies, especially returning full `content`, running live evals, and indexing/filtering extra attributes.
- But changing the schema/retrieval shape alone probably will not make the current invoice drop below the prorated monthly plan minimum.
- Deleting the namespace may reduce ongoing storage/usage charges, but may not eliminate the Launch-plan minimum for the billing period.

## Limits

This is an inference from screenshots and arithmetic, not an official turbopuffer invoice-line explanation. The exact allocation of the prorated minimum across billing categories should be confirmed with turbopuffer support or detailed invoice line items if needed.
