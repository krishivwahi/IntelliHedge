# What to send and ask your professor

## Send (one email, four attachments)

1. `IntelliHedge_Roadmap_v2.pdf` — the 12-month plan.
2. `docs/phase0/corrected_results.md` — the honest re-run of the Phase-1 prototype. **Send this first-hand; do not let them find it.**
3. `docs/phase0/data_memo.md` — the data questions and budget request.
4. `docs/phase0/pre_analysis_plan.md` and `docs/phase0/authorship_agreement.md` — for discussion at the meeting, not for signature yet.

## Ask (in the meeting, in this order)

**Data and resources — blocking, needed this week**
1. Does the university have WRDS, and does it include OptionMetrics?
2. Do we have Refinitiv/LSEG, Bloomberg or RavenPack, and can students export data?
3. Is there a fund for a one-off data purchase? Ceiling and approval route?
4. Is GPU or cluster time available?

**Science — needs their sign-off before Phase 1**
5. Do you agree with the restated hypothesis (news adds information *beyond implied volatility*) and the five evaluation arms?
6. Do you accept that a clean negative result is a valid outcome and will still be written up?
7. Are the splits (train 2015–2019, validation 2020–2021, test 2022–2025) acceptable?
8. Is the simulator design for the mechanism study sound: hidden jump-intensity regime, news as a noisy observation of it?
9. Who on the faculty could check the stochastic-calculus and statistics sections?

**Paper and logistics**
10. Will you co-author, and is the proposed author order acceptable?
11. Are there department rules on authorship, affiliation or IP?
12. Does the project need to be registered now as the final-year project?
13. Can we meet at each gate (roughly every 4–8 weeks) with a one-page written update monthly?
14. Is there support for conference registration or travel?

## Email draft

> **Subject:** IntelliHedge — corrected Phase-1 results, 12-month plan, and three decisions I need from you
>
> Dear Professor [Name],
>
> After the micro-project review I audited our prototype and found that the headline result does not hold up as evidence. The simulator's jump schedule and the scripted news stream were aligned by construction, the market-only baseline was under-trained, the hedging options were mispriced ahead of the jumps, and the statistics came from too few test paths. I have rebuilt the evaluation with 100,000 test paths, ten training seeds and bootstrap confidence intervals; the corrected numbers are attached. I would rather you hear this from me now than from a reviewer later.
>
> I have also rewritten the roadmap to finish in twelve months, with a corrected design: a stronger baseline, placebo and lag controls, a simulator in which news is a noisy observation of hidden jump risk, and a real-data test that is opened only once.
>
> I need three things from you:
>
> 1. **Data access.** Does the university have WRDS/OptionMetrics, Refinitiv or Bloomberg? If not, is there a fund for a one-off purchase of historical option data? The memo attached lays out the options. This decides what the paper can claim, so I need it within two weeks.
> 2. **Sign-off on the hypothesis and evaluation design** in the one-page pre-analysis plan.
> 3. **A conversation about authorship**, using the attached draft as a starting point.
>
> Could we meet for 45 minutes this week or next? I will bring a short list of questions.
>
> Thank you,
> Krishiv Wahi
