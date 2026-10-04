# arl-audit-repro — reproducible evaluation pack

Public companion to an independent audit of the **x402** agent-payment protocol stack. This
repository carries **method and results**, and deliberately carries **no settlement data and no
address-level scoring**.

Identity: **Ray R · Independent Researcher**. Work is published pseudonymously; the pack is
self-contained and every claim below is checkable from the files in this repository.

## Contents

| Path | What it is |
|---|---|
| `audits/x402_v0.2_20261004.pdf` | **The audit report (x402, v0.2), published release artifact** — identical text to the Zenodo deposit of this version |
| `audits/x402_v0.2_20261004.md` | Markdown source of the v0.2 release artifact |
| `audits/x402_v0.2_draft_20260919.md` | Pre-release draft of v0.2, kept so that the evolution of claims is auditable |
| `audits/x402_v0.1_draft_20260907.md` | The earlier draft, kept so that the evolution of claims is auditable |
| `scorecard/index.html` | Static evaluation scorecard (published at the project's landing page) |
| `notes/data_note_1_preliminary_20260916.md` | Preliminary data note (published on Zenodo; see below) |
| `registry_gap/METHODOLOGY.md` | How the registry-gap ledger is produced, its calibre record, and its scope limits |
| `registry_gap/probe_type_a*.py` | The probes that produce Type A observations — the script is the evidence |
| `registries/VERSIONS.md` | Calibre version record for the reference registry |

## Reproducing

The probes take their inputs as arguments and ship with no data:

```bash
python registry_gap/probe_type_a_v3.py --registry <facilitators.csv> --source <hosts.jsonl> --out <out.csv>
```

- `<facilitators.csv>` — a CSV listing registered facilitator contracts (header column `address`).
  Build or supply your own registry; the scope and boundary conditions of the registry used for
  the published run are recorded in `registries/VERSIONS.md`, and that record is the thing that
  makes a comparison meaningful.
- `<hosts.jsonl>` — one JSON object per line, each carrying the resource URL to probe.

`probe_type_a_v4.py` reads its registry path from the `REGISTRY_CSV` environment variable and
checkpoints to `v4_state.json` so that a long sweep can resume.

Before quoting any coverage figure, read `registry_gap/METHODOLOGY.md` §2 and §3: the join
between a challenge's disclosed recipient and a facilitator registry is structurally incapable
of producing a positive match, and every figure needs a positive control.

## What is intentionally absent

- The reference registry itself and any address-to-operator mapping.
- Any per-address or per-host rating. Public outputs are aggregates and coverage statements only.
- Raw probe results that contain real addresses, including decode datasets and state files.
- The implementation of the paid query endpoint.

If a number here needs to be checked against data rather than against method, the route is a
direct exchange or the query endpoint — this repository alone is not sufficient for that, and
says so on purpose.

## Related

- Data note (preliminary), Zenodo DOI `10.5281/zenodo.22807288`.

## Licence

See `LICENSE`.
