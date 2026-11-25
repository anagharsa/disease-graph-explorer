# Matching method

## Baseline

Let `S` be the selected phenotype IDs and `D` the unique phenotype IDs with non-negated (`Qualifier != NOT`) HPOA records for one disease. Disease Graph Explorer computes Jaccard overlap:

`score = |S ∩ D| / |S ∪ D|`

A disease is a candidate when it has a documented positive association with at least one selected term. Candidates rank by score descending, then disease name. The score is displayed as a phenotype match score and is never interpreted as a probability.

The response includes matched IDs/names, selected IDs without a positive record for that disease, and other documented positive phenotypes. Missing records are labeled “not documented,” not “absent.” Explicit NOT rows remain in the graph and source evidence but do not count as positive matches.

## Why this baseline

It is a small, testable overlap baseline and uses no fabricated association weights. It makes disease-profile size part of the denominator. Example: with selected set `{a,b}`, a profile `{a,b,c}` has hit-rate `2/2=1.0` but Jaccard `2/3≈0.667`. The example illustrates behavior; it is not a measured HPO record.

An information-content method would require defined corpus frequency assumptions and a carefully designed ancestor-aware metric. That is outside the current baseline. `IS_A` edges are shown and traversable in the graph but do not expand or double-count terms in matching. This avoids silently treating a parent as additional clinical evidence.

## Limitations

- HPOA records reflect curated disease features, not an individual patient record.
- Annotation gaps and variation in curation affect scores.
- A larger phenotype profile can reduce Jaccard overlap even when every selected phenotype matches.
- Candidate retrieval is bounded to the requested top records; scores are exact for the candidates returned, while later candidates may be omitted by the API limit.
- The exact annotation file has three rows under an immunodeficiency whose name includes “COVID19-related”; it has no dedicated COVID-19/SARS-CoV-2 infection profile according to the direct text audit.
