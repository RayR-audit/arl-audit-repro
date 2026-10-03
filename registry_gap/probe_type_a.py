# Type A registry-gap probe: fetch 402 challenges, decode payment request, extract settlement addresses.
# Rate-limited: 2s between requests, resumable, output CSV.
# Source data lives in agent-economy-audit/registries (shared); output lands here (arl-audit/registry_gap).
import urllib.request, urllib.error, json, base64, re, time, csv, os

# --- configuration (public version: paths are arguments, never hardcoded) ---
import argparse

_ap = argparse.ArgumentParser(description=__doc__)
_ap.add_argument('--registry', required=True,
                 help='CSV listing registered facilitator contracts (header column: address)')
_ap.add_argument('--source', required=True,
                 help='JSONL snapshot of target hosts, one JSON object per line')
_ap.add_argument('--out', default='probe_results.csv', help='output CSV path')
_args = _ap.parse_args()

_PROXY = os.environ.get('https_proxy') or os.environ.get('HTTPS_PROXY')
opener = urllib.request.build_opener(
    urllib.request.ProxyHandler({'http': _PROXY, 'https': _PROXY} if _PROXY else {}))
opener = urllib.request.build_opener(urllib.request.ProxyHandler(PROXY))
opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0')]

REG_CSV = _args.registry
SRC = _args.source
OUT = _args.out

def load_registry():
    return {r['address'].lower() for r in csv.DictReader(open(REG_CSV, encoding='utf-8'))}

def load_done():
    done = set()
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT, encoding='utf-8')):
            done.add(r['resource'])
    return done

def probe(url):
    """Returns dict: state, addrs(list), method."""
    try:
        resp = opener.open(urllib.request.Request(url), timeout=15)
        return {'state': 'NO_402', 'addrs': [], 'method': ''}
    except urllib.error.HTTPError as e:
        if e.code != 402:
            return {'state': 'HTTP_%d' % e.code, 'addrs': [], 'method': ''}
        www = e.headers.get('WWW-Authenticate', '') or ''
        addrs = set()
        method = ''
        m = re.search(r'request="([^"]+)"', www)
        if m:
            b64 = m.group(1) + '=' * (-len(m.group(1)) % 4)
            try:
                j = json.loads(base64.b64decode(b64))
                addrs |= set(re.findall(r'0x[a-fA-F0-9]{40}', json.dumps(j)))
                if 'method=' in www:
                    method = www.split('method=')[1].split(',')[0].strip('"')
            except Exception:
                addrs |= set(re.findall(r'0x[a-fA-F0-9]{40}', www))
        else:
            try:
                body = e.read().decode('utf-8', 'replace')[:8000]
                addrs |= set(re.findall(r'0x[a-fA-F0-9]{40}', body))
            except Exception:
                pass
        return {'state': 'CHALLENGE', 'addrs': sorted(addrs), 'method': method}
    except Exception as ex:
        return {'state': 'ERR_' + str(ex)[:30], 'addrs': [], 'method': ''}

def main():
    reg = load_registry()
    done = load_done()
    rows = [json.loads(l) for l in open(SRC, encoding='utf-8')]
    payable = [r for r in rows if r['state'] == 'PAYABLE']
    batch = payable
    newfile = not os.path.exists(OUT)
    with open(OUT, 'a', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        if newfile:
            w.writerow(['resource', 'host', 'probe_state', 'method', 'addrs', 'in_registry_count', 'gap_type'])
        for i, r in enumerate(batch):
            if r['resource'] in done:
                continue
            res = probe(r['resource'])
            inreg = sum(1 for a in res['addrs'] if a.lower() in reg)
            gap = ''
            if res['state'] == 'CHALLENGE':
                gap = 'A_out' if (res['addrs'] and inreg == 0) else ('A_in' if inreg > 0 else 'no_addr')
            w.writerow([r['resource'], r['host'], res['state'], res['method'], ';'.join(res['addrs']), inreg, gap])
            f.flush()
            print('%d/%d %s %s %s' % (i+1, len(batch), r['host'][:40], res['state'], gap))
            time.sleep(2)

if __name__ == '__main__':
    main()
