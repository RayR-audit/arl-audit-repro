# Type A probe v3: header (request=b64) AND body-JSON challenge paths, x402 v1+v2 shapes.
# Extracts ONLY payTo/recipient from accepts[] or top-level -- never currency contracts.
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

KNOWN_CURRENCY = {
    '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913',  # Base USDC
    '0x3c499c542cef5e3811e1192ce70d8cc03d5c3359',  # Polygon USDC (native)
    '0xaf88d065e77c8cc2239327c5edb3a432268e5831',  # Arbitrum USDC
}

def load_registry():
    return {r['address'].lower() for r in csv.DictReader(open(REG_CSV, encoding='utf-8'))}

def extract_payees(obj):
    """Recursively find payTo/recipient values in challenge JSON (dict/list)."""
    out = []
    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ('payTo', 'recipient', 'pay_to', 'payee') and isinstance(v, str) and re.match(r'^0x[a-fA-F0-9]{40}$', v):
                    out.append(v)
                else:
                    walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(obj)
    return [a for a in out if a.lower() not in KNOWN_CURRENCY]

def decode_request(www):
    m = re.search(r'request="([^"]+)"', www or '')
    if not m:
        return None
    b64 = m.group(1) + '=' * (-len(m.group(1)) % 4)
    try:
        return json.loads(base64.b64decode(b64))
    except Exception:
        return None

def probe(url):
    try:
        opener.open(urllib.request.Request(url), timeout=15)
        return {'state': 'NO_402', 'method': '', 'payees': [], 'via': ''}
    except urllib.error.HTTPError as e:
        if e.code != 402:
            return {'state': 'HTTP_%d' % e.code, 'method': '', 'payees': [], 'via': ''}
        www = e.headers.get('WWW-Authenticate', '') or ''
        method = ''
        if 'method=' in www:
            try:
                method = www.split('method=')[1].split(',')[0].strip('"')
            except Exception:
                pass
        # path 1: header request=
        j = decode_request(www)
        if j:
            return {'state': 'CHALLENGE', 'method': method, 'payees': extract_payees(j), 'via': 'header'}
        # path 2: body JSON (x402 v2)
        try:
            body = e.read().decode('utf-8', 'replace')
            j = json.loads(body)
            return {'state': 'CHALLENGE', 'method': method or 'x402v2', 'payees': extract_payees(j), 'via': 'body'}
        except Exception:
            return {'state': 'CHALLENGE', 'method': method, 'payees': [], 'via': 'unparsed'}
    except Exception:
        return {'state': 'ERR', 'method': '', 'payees': [], 'via': ''}

def main():
    reg = load_registry()
    done = set()
    if os.path.exists(OUT):
        done = {r['resource'] for r in csv.DictReader(open(OUT, encoding='utf-8'))}
    rows = [json.loads(l) for l in open(SRC, encoding='utf-8')]
    payable = [r for r in rows if r['state'] == 'PAYABLE']
    newfile = not os.path.exists(OUT)
    with open(OUT, 'a', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        if newfile:
            w.writerow(['resource', 'host', 'probe_state', 'method', 'via', 'payees', 'payee_in_registry', 'gap_type'])
        for i, r in enumerate(payable):
            if r['resource'] in done:
                continue
            res = probe(r['resource'])
            if res['state'] == 'CHALLENGE':
                if not res['payees']:
                    gap = 'no_payee'
                else:
                    inreg = any(p.lower() in reg for p in res['payees'])
                    gap = 'A_in' if inreg else 'A_out'
            else:
                gap = ''
            w.writerow([r['resource'], r['host'], res['state'], res['method'], res['via'], ';'.join(res['payees']),
                        '1' if gap == 'A_in' else ('0' if gap in ('A_out',) else ''), gap])
            f.flush()
            print('%d/%d %s %s %s' % (i+1, len(payable), r['host'][:38], res['state'], gap))
            time.sleep(2)

if __name__ == '__main__':
    main()
