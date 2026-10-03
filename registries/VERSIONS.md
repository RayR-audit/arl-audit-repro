# x402 Registry — calibre version record

> The moat of this line of work is the **calibre record**, not elapsed time. Any change to how
> an output is produced must bump the version and record the difference.

## v0.1 (2026-09-27)

- **Registry**: `base_facilitators.csv` = 105 addresses mapped to facilitator names. Source: a
  Tektonic-derived registry (frozen 2026-09-13 batch).
- **Inclusion rule**: facilitator contract addresses that appear in the upstream Tektonic
  archive (Base table). No proactive additions were made.
- **Label gate**: none. v0.1 carries no behavioural labels — only the address-to-name mapping.
- **Known boundary**: the upstream archive stopped updating on 2026-04-14 (a 131-day window
  as-of that date). Facilitators that first appeared after 2026-04-14 are not in the table.
  This is the most important calibre limitation of the table, and every quotation of a
  coverage figure must carry this sentence.
- **Gap-ledger (`registry_gap/`) definitions**:
  - Type A = a `402` challenge whose settlement-layer address is **not** in the registry.
  - Type B = self-reported x402 support with **zero** on-chain addresses disclosed in public
    documentation.
  - Both classifications concern settlement-path attribution only. Neither is a statement about
    service quality or integrity.
- **Alternative source (not integrated)**: the Dune curated `payments.agentic_payments` dataset
  (x402 + MPP, Base / Polygon / Solana, carrying facilitator names). Until it has been run end
  to end, it must not be used to change the calibre of any output.
- **Change discipline**: any field addition/removal or inclusion-rule change requires a version
  bump, a written difference, and a list of the downstream artefacts it affects.
