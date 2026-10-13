# MCP declared-surface conformance probe

Read-only probe that compares an MCP server's **registry declaration** against its
**repository declaration** and reports mechanical differences. It never executes third-party
code, never authenticates, and never contacts a server endpoint. See [METHODOLOGY.md](METHODOLOGY.md)
for the check list, the deliberate non-goals, and the known limits.

```
python mcp_conformance_probe.py --stage registry
python mcp_conformance_probe.py --repo owner/name
```

Output: one JSON report per target under `reports/`, plus a cached registry listing with its
fetch timestamp and entry count.

**Corrections are welcome and are merged with attribution.** If a `DIFF` in your report is
explained by something we did not read (a second manifest, a different version scheme, a
registry entry outside the fetched pages), tell us and we will re-run and correct the record.
