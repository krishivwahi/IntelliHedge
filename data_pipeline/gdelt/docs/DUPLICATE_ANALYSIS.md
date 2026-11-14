
# GDELT Duplicate Analysis — October 2026

## Dataset
- Total GKG records: 2,985,215
- Records with headlines: 2,979,631
- Unique normalized headlines: 1,854,411
- Repeated headline groups: 203,642

## Findings

### 1. URL duplicates
- Raw duplicate URLs: 0
- Normalized duplicate URLs: 16,582
- Redundant record percentage: 0.5555%

### 2. Headline duplicates
- Same-domain duplicate headlines: 127,552 redundant records (4.2808%)
- Cross-domain duplicate headlines: 1,125,220 redundant records (37.7637%)

### 3. Manual inspection

Examples identified:

- Targeted News Service: repeated title across different press-release URLs.
- China Daily: repeated website title across different article URLs.
- Cairns Post: generic subscription title across different articles.
- Deadline: repeated title across different article IDs.
- Samsung Galaxy: same article path distributed across multiple radio domains.

## Interpretation

Matching headlines do not necessarily represent duplicate news events.

Repeated headlines may arise from:
- Website boilerplate and generic page titles.
- Press-release distribution.
- Syndicated news.
- Genuine repeated coverage.

## Recommended IntelliHedge Policy

1. Preserve all original GDELT records.
2. Do not deduplicate solely by headline.
3. Normalize URLs before identifying duplicate URLs.
4. Flag generic and repeated page titles.
5. Investigate syndication separately.
6. Preserve source provenance.

## Conclusion

Headline duplication is a significant data-quality consideration.
It requires intelligent deduplication rather than simple headline removal.
