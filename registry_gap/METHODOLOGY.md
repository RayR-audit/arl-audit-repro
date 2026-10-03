# Methodology — registry-gap ledger (Type A probes)

This document describes how the `registry_gap/` artefacts in this repository are produced,
what their inputs are, and what they deliberately do **not** contain. It is the reproducibility
companion to the registry-calibre record in [`../registries/VERSIONS.md`](../registries/VERSIONS.md).

## 1. What is being measured

For a set of target hosts that are expected to speak the x402 payment protocol, two distinct
observations are recorded and are **never mixed**:

| | Definition | Nature |
|---|---|---|
| **Type A** | A host answers with a `402` payment challenge whose **settlement-layer address is not present in the reference registry**. | Mechanical, reproducible: a set difference over address sets. |
| **Type B** | A host self-reports x402 support in its public documentation but **discloses no on-chain address anywhere**. | A statement of fact about disclosure, **not** an allegation. |

Type A is a coverage statement about the *registry*, not a judgement about the host.
Type B says nothing about integrity, quality of service, or intent, and must never be
paraphrased as such.

## 2. The join-semantics correction (read before quoting any coverage number)

A payment challenge discloses a **recipient** (`payTo`) — the merchant's settlement address.
The *facilitator* that submits the settlement transaction is a **different party** (the
transaction sender). In the `exact` scheme these two are essentially always distinct.

Consequence: **joining disclosed `payTo` values against a facilitator registry is
structurally incapable of producing a positive match**, on any registry. A headline of the
form "0 of N hosts are covered" produced that way is a property of the join, not a coverage
finding. Any number published from this ledger must state which join was used, and — see §3 —
must be accompanied by a positive control.

The correct join, as implemented in the `v4` probe, is: for each payee, pull inbound
USDC `Transfer` logs, take the transaction sender for each settlement, and match *that*
against the registry.

## 3. Positive-control requirement

Before any coverage figure from this ledger is quoted, the measurement instrument must be
shown to be capable of moving: run the same join against objects that are **known** to be in
the registry and confirm the pipeline returns a hit. An instrument that cannot return a
positive is not evidence of a negative. Scripts here therefore accept explicit acceptance
vectors; a run that fails them must be reported as instrument failure, not as a finding.

## 4. Inputs

Both inputs are **arguments**, not hardcoded paths — this repository ships no data:

- `--registry` — a CSV listing registered facilitator contracts (a header column named
  `address`). The upstream registry used for the published run is described, with its scope
  and boundary conditions, in [`../registries/VERSIONS.md`](../registries/VERSIONS.md).
- `--source` — a JSONL snapshot of target hosts, one JSON object per line, each carrying the
  resource URL to be probed.

The `v4` probe takes its registry path from the `REGISTRY_CSV` environment variable because it
is designed to run unattended and resumably (state file: `v4_state.json`).

## 5. Probes

| Script | Path covered | Notes |
|---|---|---|
| `probe_type_a.py` | challenge in the `WWW-Authenticate` header (base64 request) | original single-path probe |
| `probe_type_a_v2.py` | header + body-JSON challenge paths, x402 v1 and v2 shapes | widened decoding |
| `probe_type_a_v3.py` | as v2, with an explicit currency-contract exclusion set | extracts **only** recipient fields; currency contracts are never reported as payees |
| `probe_type_a_v4.py` | per-payee inbound `Transfer` logs, submitter join | rate-limited (1.1 s/request), resumable, public RPC endpoint |

Decoding rules that matter for reproducibility:

1. Parse **both** the `WWW-Authenticate` header and the response body; challenge shapes are
   not uniform across hosts.
2. Extract only settlement **recipient** fields. Asset/currency contract addresses must be
   excluded via an explicit set, otherwise the currency contract itself is misreported as a
   payee.
3. Rate-limit and checkpoint. A full sweep is long-running; a run that is interrupted must
   resume rather than restart.
4. A repaired bug invalidates the state accumulated before the repair. State files carry the
   calibre version they were produced under; on a calibre change, restart rather than append.

## 6. What is deliberately not published

- **The reference registry itself** and any mapping from address to operator name. Publishing it
  would invert the purpose of a coverage measurement and would identify specific parties.
- **Per-address scoring of any kind.** This project does not publish address-level or
  host-level ratings; public outputs are aggregate statistics and coverage statements only.
- **Raw probe results containing real addresses**, including the per-host challenge-decode
  dataset and partial state files.
- **The paid query endpoint implementation.** The service that answers queries about a
  supplied address is a separate product and is not part of this pack.

Aggregate outputs (counts, distributions, calibre records) are published. If you need to
verify a specific aggregate against data, the endpoint or a direct exchange is the route —
this is stated here so that "not reproducible from this repository alone" is not misread as
"unverifiable".

## 7. Scope limits that must travel with every quotation

- The upstream registry archive behind the published run stopped updating in April 2026; hosts
  that began operating after that date cannot be in the table. This is the single most
  important calibre limitation and must be restated whenever a coverage number is quoted.
- Coverage statements are about the *settlement path* only. They say nothing about service
  quality, and nothing about any host's conduct.
- A single-snapshot sweep is a lower bound at best: address rotation and per-request
  variability mean a miss is not proof of absence.
