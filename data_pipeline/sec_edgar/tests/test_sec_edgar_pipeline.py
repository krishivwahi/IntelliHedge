"""
End-to-end tests on SYNTHETIC SEC data served by a local mock server (tests/mock_sec_server.py).
Run:  python -m unittest discover -s tests -v      (from the SEC_EDGAR folder; works on Windows)

These tests prove the code behaves correctly on planted cases. They say NOTHING about real SEC data or about
how the collector behaves against sec.gov.
"""
import argparse
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "synthetic_data"))

import pandas as pd  # noqa: E402

import build_synthetic_sec as synth  # noqa: E402
import sec_edgar_collector as col  # noqa: E402
import sec_edgar_parser as par  # noqa: E402
import sec_edgar_quality_analysis as qa  # noqa: E402
from mock_sec_server import MockSec  # noqa: E402

UA = "IntelliHedge-Test test-user@example.invalid"


def collect_ns(url, out, **kw):
    d = dict(start="2026-10-01", end="2026-10-05", forms="8-K,8-K/A", out=str(out), workers=3, margin_days=2,
             closed_dates=col.DEFAULT_CLOSED, skip_documents=False, max_filings=0, www_base=url, data_base=url,
             user_agent=UA, rate=10.0, retries=3, backoff=0.05, pause_on_block=0.2, max_blocks=5, timeout=10)
    d.update(kw)
    return argparse.Namespace(**d)


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.tree = cls.root / "server_root"
        synth.build(cls.tree)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()


class TestFairAccess(Base):
    def test_user_agent_without_email_is_refused(self):
        for bad in (None, "", "JustAName", "no-at-sign example.com"):
            with self.assertRaises(SystemExit):
                col.preflight_ua(bad)
        self.assertEqual(col.preflight_ua("App me@x.org"), "App me@x.org")

    def test_gate_enforces_spacing_across_threads(self):
        g = col.Gate(10.0)
        t0 = time.monotonic()
        ts = [threading.Thread(target=lambda: [g.wait() for _ in range(5)]) for _ in range(4)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertGreaterEqual(time.monotonic() - t0, 19 * 0.1 * 0.95)       # 20 calls at <=10/s
        times = sorted(g.request_times)
        self.assertTrue(all(b - a >= 0.095 for a, b in zip(times, times[1:])))

    def test_rate_is_clamped_to_sec_maximum(self):
        ns = argparse.Namespace(user_agent=UA, rate=50, retries=1, backoff=0, pause_on_block=1, max_blocks=1, timeout=1)
        self.assertLessEqual(1.0 / col.make_client(ns).gate.interval, 10.0 + 1e-9)


class TestFullPipeline(Base):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.out = cls.root / "run1" / "data"
        with MockSec(cls.tree) as srv:
            cls.rc = col.run_collect(collect_ns(srv.url, cls.out))
            cls.requests = list(srv.requests)
        cls.raw = cls.out / "raw"
        cls.mani = pd.read_csv(cls.raw / "manifests/manifest.csv", dtype=str, keep_default_na=False)
        cls.summary = json.loads(next((cls.raw / "manifests").glob("collection_summary_*.json")).read_text())
        par.build(argparse.Namespace(data_root=str(cls.out), start="2026-10-01", end="2026-10-05", format="csv", min_chars=200))
        cls.proc = cls.out / "processed"
        cls.fp = pd.read_csv(cls.proc / "filings_primary.csv", dtype=str, keep_default_na=False)
        cls.fm = pd.read_csv(cls.proc / "filings_margin.csv", dtype=str, keep_default_na=False)
        cls.ex = pd.read_csv(cls.proc / "exhibits.csv", dtype=str, keep_default_na=False)
        cls.metrics = qa.analyse(argparse.Namespace(data_root=str(cls.out), out_dir=str(cls.root / "run1" / "reports"),
                                                    start="2026-10-01", end="2026-10-05", closed_dates=qa.DEFAULT_CLOSED))

    def row(self, acc):
        r = self.fp[self.fp.accession == acc]
        self.assertEqual(len(r), 1, acc)
        return r.iloc[0]

    # ---------------- collector
    def test_every_request_carries_the_declared_user_agent(self):
        self.assertTrue(self.requests)
        self.assertTrue(all(ua == UA for _, _, ua in self.requests))

    def test_selection_in_window_margin_and_other_forms(self):
        self.assertEqual(self.summary["index"]["unique_accessions_in_window"], 6)
        self.assertEqual(self.summary["index"]["unique_accessions_margin_after_end"], 1)
        self.assertEqual(len(self.fp), 6)
        self.assertEqual(len(self.fm), 1)
        self.assertNotIn("0000000006-26-000001", set(self.fp.accession))           # the 10-Q is not mixed in
        self.assertEqual(self.summary["index"]["expected_business_days_without_index"], [])

    def test_amendment_distinguished(self):
        r = self.row("0000000003-26-000001")
        self.assertEqual((r.idx_form_type, r.is_amendment, r.form_group), ("8-K/A", "True", "8-K/A"))
        self.assertEqual(self.row("0000000001-26-000001").is_amendment, "False")

    def test_submissions_pagination_found_older_page_record(self):
        r = self.row("0000000003-26-000001")
        self.assertEqual(r.has_submissions_record, "True")
        self.assertEqual(r.sub_primaryDocument, "gamma8ka.htm")

    def test_multifiler_collapsed_to_one_row(self):
        r = self.row("0000000004-26-000001")
        self.assertEqual((r.idx_row_count, r.idx_co_filer_ciks), ("2", "5"))

    def test_inaccessible_and_empty_documents_are_flagged_not_counted_as_success(self):
        self.assertEqual(self.row("0000000004-26-000001").primary_doc_status, "not_found")
        iota = self.row("0000000009-26-000001")
        self.assertEqual(iota.primary_doc_status, "failed")
        m = self.mani[(self.mani.resource == "primary_doc") & (self.mani.key == "0000000009-26-000001")].iloc[0]
        self.assertIn("empty", m.error)

    def test_primary_doc_found_via_index_page_when_submissions_missing(self):
        r = self.row("0000000007-26-000001")
        self.assertEqual(r.has_submissions_record, "False")
        self.assertEqual(r.primary_doc_status, "success")
        self.assertTrue(r.primary_doc_url.endswith("/eta8k.htm"))

    def test_manifest_statuses(self):
        ok = self.mani[(self.mani.resource == "primary_doc") & (self.mani.status == "success")]
        self.assertEqual(len(ok), 4)          # ACME, BETA, GAMMA, ETA (DELTA 404, IOTA empty)
        self.assertEqual(set(self.mani.status) - {"success", "not_found", "failed", "skipped_cached", "no_reference"}, set())
        self.assertEqual(int((self.mani.status == "failed").sum()), 1)

    def test_rerun_does_not_redownload_cached_files(self):
        before = len(self.requests)
        with MockSec(self.tree) as srv:
            col.run_collect(collect_ns(srv.url, self.out))
            second = srv.requests
        redownloaded = [p for _, p, _ in second if p.endswith(("-index.html", ".hdr.sgml", "acme8k.htm", "beta8k.htm", "gamma8ka.htm"))]
        self.assertEqual(redownloaded, [])
        self.assertLess(len(second), before)

    # ---------------- parser: timestamps
    def test_acceptance_convention_detection(self):
        self.assertEqual(self.row("0000000001-26-000001").acceptance_convention, "api_true_utc")
        self.assertEqual(self.row("0000000002-26-000001").acceptance_convention, "api_wallclock_equals_header_wallclock")
        self.assertEqual(self.row("0000000007-26-000001").acceptance_convention, "unverifiable")

    def test_filing_date_vs_acceptance_after_1730(self):
        b = self.row("0000000002-26-000001")
        self.assertEqual((b.filing_date, b.accepted_date_et, b.filing_date_minus_accepted_date_days), ("2026-10-02", "2026-10-01", "1"))
        self.assertEqual((b.accepted_after_1730_et, b.filing_date_rule_consistent, b.session_bucket), ("True", "True", "after_hours"))
        a = self.row("0000000001-26-000001")
        self.assertEqual((a.filing_date_minus_accepted_date_days, a.session_bucket), ("0", "regular_session"))
        self.assertEqual(self.row("0000000003-26-000001").session_bucket, "pre_market")

    def test_acceptance_in_utc_conversion(self):
        a = self.row("0000000001-26-000001")
        self.assertTrue(a.acceptance_utc_best.startswith("2026-10-01 14:15:00"))       # EDT = UTC-4

    def test_margin_filing_accepted_inside_window(self):
        t = self.fm.iloc[0]
        self.assertEqual((t.accession, t.in_filing_date_window, t.in_acceptance_window_et), ("0000000008-26-000001", "False", "True"))
        self.assertEqual(self.metrics["acceptance_window_check"]["filed_after_end_but_accepted_inside_window"], 1)

    # ---------------- parser: content
    def test_items_and_titles_preserved(self):
        a = self.row("0000000001-26-000001")
        self.assertEqual(a.items_list, "2.02;9.01")
        self.assertIn("2.02: Results of Operations and Financial Condition", a.items_titles)
        self.assertIn("Results of Operations", a.hdr_item_descriptions)

    def test_company_fields_and_exhibits(self):
        a = self.row("0000000001-26-000001")
        self.assertEqual((a.sub_tickers, a.sub_exchanges, a.sub_sic, a.hdr_sic_code), ("SYNA", "Nasdaq", "7372", "7372"))
        self.assertEqual(float(a.page_exhibit_count), 1.0)
        self.assertIn("EX-99.1", set(self.ex[self.ex.accession == a.accession].doc_type))

    def test_text_extraction(self):
        a = self.row("0000000001-26-000001")
        self.assertEqual(a.text_status, "success")
        txt = (self.proc / a.text_path).read_text(encoding="utf-8")
        self.assertIn("Item 2.02", txt)
        self.assertNotIn("color:red", txt)                                        # <style> content removed
        self.assertEqual(a.items_text_matches_metadata, "True")
        self.assertEqual(self.row("0000000004-26-000001").text_status, "not_attempted")

    # ---------------- quality analysis
    def test_metrics_values(self):
        M = self.metrics
        self.assertEqual(M["total_filings_primary"], 6)
        self.assertEqual(M["duplicate_analysis"]["amendments_8k_a"], 1)
        self.assertEqual(M["duplicate_analysis"]["duplicate_primary_documents_by_sha256"]["redundant"], 1)  # ACME == ETA
        self.assertEqual(M["duplicate_analysis"]["duplicate_accession_rows_in_processed"], 0)
        self.assertEqual(M["coverage_analysis"]["unique_ciks"], 6)
        self.assertEqual(M["coverage_analysis"]["unique_tickers"], 2)
        self.assertEqual(M["coverage_analysis"]["missing_business_days"], [])
        self.assertEqual(M["retrieval_and_content"]["primary_document_retrieval"]["success_pct"], 66.6667)   # 4 of 6
        self.assertEqual(M["retrieval_and_content"]["text_extraction"]["success_pct_of_all_filings"], 66.6667)
        self.assertEqual(M["market_session_alignment"]["session_distribution"],
                         {"regular_session": 4, "after_hours": 1, "pre_market": 1})

    def test_timezone_hypothesis_test_prefers_correct_interpretation(self):
        h = self.metrics["timestamp_analysis"]["timezone_hypothesis_test"]
        self.assertEqual(h["H1_header_is_eastern"]["filing_date_rule_violation_pct"], 0.0)
        self.assertEqual(h["H1_header_is_eastern"]["pct_outside_edgar_hours_or_weekend"], 0.0)


class TestBlocks(Base):
    def test_403_pauses_then_recovers(self):
        hdr = "/Archives/edgar/data/1/000000000126000001/0000000001-26-000001.hdr.sgml"
        out = self.root / "blk" / "data"
        with MockSec(self.tree, block_once={hdr}) as srv:
            t0 = time.monotonic()
            col.run_collect(collect_ns(srv.url, out, pause_on_block=0.6, skip_documents=True))
            self.assertGreaterEqual(time.monotonic() - t0, 0.6)
        m = pd.read_csv(out / "raw/manifests/manifest.csv", dtype=str, keep_default_na=False)
        r = m[(m.resource == "header") & (m.key == "0000000001-26-000001")].iloc[0]
        self.assertEqual((r.status, r.attempts), ("success", "2"))

    def test_persistent_403_aborts_instead_of_hammering(self):
        out = self.root / "blk2" / "data"
        with MockSec(self.tree, always_block=True) as srv:
            rc = col.run_collect(collect_ns(srv.url, out, pause_on_block=0.05, max_blocks=3, retries=10))
            n = len(srv.requests)
        self.assertEqual(rc, 3)
        self.assertLessEqual(n, 3)


class TestParsersUnit(unittest.TestCase):
    def test_master_idx_variants(self):
        t = "junk\nCIK|Company Name|Form Type|Date Filed|Filename\n-----\n1|A, INC|8-K|20261001|edgar/data/1/0000000001-26-000001.txt\nbad|line\n"
        rows = col.parse_master_idx(t)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["accession"], "0000000001-26-000001")
        self.assertEqual(col.norm_date("20261001"), "2026-10-01")
        self.assertEqual(col.norm_date("2026-10-01"), "2026-10-01")

    def test_invalid_timestamps(self):
        self.assertIsNone(par.parse_hdr_accept("2026100110"))
        self.assertIsNone(par.parse_hdr_accept("20261301101500"))
        self.assertIsNone(par.parse_api_accept("garbage"))
        self.assertIsNone(par.parse_api_accept(None))
        self.assertEqual(par.infer_convention(None, None), "unverifiable")

    def test_safe_name_windows(self):
        self.assertNotIn(":", col.safe_name("a:b*c?.htm"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
