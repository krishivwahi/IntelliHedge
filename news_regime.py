"""
IntelliHedge — Engine 1: Point-in-Time News Narrative Intelligence
Authors: Krishiv Wahi, Kamya Aggarwal, Sarthak Shandiliya

Implements:
  1. 3-gram shingle MinHash-style near-duplicate wire filtering
  2. Dual-Anchor Leader-Clustering (Immutable Origin o_k + EMA Recency r_k(t))
  3. Constrained Semantic Novelty scaled by Deterministic Numeric Delta
  4. Independent Logistic Squashing + Asymmetric Schmitt Trigger
     (H_k=0.75 → DOMINANT, L_k=0.55 → FADING, REIGNITION flag)
  5. Emits point-in-time regime vector Q_t^news = [S_k, state_num, trend_num, novelty_mass]
"""

import re
import math
import numpy as np


class PointInTimeNewsEngine:
    """
    Point-in-time news regime engine.

    Separation guarantee: regime strength S_k(t) is computed from the news
    stream ONLY. Market prices, volatility, and P&L never enter this class.
    """

    def __init__(self, alpha_ema: float = 0.35, h_thresh: float = 0.75, l_thresh: float = 0.55):
        self.alpha  = alpha_ema   # EMA blending weight for recency centroid
        self.H_k    = h_thresh    # Schmitt upper threshold → enter DOMINANT
        self.L_k    = l_thresh    # Schmitt lower threshold → exit to FADING

        # Dual-anchor cluster state
        self.origin_anchor    = None   # Immutable: first breaking article embedding
        self.recency_centroid = None   # EMA-updated recency centroid r_k(t)
        self.recent_embeddings: list  = []

        # Deduplication & numeric tracking
        self.seen_shingles: set = set()
        self.ref_numbers:  list = []

        # State machine
        self.state        = "DORMANT"
        self.prev_strength = 0.0
        self.ema_dS        = 0.0

        # Domain vocabulary for fast, deterministic offline semantic embeddings.
        # No external API — zero-dependency by design.
        self.vocab = [
            "iran", "us", "strike", "missile", "strait", "hormuz", "oil", "tanker",
            "pentagon", "casualties", "sanctions", "naval", "fleet", "ceasefire",
            "talks", "diplomacy", "red", "sea", "drone", "refinery", "brent",
            "escalation", "retaliation", "embargo", "warships", "tehran", "supply",
        ]

    # ------------------------------------------------------------------
    # 1. Near-duplicate wire filtering (3-gram shingle Jaccard)
    # ------------------------------------------------------------------
    def _shingle_dedup(self, text: str, threshold: float = 0.80) -> bool:
        """Return True if *text* is a near-duplicate of a previously seen headline."""
        words    = re.findall(r"[a-z]+", text.lower())
        shingles = set(" ".join(words[i:i + 3]) for i in range(max(1, len(words) - 2)))
        for past in self.seen_shingles:
            overlap = len(shingles & past) / max(1, len(shingles | past))
            if overlap >= threshold:
                return True   # Syndicated duplicate — drop
        self.seen_shingles.add(frozenset(shingles))
        return False

    # ------------------------------------------------------------------
    # 2. Deterministic offline embedding (vocab bag-of-words + char hash)
    # ------------------------------------------------------------------
    def _embed(self, text: str) -> np.ndarray:
        words    = re.findall(r"[a-z]+", text.lower())
        vec      = np.zeros(len(self.vocab), dtype=np.float32)
        for i, token in enumerate(self.vocab):
            vec[i] = sum(1.0 for w in words if token in w)
        # 16-dim character n-gram hash projection for general semantic coverage
        hash_vec = np.zeros(16, dtype=np.float32)
        for w in words:
            hash_vec[hash(w) % 16] += 0.5
        full = np.concatenate([vec, hash_vec])
        norm = np.linalg.norm(full)
        return full / (norm + 1e-8)

    # ------------------------------------------------------------------
    # 3. Regex numeric-delta extractor
    #    Detects changes in casualties, basis points, or percentages
    # ------------------------------------------------------------------
    def _extract_numeric_delta(self, text: str) -> float:
        nums = [float(x) for x in re.findall(r"\b\d+(?:\.\d+)?\b", text)]
        if not nums:
            return 0.0
        if not self.ref_numbers:
            self.ref_numbers = nums
            return 0.5
        max_curr = max(nums)
        max_ref  = max(self.ref_numbers)
        delta    = 1.0 - math.exp(-abs(max_curr - max_ref) / (max_ref + 10.0))
        self.ref_numbers = nums
        return float(delta)

    # ------------------------------------------------------------------
    # 4. Cosine similarity utility
    # ------------------------------------------------------------------
    @staticmethod
    def _cos(a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

    # ------------------------------------------------------------------
    # 5. Main processing step — one time-window of headlines
    # ------------------------------------------------------------------
    def step(self, step_idx: int, headlines_batch: list) -> dict:
        """
        Process all point-in-time articles arriving in window t.

        Parameters
        ----------
        step_idx        : int   — current time step index
        headlines_batch : list  — [(source_str, text_str), ...]

        Returns
        -------
        dict with keys: t, S, state, trend, reignited, novelty_mass, Q_vec
        """
        valid_novelties: list = []
        numeric_deltas:  list = []
        unique_sources:  set  = set()

        for source, text in headlines_batch:
            if self._shingle_dedup(text):
                continue   # Drop syndicated wire clone

            unique_sources.add(source)
            e_i       = self._embed(text)
            num_delta = self._extract_numeric_delta(text)

            if self.origin_anchor is None:
                # First ever article → seed both anchors
                self.origin_anchor    = e_i.copy()
                self.recency_centroid = e_i.copy()
                affinity  = 1.0
                freshness = 1.0
            else:
                # Dual-Anchor Affinity: A_k(i) = 0.6*cos(e_i, o_k) + 0.4*cos(e_i, r_k(t))
                a_origin = max(0.0, self._cos(e_i, self.origin_anchor))
                a_recent = max(0.0, self._cos(e_i, self.recency_centroid))
                affinity = 0.6 * a_origin + 0.4 * a_recent

                # Freshness: 1 − max_j∈recent cos(e_i, e_j)
                recent_window  = self.recent_embeddings[-6:]
                max_sim_recent = max((self._cos(e_i, ej) for ej in recent_window), default=0.0)
                freshness      = max(0.0, 1.0 - max_sim_recent)

                # EMA recency centroid update — origin_anchor stays immutable
                raw_r = (1.0 - self.alpha) * self.recency_centroid + self.alpha * e_i
                self.recency_centroid = raw_r / (np.linalg.norm(raw_r) + 1e-8)

            # Constrained Novelty = Affinity × Freshness × (1 + Numeric Delta Boost)
            novelty_i = affinity * freshness * (1.0 + 0.85 * num_delta)
            valid_novelties.append(novelty_i)
            numeric_deltas.append(num_delta)
            self.recent_embeddings.append(e_i)

        # Aggregate signal features
        novelty_mass   = sum(valid_novelties)
        source_entropy = math.log(1.0 + len(unique_sources))
        max_num_shock  = max(numeric_deltas, default=0.0)

        # Independent Logistic Squashing S_k(t) = 1 / (1 + exp(-z_k(t)))
        z_t = (-1.6
               + 0.75 * novelty_mass
               + 0.55 * source_entropy
               + 1.15 * max_num_shock
               + 1.35 * (0.65 * self.prev_strength))
        S_t = 1.0 / (1.0 + math.exp(-z_t))

        # ------------------------------------------------------------------
        # Asymmetric Schmitt Trigger State Machine
        #   DORMANT / FADING → DOMINANT if S_t >= H_k
        #   DOMINANT         → FADING   if S_t <= L_k
        #   REIGNITION flag  when FADING → DOMINANT
        # ------------------------------------------------------------------
        reignited = False
        if self.state in ("DORMANT", "FADING") and S_t >= self.H_k:
            if self.state == "FADING":
                reignited = True
            self.state = "DOMINANT"
        elif self.state == "DOMINANT" and S_t <= self.L_k:
            self.state = "FADING"
        elif self.state == "DORMANT" and S_t > 0.30:
            self.state = "FADING"

        # Trend: EMA of first-difference of S_k(t)
        dS          = S_t - self.prev_strength
        self.ema_dS = 0.6 * dS + 0.4 * self.ema_dS
        if self.ema_dS >= 0.04:
            trend = "RISING"
        elif self.ema_dS <= -0.04:
            trend = "FALLING"
        else:
            trend = "STABLE"

        self.prev_strength = S_t

        # Numeric encoding for regime vector
        state_num = 1.0 if self.state == "DOMINANT" else (0.5 if self.state == "FADING" else 0.0)
        trend_num = 1.0 if trend == "RISING" else (-1.0 if trend == "FALLING" else 0.0)

        return {
            "t":            step_idx,
            "S":            S_t,
            "state":        self.state,
            "trend":        trend,
            "reignited":    reignited,
            "novelty_mass": novelty_mass,
            "Q_vec":        np.array([S_t, state_num, trend_num, min(1.0, novelty_mass)],
                                     dtype=np.float32),
        }


# -------------------------------------------------------------------------
# Synthetic Crisis News Stream — 15-step US-Iran Strait of Hormuz replay
# -------------------------------------------------------------------------
def build_crisis_news_stream() -> list:
    """
    15-step chronological news stream.
    Includes: escalation burst, syndicated wire duplicates, fading, reignition.
    No market price data enters this stream — dynamics separation enforced.
    """
    return [
        [("Reuters",  "Routine OPEC energy ministers meeting concludes with 0 change in output quotas")],
        [("Bloomberg","Diplomatic tensions simmer near Strait of Hormuz as naval patrol routine continues")],
        [
            ("Reuters",  "BREAKING: US naval destroyers intercept 14 missiles launched near Strait of Hormuz"),
            ("AP",       "Pentagon confirms strike on 3 radar sites following Strait of Hormuz escalation"),
            ("FT",       "Crude oil tankers halt transit across Hormuz as war risk insurance surges 300 bps"),
        ],
        [
            ("Bloomberg","Iranian forces seize 2 commercial oil tankers; Brent crude volatility spikes 45 percent"),
            ("WSJ",      "Emergency UN Security Council session called as 850 personnel deployed to Gulf fleet"),
            ("CNBC",     "BREAKING: US naval destroyers intercept 14 missiles launched near Strait of Hormuz"),  # Syndicated!
        ],
        [
            ("Reuters",  "US announces sanctions on 18 petrochemical entities after Hormuz naval clash"),
            ("FT",       "Global shipping insurers raise Gulf war risk premiums by 150 bps amid naval standoff"),
        ],
        [
            ("Bloomberg","Analyst roundup: Oil markets digest Strait of Hormuz tensions as tankers reroute"),
            ("Reuters",  "US announces sanctions on 18 petrochemical entities after Hormuz naval clash"),  # Duplicate!
        ],
        [("FT",      "Middle East envoy arrives for indirect de-escalation talks; 0 new naval incidents")],
        [("Reuters", "Shipping traffic partially resumes through Hormuz under escort with 0 new strikes")],
        [("Bloomberg","Market commentary: Geopolitical risk premium fades as Hormuz ceasefire holds for day 4")],
        [("WSJ",     "Energy traders refocus on seasonal inventory data as Gulf naval tensions remain quiet")],
        [
            ("Reuters",  "FLASH: Massive drone swarm strikes 4 major oil refineries; 1200 barrels/day offline"),
            ("Bloomberg","Tehran vows full blockade of Strait of Hormuz; US orders 2 carrier strike groups in"),
            ("FT",       "Emergency G7 reserve release weighed as Hormuz blockade threatens 20 percent of oil supply"),
        ],
        [
            ("AP",  "Naval exchange damages 3 supertankers in Gulf; Pentagon raises readiness to DEFCON 2"),
            ("WSJ", "Treasury imposes total embargo on energy exports; crude implied volatility hits 68 percent"),
        ],
        [("Reuters",  "Ceasefire hotline activated after 48-hour Hormuz escalation; naval fleet holds position")],
        [("Bloomberg","Damage assessment underway at Gulf terminals; shipping slowly resumes under convoy")],
        [("FT",       "Provisional maritime corridor treaty signed; war risk surcharges reduced by 120 bps")],
    ]

