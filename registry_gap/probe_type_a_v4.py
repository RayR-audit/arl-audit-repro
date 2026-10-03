# -*- coding: utf-8 -*-
"""v4 full probe: submitter-join coverage over ALL payees from probe_results_v3.csv.
Resumable via a state file; rate-limited (1.1s/req).
Design: for each payee, pull inbound USDC Transfer logs on Base, take tx.from per
settlement, and match it against the registry (see METHODOLOGY.md).
Acceptance vectors (validated in pilot): row1 must cover, rows 2-3 must miss.

Usage: python arl_v4_probe.py [--batch N]
  --batch N  : process up to N payees this run then checkpoint (default 12)
State: v4_state.json in the script directory (resumable).
Output: v4_results_partial.json (merged after each payee) + log lines to stdout
"""
import sys, json, time, csv, os, urllib.request


BASE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(BASE, 'v4_state.json')
PARTIAL = os.path.join(BASE, 'v4_results_partial.json')
RPC = 'https://mainnet.base.org'
USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
TOPIC_TRANSFER = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
WINDOW = 720_000  # ~30 days (2s blocks) — v4 scope: recent settlement coverage, not all-time
STEP = 2_000      # block range per eth_getLogs call (413-safe)
REQ_DELAY = 1.1

_PROXY = os.environ.get('https_proxy') or os.environ.get('HTTPS_PROXY')
_proxy_map = {'https': _PROXY} if _PROXY else {}


def rpc(method, params):
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    last = None
    for p in (_proxy_map,):
        for a in range(3):
            try:
                op = urllib.request.build_opener(urllib.request.ProxyHandler(p))
                return json.load(op.open(urllib.request.Request(RPC, data=body,
                    headers={'Content-Type': 'application/json', 'User-Agent': 'curl/8.0'}), timeout=30))
            except Exception as e:
                last = e
                time.sleep(2)
    raise last

_registry_csv = os.environ.get('REGISTRY_CSV')
if not _registry_csv:
    raise SystemExit('set REGISTRY_CSV to a CSV listing registered facilitator addresses')


def load_registry():
    reg = set()
    with open(_registry_csv, encoding='utf-8') as f:
        for row in csv.reader(f):
            if row and row[0].lower().startswith('0x'):
                reg.add(row[0].lower())
    return reg

def load_payees():
    """payees from v3 results: rows where gap_type=A_out (decoded payTo, not in registry)."""
    payees = []
    seen = set()
    with open(os.path.join(BASE, 'probe_results_v3.csv'), encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if (row.get('gap_type') or '').strip() != 'A_out':
                continue
            p = (row.get('payees') or '').strip().lower()
            if p.startswith('0x') and len(p) == 42 and p not in seen:
                seen.add(p)
                payees.append(p)
    return payees

def probe_payee(payee, reg, state):
    head = int(rpc('eth_blockNumber', []).get('result'), 16)
    start = head - WINDOW
    logs = []
    prog_key = 'prog_' + payee
    frm = state.get(prog_key, {}).get('frm', start)
    calls = 0
    print(f'[v4] {payee} resuming from block {frm}' if frm != start else f'[v4] {payee} fresh start at {frm}')
    topic2 = '0x' + '0' * 24 + payee[2:]
    while frm <= head:
        to = min(frm + STEP - 1, head)
        params = [{'fromBlock': hex(frm), 'toBlock': hex(to), 'address': USDC,
                   'topics': [TOPIC_TRANSFER, None, topic2]}]
        res = rpc('eth_getLogs', params).get('result') or []
        logs.extend(res)
        time.sleep(REQ_DELAY)
        frm = to + 1
        # heartbeat: absolute call counter (grid-aligned modulo never fired for some start points)
        calls += 1
        if calls % 20 == 0:
            state[prog_key] = {'frm': frm}
            with open(STATE, 'w') as f:
                json.dump(state, f)
    submitters = {}
    for lg in logs:
        txh = lg['transactionHash']
        if txh not in submitters:
            tx = rpc('eth_getTransactionByHash', [txh]).get('result')
            submitters[txh] = (tx or {}).get('from', '').lower()
            time.sleep(REQ_DELAY)
    covered = [t for t, s in submitters.items() if s in reg]
    return {'logs': len(logs), 'settlements': len(submitters),
            'covered': len(covered),
            'submitters': sorted(set(submitters.values()))}

def main():
    batch = 12
    if '--batch' in sys.argv:
        batch = int(sys.argv[sys.argv.index('--batch') + 1])
    reg = load_registry()
    payees = load_payees()
    state = json.load(open(STATE)) if os.path.exists(STATE) else {'done': {}}
    results = json.load(open(PARTIAL)) if os.path.exists(PARTIAL) else {}
    todo = [p for p in payees if p not in state['done']]
    print(f'[v4] payees total={len(payees)} done={len(state["done"])} todo={len(todo)} batch={batch}')
    processed = 0
    try:
        for p in todo:
            if processed >= batch:
                break
            t0 = time.time()
            try:
                # clear stale per-payee progress so a re-run starts fresh
                state.pop('prog_' + p, None)
                r = probe_payee(p, reg, state)
                results[p] = r
                state['done'][p] = {'ts': time.strftime('%Y-%m-%dT%H:%M:%S')}
                cov = f"{r['covered']}/{r['settlements']}" if r['settlements'] else 'n/a'
                print(f"[v4] {p} logs={r['logs']} settlements={r['settlements']} covered={cov} ({time.time()-t0:.0f}s)")
            except Exception as e:
                state['done'][p] = {'ts': time.strftime('%Y-%m-%dT%H:%M:%S'), 'error': str(e)[:200]}
                print(f"[v4] {p} ERROR {str(e)[:120]}")
            processed += 1
            # checkpoint every payee
            with open(PARTIAL, 'w') as f:
                json.dump(results, f)
            with open(STATE, 'w') as f:
                json.dump(state, f)
            time.sleep(REQ_DELAY)
    finally:
        done_n = len(state['done'])
        total = len(payees)
        with_cov = [r for r in results.values() if r.get('settlements', 0) > 0]
        cov_sum = sum(r['covered'] for r in with_cov)
        set_sum = sum(r['settlements'] for r in with_cov)
        print(f'[v4] PROGRESS {done_n}/{total} payees done')
        if set_sum:
            print(f'[v4] running coverage: {cov_sum}/{set_sum} = {cov_sum/set_sum*100:.1f}% '
                  f'(over {len(with_cov)} payees with settlements)')
        if done_n >= total:
            print('[v4] COMPLETE - ready to merge into v4_results.json')

if __name__ == '__main__':
    main()
