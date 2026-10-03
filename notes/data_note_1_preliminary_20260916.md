# Data Note #1 (Preliminary) — At Most 84.1% of x402 Settlement Count Sits in Coordinated Payer Cohorts (Base, Dec 2025 – Apr 2026)

**Data Note · v0.1 · 2026-09-16 · Ray R, Independent Researcher**

**PRELIMINARY — superseded by the full report (early October 2026). Do not cite as the final result.**

> **Status: PREVIEW / PRELIMINARY.** This note releases one finding from an audit in progress. The complete report (full methodology, sensitivity analysis, figures, and replication files) is scheduled for release in early October 2026. Figures here are version-stamped to the dataset window below and may be refined in the final report. Zenodo metadata note: the creator name is a persistent pseudonym; no ORCID is linked.

---

## The finding (one number, stated with its bounds)

Filtering a public CC0 BigQuery listing to x402 settlement activity on Base yields a slice of **52,652,290 settlements routed through 105 known facilitator addresses** (99.86% of the 52,723,702 raw rows). Events span **2025-12-05 to 2026-04-14 UTC (131 days)** — the coverage period of the upstream dataset, which has not been updated since April 2026. Every number below describes that frozen window, not a live network.

Using behavioral fingerprinting and union-find clustering, we identify **181 coordinated payer cohorts comprising 52,008 wallets** — 52,008 of the 78,196 paying addresses in the slice (66.5%) — that account for **at most 84.1% of settlement count but only 24.9% of settled value** (mean ticket $0.050 vs $0.170 slice-wide).

**This is an upper bound, not a point estimate.** Fingerprints capture behavioral similarity, not intent. The bound is robust to the clustering parameters: across the merge-threshold × cohort-cutoff grid, the headline stays in a narrow band (84.1%–85.1% at ≥30–50-wallet cutoffs; 74.3%–74.4% at the ≥100 cutoff).

## Why the concentrated portion looks coordinated, not merely concentrated

Concentration alone proves nothing — the question is whether the concentrated part behaves like an operator or like many independent customers. We compare **diurnal activity rhythms** within matched volume strata: cohort wallets are systematically flatter around the clock than the rest of the network. (The amplitude is the first Fourier harmonic of a payer's 24-hour settlement histogram, normalized by its mean — following the payer-clock method of Ling et al., arXiv:2607.12575, §5.2; the fingerprinting and clustering are our own and use no funding graph.) In the 10³-settlement stratum, the median 24-hour Fourier amplitude is **0.070 for cohort wallets vs 0.375 for the rest**. The cohort median amplitude (0.070 in the 10³ stratum, 0.037 in 10⁴) sits at or below the operator-cluster baseline (0.12) and the provably-manufactured-payer baseline (0.08) reported by the independent census below; the non-cohort median in the same 10³ stratum (0.375) sits well above both anchors — the contrast is the point: cohort wallets behave like round-the-clock operators, the rest like human users with nights.

Notably, **69.0% of comparable high-volume payers outside cohorts** (n=523 in the 10³ stratum) also show no day–night cycle — suggesting that genuine, consumption-driven demand in this slice is thinner than headline settlement counts imply.

## Why settlement count is the wrong headline metric

A settlement is cheap to manufacture: gas is sponsored, and nothing on-chain marks who controls a paying wallet. Settlement count therefore measures *manufacturability*, not adoption. Two methodologically orthogonal methods converge:

- **Ling et al., "How Agentic Is Agentic Commerce? A Population-Scale Measurement of x402 Adoption and Authenticity" (arXiv:2607.12575, 2026-07-14)** — funding-provenance method: 84.98% of Base settlement count is operator-internal (63.8% inside cluster-internal loops); 21.2% provably fictitious.
- **This audit** — behavioral-fingerprint method, no funding graph used: at most 84.1% of settlement count in coordinated cohorts.

Two orthogonal methods landing near the same headline corroborates the finding at the level of method. Both analyses rest on the same underlying evidence (Base on-chain events; our slice is 38.5% of their census by count and ~20% by value), so this is convergence of methods, not fully independent replication. We did not use their data or code.

## Method (summary)

Raw event table → facilitator slice (105-address registry, treated as a scope condition, not ground truth) → payer×facilitator edge aggregation → concentration metrics (Gini: 0.974 settled value, 0.967 settlement count) → per-edge behavioral fingerprints (activity window, hour-of-day histogram, inter-settlement rhythm) → union-find clustering with a ≥3-wallet merge threshold → cohorts reported at ≥50 wallets → volume-stratified cohort-vs-rest rhythm comparison. Every step runs on BigQuery's free tier ($0.00; the full-history scan processed ~35 GB, ~3.4% of the monthly free quota); the full pipeline and queries ship with the final report under CC0.
## Limitations

1. **Upper bound.** Behavioral similarity ≠ intent; we cannot distinguish internal routers, bidders, or scripted buyer-side agents from other forms of coordination.
2. **Base only.** Solana-side x402 settlement is not covered by the upstream listing.
3. **Frozen window.** The upstream dataset stopped updating in April 2026; no figure here describes current network state.
4. **Registry dependence.** The 105-facilitator registry is hand-assembled from public announcements and on-chain labeling and may be incomplete in both directions.
5. **Aggregate disclosure only.** The mapping from Hub labels to on-chain addresses is withheld and is not recoverable from this note.
6. **Rhythm comparison arm.** The comparison arm is the network present in ≥3-wallet fingerprint groups but outside ≥50-wallet cohorts. Payers with no fingerprint group at all (2,093 of 11,408 payers with ≥100 settlements, 18.3%) are excluded — a conservative exclusion, since ungrouped singletons are the least coordination-like payers.
7. **Amplitude is a feature, not a verdict.** A scheduled agent is also regular; we never label a wallet as manufactured from its amplitude alone. (Our first threshold-based typing attempt produced an artifactually clean "99.5% bot-like" split and was discarded; only the stratified comparison is reported.) Consistent with responsible-disclosure practice for pseudonymous audit work, we publish aggregate statistics and risk intervals; we do not name facilitators, wallets, or companies, and the anonymization mapping stays internal. Full addresses are withheld; hub identities are anonymized (Hub A/B/C).

## What ships next

The complete audit report — full methodology, parameter sensitivity grids, anonymized figures, the relation-to-prior-work section, and CC0 replication files — is scheduled for release in **early October 2026**. This note will be superseded by that report; cite it as preliminary. This note releases exactly one finding: the cohort-count upper bound and its parameter band. Figures, the full 10²/10⁴ stratum tables, per-cohort breakdowns, and all replication files first appear in the full report; no other result should be cited from this note.

---

*Corrections welcome: miscomputed figures or missed prior work — open an issue on the audit repository. Corrections are merged with attribution.*

*Ray R · Independent Researcher · Data Note #1 v0.1 · 2026-09-16 · preliminary*

