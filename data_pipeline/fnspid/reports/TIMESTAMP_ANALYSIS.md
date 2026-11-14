# FNSPID Timestamp Analysis

## October 2023 source findings

- Records inspected: 89,036
- Records with literal UTC suffix: 89,036 (100%)
- Records without an explicit timezone marker: 0
- Distinct time-of-day values: 1
- Observed time-of-day: 00:00:00

## Interpretation

All inspected October 2023 Date values contain a literal UTC suffix.

However, every record has a time component of 00:00:00. These values therefore provide daily date-level granularity, not reliable intraday article publication times.

The UTC label is present in the source values, but the underlying timestamp-generation methodology and publication-time accuracy have not been independently verified.

## Parser behaviour

- Original Date values are preserved.
- Parsed comparable timestamps are generated separately.
- Explicit timezone markers are detected, including UTC, GMT, Z and numeric offsets.
- Timezone-naive values must not be assumed to represent UTC without verification.

## Downstream limitations

1. Do not interpret midnight timestamps as exact article publication instants.
2. Do not use these values for intraday news-to-market event ordering.
3. Preserve original timestamps alongside normalized fields.
4. Verify source timestamp semantics before point-in-time model integration.

**Conclusion:** October 2023 FNSPID timestamps are explicitly UTC-labelled but have daily granularity. Intraday publication-time precision is not established.
