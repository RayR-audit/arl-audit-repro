# Methodology — MCP declared-surface conformance probe (Tier 1)

This directory contains a read-only probe that compares **two declared surfaces** of an
MCP server and reports the mechanical differences between them:

| Surface | Source |
|---|---|
| **A. Registry declaration** | the official MCP registry listing (`registry.modelcontextprotocol.io/v0/servers`, paginated, cached with fetch timestamp) |
| **B. Repository declaration** | the server's own public repository — `README.md`, one package manifest (`package.json` / `pyproject.toml` / `Cargo.toml` / `server.json`), and the latest release tag |

## What is measured

| Check | Meaning |
|---|---|
| C1 | Is the server listed in the public registry (matched by exact registry name, else by repository URL)? |
| C2 | Does the registry entry's `repository.url` point at the repository being checked? |
| C3 | Are the registry entry's required fields (`name` / `description` / `version`) present? |
| C4 | Do the registry version and the repository's own declared version agree? |
| C5 | Do the registry's package identifiers (or remote types) and the README's install/transport instructions agree? Verdicts: `PASS` = every declared remote type is mentioned in the README; `PARTIAL` = the README documents a different transport than the one declared; `DIFF` = no overlap. |

Every check is a string/set comparison over public documents. `DIFF` means **two public
declarations differ** — it is not a statement that either is wrong, outdated on purpose, or
that anything is broken.

## What this probe deliberately does NOT do

- It does **not** execute third-party code. No `npx`, no container run, no local install.
- It does **not** authenticate, and it **does not** send any request to a server endpoint.
- It does **not** test for vulnerabilities, misconfiguration, or security properties.
- It makes **no** statement about service quality, integrity, intent, or fitness for use.
- It does **not** crawl: one request per URL, ≥1.2 s pacing, 20 s timeout, no retry storms.

## Known limits (carry these with any figure)

1. **Pagination cap.** The registry listing is fetched page by page up to a fixed cap. An
   `ABSENT` verdict means *not found in the pages fetched on that date*, not "not registered".
   The fetch timestamp and entry count are recorded in `registry_cache.json`.
2. **Version strings are compared as strings.** Repositories may legitimately use different
   version schemes per document (for example a release tag alongside a document-local schema
   version). A `DIFF` is a divergence between documents, not necessarily a defect.
3. **Manifest selection is best-effort.** At most one manifest is read, in a fixed order; a
   repository that declares its version elsewhere will read as `UNKNOWN`.
4. **README parsing is regex-based.** Install-command and transport mentions are extracted
   textually; absence of a mention is not absence of the capability.

## Reproduction

```
python mcp_conformance_probe.py --stage registry      # cache the registry listing
python mcp_conformance_probe.py --repo owner/name     # one ad-hoc target
python mcp_conformance_probe.py --stage targets       # every target in targets.json
```

Reports land in `reports/` as one JSON file per target.
