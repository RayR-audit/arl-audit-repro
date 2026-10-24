# -*- coding: utf-8 -*-
"""MCP declared-surface conformance probe — Tier 1 (static, read-only).

WHAT IT DOES: compares two *declared* surfaces for one MCP server —
  (A) the official MCP registry entry (registry.modelcontextprotocol.io)
  (B) the server's own public repository (README + package manifest / latest release)
and reports mechanical differences between them.

WHAT IT DELIBERATELY DOES NOT DO: it never executes third-party code, never
authenticates, never sends a request to a server endpoint, never probes for
vulnerabilities or misconfiguration, and never assesses intent, security or
quality. Every check below is a set/text comparison over public documents.

Boundary: one request per URL, >=1.2s pacing, hard 20s timeout, no retries that
hammer a host. Only public endpoints (registry API, GitHub REST/raw).

Usage:
  python mcp_conformance_probe.py --stage registry     # cache registry listing
  python mcp_conformance_probe.py --stage targets      # per-target report
"""
import json, re, os, sys, time, base64, urllib.request, urllib.error, urllib.parse

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"
ROOT = os.path.dirname(os.path.abspath(__file__))
REG_API = "https://registry.modelcontextprotocol.io/v0/servers"
REG_CACHE = os.path.join(ROOT, "registry_cache.json")
REPORT_DIR = os.path.join(ROOT, "reports")

def _load_targets():
    """Targets come from --repo (single, ad hoc) or targets.json next to this script.

    targets.json shape: [{"id": "optional-label", "repo": "owner/name",
                          "registry_name": "optional/exact-registry-name"}, ...]
    """
    if "--repo" in sys.argv:
        r = sys.argv[sys.argv.index("--repo") + 1]
        rn = sys.argv[sys.argv.index("--registry-name") + 1] if "--registry-name" in sys.argv else None
        return [{"id": "ad-hoc", "repo": r, "registry_name": rn}]
    p = os.path.join(ROOT, "targets.json")
    if os.path.exists(p):
        return json.load(open(p, encoding="utf-8"))
    print("no targets: pass --repo owner/name or create targets.json (see targets.example.json)")
    return []


TARGETS = []   # filled in __main__ from --repo / targets.json

def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read(2000).decode("utf-8", "replace")
    except Exception as e:
        return None, "ERR:%s:%s" % (type(e).__name__, str(e)[:90])

def gh_contents(repo, path=""):
    st, body = fetch("https://api.github.com/repos/%s/contents/%s" % (repo, path))
    if st != 200:
        return None
    try:
        return json.loads(body)
    except Exception:
        return None

# ---------------- stage 1: registry cache ----------------
# 上限修复（2026-10-24）：原 12 页 = 1200 条，registry 实际条目远超此数（search=dinglebear
# 单关键词即 60+ 条），导致 BuyWhere / ClawFetch / dinglebear 三家被误判 ABSENT（假阴性）。
# 修法两层：① 全量上限提到 60 页；② 新增 stage_registry_targeted 按 target 关键词定向 search，
# 命中结果并入 cache（去重按 server.name + version）。ABSENT 结论只有在「全量 + 定向」都空时才可写。
MAX_PAGES = 60

def _merge_registry(extra, tag):
    """把 extra 里的 server 条目并入 REG_CACHE（按 name+version 去重）。"""
    if not os.path.exists(REG_CACHE):
        cache = {"fetched": None, "count": 0, "servers": []}
    else:
        cache = json.load(open(REG_CACHE, encoding="utf-8"))
    seen = set()
    for e in cache.get("servers") or []:
        s = e.get("server") or {}
        seen.add((s.get("name"), s.get("version")))
    added = 0
    for e in extra:
        s = e.get("server") or {}
        k = (s.get("name"), s.get("version"))
        if k in seen:
            continue
        seen.add(k)
        cache["servers"].append(e)
        added += 1
    cache["count"] = len(cache["servers"])
    cache["fetched"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    cache.setdefault("extra_sources", [])
    cache["extra_sources"].append({"stage": tag, "added": added})
    json.dump(cache, open(REG_CACHE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("MERGED[%s] +%d -> total %d" % (tag, added, cache["count"]))
    return cache

def stage_registry_targeted():
    """按 target 的 owner/repo 关键词定向 search，补全全量抓取漏掉的条目。"""
    extra = []
    for t in TARGETS:
        repo = t["repo"]
        owner, _, name = repo.partition("/")
        for q in {owner, name, repo}:
            if not q:
                continue
            url = REG_API + "?search=" + urllib.parse.quote(q) + "&limit=100"
            st, body = fetch(url)
            if st != 200:
                print("search %r -> %s" % (q, st)); continue
            try:
                j = json.loads(body)
            except Exception:
                continue
            got = j.get("servers") or []
            extra.extend(got)
            print("search %-30r +%d" % (q, len(got)))
            time.sleep(1.2)
    if extra:
        _merge_registry(extra, "targeted_search")
    else:
        print("targeted search: 0 entries")

def stage_registry():
    out, url, pages = [], REG_API + "?limit=100", 0
    while url and pages < MAX_PAGES:
        st, body = fetch(url)
        if st != 200:
            print("registry page %d -> %s" % (pages, st)); break
        try:
            j = json.loads(body)
        except Exception as e:
            print("registry parse err", e); break
        entries = j.get("servers") or []
        out.extend(entries)
        meta = j.get("metadata") or {}
        cur = meta.get("nextCursor") or meta.get("next_cursor")
        url = (REG_API + "?limit=100&cursor=" + str(cur)) if cur else None
        pages += 1
        print("page %d: +%d entries (total %d)%s" % (pages, len(entries), len(out), " next" if cur else " end"))
        time.sleep(1.2)
    json.dump({"fetched": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "count": len(out), "servers": out}, open(REG_CACHE, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("WROTE", REG_CACHE, len(out), "entries")

# ---------------- stage 2: per-target conformance ----------------
def latest_release(repo):
    st, b = fetch("https://api.github.com/repos/%s/releases/latest" % repo)
    if st == 200:
        try:
            return json.loads(b).get("tag_name")
        except Exception:
            return None
    return None

def manifest_version(repo):
    """version declared in the repo's own package manifest (best effort, first hit)."""
    for path, pat in [("package.json", r'"version"\s*:\s*"([^"]+)"'),
                      ("pyproject.toml", r'^version\s*=\s*"([^"]+)"'),
                      ("Cargo.toml", r'^version\s*=\s*"([^"]+)"'),
                      ("server.json", r'"version"\s*:\s*"([^"]+)"')]:
        st, b = fetch("https://raw.githubusercontent.com/%s/HEAD/%s" % (repo, path))
        if st == 200 and "ERR:" not in b:
            m = re.search(pat, b, re.M)
            if m:
                return {"path": path, "version": m.group(1)}
    return None

def stage_targets():
    if not os.path.exists(REG_CACHE):
        print("no registry cache; run --stage registry first"); return
    reg = json.load(open(REG_CACHE, encoding="utf-8"))["servers"]
    os.makedirs(REPORT_DIR, exist_ok=True)
    summary = []
    for t in TARGETS:
        repo, rname = t["repo"], t["registry_name"]
        rep = {"target": t, "checks": []}
        # --- registry side ---
        # 2026-10-24 修复：ABSENT 不得只依赖 cache 命中。cache 来自全量枚举，而 registry 无总数、
        # 实测 >6000 条且仍有 next，历史 12 页上限导致 3 家假阴性。故：cache 未命中 → 现场定向 search
        # → 合并 cache 后重试匹配。只有「cache + 现场 search 三关键词变体」全空，才允许写 ABSENT。
        def _off(e):
            return ((e.get("_meta") or {}).get("io.modelcontextprotocol.registry/official") or {})

        def _pick_latest(cands):
            """Among entries with the same server name, the registry keeps one row per
            published version. The *current* declaration is the one flagged
            isLatest=True -- NOT the first row returned (which is the oldest version).
            Picking the first row silently turns a PASS into a false DIFF."""
            if not cands:
                return None
            flagged = [e for e in cands if _off(e).get("isLatest")]
            if flagged:
                return flagged[0]
            return sorted(cands, key=lambda e: (_off(e).get("publishedAt") or ""))[-1]

        def _match(entries):
            by_name = [e for e in entries if rname and ((e.get("server") or {}).get("name")) == rname]
            if by_name:
                return _pick_latest(by_name)
            by_repo = [e for e in entries
                       if repo.lower() in (((e.get("server") or {}).get("repository") or {}).get("url") or "").lower()]
            return _pick_latest(by_repo)

        hit = _match(reg)
        live_search_used = False
        if hit is None:
            live_search_used = True
            owner, _, rname_only = repo.partition("/")
            live = []
            for q in {owner, rname_only, repo}:
                if not q:
                    continue
                u = REG_API + "?search=" + urllib.parse.quote(q) + "&limit=100"
                st, body = fetch(u)
                if st != 200:
                    print("  live search %r -> %s" % (q, st)); continue
                try:
                    j = json.loads(body)
                except Exception:
                    continue
                got = j.get("servers") or []
                live.extend(got)
                print("  live search %-30r +%d" % (q, len(got)))
                time.sleep(1.2)
            if live:
                _merge_registry(live, "live_" + repo.replace("/", "_"))
                reg = json.load(open(REG_CACHE, encoding="utf-8"))["servers"]
                hit = _match(reg)
        entry = (hit or {}).get("server") or {}
        # 同 name 在 registry 的版本行数（用于 C4 口径可核查：>1 时必须取 isLatest）
        _n_versions = len([e for e in reg if rname and ((e.get("server") or {}).get("name")) == rname])
        meta = ((hit or {}).get("_meta") or {}).get("io.modelcontextprotocol.registry/official") or {}
        rep["registry"] = {"listed": bool(hit), "name": entry.get("name"), "version": entry.get("version"),
                           "packages": [p.get("identifier") for p in (entry.get("packages") or [])],
                           "remotes": [r.get("type") for r in (entry.get("remotes") or [])],
                           "repository": (entry.get("repository") or {}).get("url"),
                           "status": meta.get("status"), "updatedAt": meta.get("updatedAt"),
                           # 2026-10-24 补：版本选取必须可核查 —— 同 name 在 registry 有
                           # 多行（每发布一版一行），C4 只能比 isLatest 那一行。
                           "isLatest": meta.get("isLatest"), "publishedAt": meta.get("publishedAt"),
                           "versions_in_registry": _n_versions}
        def add(cid, status, detail):
            rep["checks"].append({"id": cid, "status": status, "detail": detail})
        # C1 listed
        add("C1_listed_in_official_registry",
            "PASS" if hit else "ABSENT",
            "registry entry found: %s" % (entry.get("name") if hit else "no entry matched by name or repository URL"))
        if hit:
            add("C2_registry_repository_matches_repo", "PASS" if repo.lower() in ((entry.get("repository") or {}).get("url") or "").lower() else "DIFF",
                "registry repository url = %r" % ((entry.get("repository") or {}).get("url")))
            add("C3_required_fields_present",
                "PASS" if all(entry.get(k) for k in ("name", "description", "version")) else "DIFF",
                "name/description/version present = %s" % {k: bool(entry.get(k)) for k in ("name", "description", "version")})
        # --- repo side ---
        readme = fetch("https://raw.githubusercontent.com/%s/HEAD/README.md" % repo)
        rtxt = readme[1] if readme[0] == 200 else ""
        rel = latest_release(repo)
        man = manifest_version(repo)
        rep["repo"] = {"readme_chars": len(rtxt), "latest_release": rel, "manifest": man}
        if rtxt:
            install = re.findall(r"(npx|uvx|pip install|docker run|go install|pnpm dlx)\s+[^\s`\"']+", rtxt)
            rep["repo"]["install_commands"] = sorted(set(install))[:6]
            rep["repo"]["mentions_streamable_http"] = bool(re.search(r"streamable[- ]?http", rtxt, re.I))
            rep["repo"]["mentions_sse"] = bool(re.search(r"\bSSE\b|server-sent", rtxt, re.I))
            rep["repo"]["mentions_auth"] = bool(re.search(r"api[_ -]?key|bearer|oauth|token", rtxt, re.I))
            if hit:
                # C4 version drift: registry vs (repo manifest, else latest release)
                rv = (man or {}).get("version") or (rel or "").lstrip("v")
                same = bool(rv) and str(entry.get("version") or "").lstrip("v").startswith(str(rv).lstrip("v"))
                add("C4_version_registry_vs_repo", "PASS" if same else ("DIFF" if rv else "UNKNOWN"),
                    "registry=%r repo_manifest=%r latest_release=%r" % (entry.get("version"), (man or {}).get("version"), rel))
                # C5 transport/package declared on both sides
                if entry.get("packages"):
                    ids = [str(p) for p in rep["registry"]["packages"]]
                    hit_id = any(any(i in c for i in ids) for c in rep["repo"]["install_commands"]) if rep["repo"]["install_commands"] else False
                    add("C5_package_identifier_matches_install_command", "PASS" if hit_id else "DIFF",
                        "registry packages=%r ; readme install=%r" % (ids, rep["repo"].get("install_commands")))
                else:
                    rts = [r.get("type") for r in (entry.get("remotes") or [])]
                    rd = {"streamable-http": rep["repo"]["mentions_streamable_http"], "sse": rep["repo"]["mentions_sse"]}
                    if rts and all(rd.get(t) for t in rts):
                        c5 = "PASS"
                    elif rts and any(rd.get(t) for t in rts):
                        c5 = "PARTIAL"
                    else:
                        c5 = "DIFF"
                    add("C5_remote_declared_matches_readme", c5,
                        "registry remotes=%r ; readme streamable-http=%s sse=%s" % (rts, rep["repo"]["mentions_streamable_http"], rep["repo"]["mentions_sse"]))
        else:
            add("C0_repo_readme_reachable", "ABSENT", "README not retrievable at this run")
        p = os.path.join(REPORT_DIR, "conformance_%s_%s.json" % (t["id"], repo.replace("/", "_")))
        json.dump(rep, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        summary.append((t["id"], repo, rep["registry"]["listed"], [c["status"] for c in rep["checks"]], p))
        time.sleep(1.2)
    print("\n%-5s %-28s %-8s %s" % ("ID", "REPO", "LISTED", "CHECKS"))
    for s in summary:
        print("%-5s %-28s %-8s %s" % (s[0], s[1][:28], s[2], " ".join("%s=%s" % (i, v) for i, v in enumerate(s[3]))))
    print("\nreports in", REPORT_DIR)

if __name__ == "__main__":
    TARGETS = _load_targets()
    stage = sys.argv[sys.argv.index("--stage") + 1] if "--stage" in sys.argv else "all"
    if stage in ("registry", "all"):
        stage_registry()
        stage_registry_targeted()
    if stage in ("targets", "all"):
        stage_targets()
