"""Fetches every 2018-2026 Senate nominee's campaign finance reports from the FEC's API (api.open.fec.gov), into
samples/, for testing money raised by each date in the Senate forecast. Run by the "Source samples" workflow with
script=tools/fetch_fec_reports.py; the API key is read from the FEC_API_KEY secret and never written or printed.

For each nominee: the reports of their campaign committees for the election's two-year cycle (most recent version of
each, amendments applied), with the dates they cover, the date the FEC received them, and the money raised in each.
2026 nominees' FEC numbers are found by searching the FEC's candidate list by state, office and name.
"""
import json, os, re, sys, time, urllib.parse, urllib.request
import pandas as pd

KEY = os.environ.get('FEC_API_KEY', '')
API = 'https://api.open.fec.gov/v1'
OUT = os.path.join(os.getcwd(), 'samples'); os.makedirs(OUT, exist_ok=True)
FIELDS = ('committee_id', 'report_type', 'report_year', 'coverage_start_date', 'coverage_end_date', 'receipt_date', 'total_receipts_period',
          'total_individual_contributions_period', 'cash_on_hand_end_period', 'is_amended', 'most_recent', 'candidate_id')
log, calls = [], [0]


def get(path, **params):
    q = urllib.parse.urlencode({**params, 'api_key': KEY})
    for i in range(6):
        try:
            calls[0] += 1
            with urllib.request.urlopen(urllib.request.Request(f'{API}{path}?{q}', headers={'User-Agent': 'election-research'}), timeout=60) as r:
                out = json.loads(r.read())
            time.sleep(3.7)                                    # under 1,000 calls an hour
            return out
        except urllib.error.HTTPError as e:
            err = f'HTTP {e.code}'; time.sleep(60 if e.code == 429 else 10 * (i + 1))
        except Exception as e:                                 # noqa: BLE001 - logged and retried
            err = type(e).__name__; time.sleep(10 * (i + 1))
    log.append({'path': path, 'params': {k: v for k, v in params.items()}, 'error': err}); return None


def surname(n):
    n = str(n).upper().replace("'", '')
    if ',' in n: n = n.split(',')[0]
    w = [x for x in re.findall(r'[A-Z][A-Z-]*', n) if x not in ('JR', 'SR', 'II', 'III', 'IV') and len(x) > 1]
    return w[-1] if w else ''


def find_id(name, state, party, year):
    j = get('/candidates/search/', q=surname(name), state=state, office='S', election_year=year, per_page=20)
    hits = [c for c in (j or {}).get('results', []) if surname(c.get('name', '')) == surname(name)]
    want = {'D': ('DEM', 'DFL'), 'R': ('REP',), 'I': ('IND', 'NPA', 'NNE', 'UN', 'OTH')}[party]
    pick = [c for c in hits if c.get('party') in want] or hits
    return pick[0]['candidate_id'] if pick else None


def reports(cid, year):
    out, page = [], 1
    while True:
        j = get('/reports/house-senate/', candidate_id=cid, cycle=year, per_page=100, page=page, sort='coverage_end_date')
        if not j: break
        out += [{k: r.get(k) for k in FIELDS} for r in j.get('results', [])]
        if page >= j.get('pagination', {}).get('pages', 1): break
        page += 1
    return out


def main():
    if not KEY:
        print('FEC_API_KEY is not set'); sys.exit(1)
    R = pd.read_csv('data/senate/races.csv'); R26 = pd.read_csv('data/senate/2026/races_2026.csv'); R26['year'] = 2026
    data = {}
    for r in R.itertuples():
        for side, cid in (('dem', r.dem_fec), ('rep', r.rep_fec)):
            if isinstance(cid, str) and cid:
                data[f'{r.year}|{r.state}|{r.special}|{side}'] = {'candidate_id': cid, 'reports': reports(cid, int(r.year))}
    for r in R26.itertuples():
        for side, name, party in (('dem', r.dem, 'I' if r.dem_independent else 'D'), ('rep', r.rep, 'R')):
            cid = find_id(name, r.state, party, 2026)
            data[f'2026|{r.state}|{r.special}|{side}'] = {'candidate_id': cid, 'name': name, 'reports': reports(cid, 2026) if cid else []}
    with open(os.path.join(OUT, 'fec_reports.json'), 'w') as f: json.dump(data, f)
    log.append({'nominees': len(data), 'with_reports': sum(1 for v in data.values() if v['reports']), 'calls': calls[0]})
    with open(os.path.join(OUT, 'fetch_log.json'), 'w') as f: json.dump(log, f, indent=1)
    print(json.dumps(log[-1]))


if __name__ == '__main__':
    main()
