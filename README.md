# IntelliHedge

Does news give an options hedger information that option prices do not already contain?

A research project, in progress. Methods and results will be published with the paper.

## Contents

- `data_pipeline/`: collectors and quality audits for four news sources (GDELT, SEC EDGAR, FNSPID, Alpaca/Benzinga).
- `merton_env.py`: Black-Scholes put price and delta.
- `deep_hedger.py`: CVaR loss.
- `tests/`: unit tests for the above.

Install with `pip install -r requirements.txt`, test with `python -m pytest -q`.
