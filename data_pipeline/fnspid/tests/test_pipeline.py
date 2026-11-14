import sys, tempfile, unittest
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from fnspid_dates import parse_date_series, normalize_ticker, normalize_url
from fnspid_parser import process_frame, parse_csv
from fnspid_quality_analysis import analyse

class TestFNSPID(unittest.TestCase):
    def setUp(self):
        self.tmp=Path(tempfile.mkdtemp())
        self.src=ROOT/"tests"/"synthetic_data"/"news_fixture.csv"
    def test_date_parser_handles_iso_and_invalid(self):
        s=parse_date_series(pd.Series(["2023-10-01","2023-10-02T09:30:00-04:00","bad"]))
        self.assertEqual(s.notna().sum(),2)
    def test_ticker_normalization(self):
        x=normalize_ticker(pd.Series([" aapl ","msft",None]))
        self.assertEqual(x.iloc[0],"AAPL"); self.assertEqual(x.iloc[1],"MSFT")
    def test_url_normalization(self):
        x=normalize_url(pd.Series(["HTTP://Example.com/a?utm=x"]))
        self.assertEqual(x.iloc[0],"https://Example.com/a")
    def test_preserves_original_and_adds_derived(self):
        f=pd.read_csv(self.src)
        out=process_frame(f)
        self.assertIn("Article_title",out.columns)
        self.assertIn("ih_title",out.columns)
        self.assertIn("ih_timestamp_parsed_utc_comparable",out.columns)
    def test_chunked_date_filter(self):
        dest=self.tmp/"oct.csv"
        n=parse_csv(self.src,dest,chunksize=2,start="2023-10-03",end="2023-10-03")
        self.assertEqual(n,1)
        self.assertEqual(len(pd.read_csv(dest)),1)
    def test_quality_metrics(self):
        m=analyse(self.src,chunksize=2)
        self.assertEqual(m["rows"],4)
        self.assertEqual(m["invalid_dates"],1)
        self.assertEqual(m["unique_tickers"],3)
        self.assertEqual(m["unique_publishers"],2)

if __name__=="__main__": unittest.main()
