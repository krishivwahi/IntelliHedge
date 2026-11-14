# Smoke test on SYNTHETIC data — NOT GDELT RESULTS

`make_synthetic_gkg.py` invents 2 days of GKG-format files with planted defects. The pipeline
(parser -> quality analysis) was run on it and every computed value matched the planted truth:

| Planted | Expected | Computed |
|---|---|---|
| records (2 days, 1 slot omitted, 1 malformed line) | 484 + 479 = 963 | 963 |
| malformed line (3 fields) | 1 quarantined | 1 dropped, flagged in parse_stats.csv |
| missing 15-min slot | 20261002023000 | 20261002023000 |
| bad V2.1DATE ("20261O01") | 2 (one per day) | bad_format 0.2077% = 2/963 |
| repeated GKGRECORDID (exact repeated row) | 2 | 2 |
| exact duplicate rows excl. id | 3 | 3 |
| duplicate raw URLs / normalised (utm stripped) | 5 / 6 | 5 / 6 |
| translingual record (srclc:deu) | 2 | language deu = 2 |
| record time == file slot | 100% | 100% |

Numbers from this test must never be quoted as properties of GDELT.
Regenerate with: python tests/make_synthetic_gkg.py tests/synthetic_raw
