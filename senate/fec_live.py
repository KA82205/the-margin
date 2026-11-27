"""Money raised by the coming election's Senate candidates, from the FEC (api.open.fec.gov), for the Senate tab. Run once
a day by .github/workflows/senate-money.yml with the FEC_API_KEY secret, which is read from the environment and never
written or printed. Shown, not used: money raised was tested twice (senate/README.md, steps 13 and 18) and made the
forecast worse.

For each seat up: the senator holding it, every declared candidate on Wikipedia's page for the year, and the nominees
once chosen. Each is found in the FEC's candidate list by state, office and surname (and first initial when two share a
surname, preferring one registered for this election), and the FEC number kept in data/senate/<year>/fec_ids.json so a
later run does not search again. Then the campaign's totals for this election (for a senator, the six years since their
last one): what it has raised, and the cash it had at its latest report.

    python senate/fec_live.py        writes data/senate/<year>/money.json and fec_ids.json
"""
import json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import live as L

KEY = os.environ.get('FEC_API_KEY', '')
API = 'https://api.open.fec.gov/v1'
FEC_PARTY = {'DEM': 'D', 'DFL': 'D', 'REP': 'R', 'IND': 'I', 'NPA': 'I', 'NNE': 'I', 'UN': 'I', 'LIB': 'L', 'GRE': 'G'}
calls = [0]


def get(path, **params):
    """One API call; the key goes in the request and nowhere else (errors name the path, never the address)."""
    q = urllib.parse.urlencode({**params, 'api_key': KEY})
    err = None
    for i in range(5):
        try:
            calls[0] += 1
            with urllib.request.urlopen(urllib.request.Request(f'{API}{path}?{q}', headers={'User-Agent': 'election-research'}), timeout=60) as r:
                out = json.loads(r.read())
            time.sleep(3.7)                                        # under 1,000 calls an hour
            return out
        except urllib.error.HTTPError as e:
            err = f'HTTP {e.code}'; time.sleep(60 if e.code == 429 else 10 * (i + 1))
        except Exception as e:                                     # noqa: BLE001 - retried, then reported without the address
            err = type(e).__name__; time.sleep(10 * (i + 1))
    print(f'FEC {path}: {err}'); return None


def parts(name):
    n = L.WP.plain(name or '').upper().replace("'", '')
    if ',' in n: last, first = n.split(',', 1)
    else: w = n.split(); first, last = (' '.join(w[:-1]), w[-1]) if w else ('', '')
    last = re.sub(r'\b(JR|SR|II|III|IV)\b\.?', '', last).strip().split()[-1] if last.strip() else ''
    return last, (first.strip()[:1] if first.strip() else '')


def find(name, state, party):
    last, ini = parts(name)
    if not last: return None
    j = get('/candidates/search/', q=last, state=state, office='S', per_page=50)
    hits = [c for c in (j or {}).get('results', []) if parts(c.get('name'))[0] == last]
    if ini: hits = [c for c in hits if not parts(c.get('name'))[1] or parts(c.get('name'))[1] == ini] or hits
    want = [c for c in hits if FEC_PARTY.get(c.get('party')) == party] or hits
    want.sort(key=lambda c: (L.YEAR in (c.get('election_years') or []), c.get('last_file_date') or ''), reverse=True)
    return want[0]['candidate_id'] if want else None


def totals(cid):
    j = get(f'/candidate/{cid}/totals/', cycle=L.YEAR, election_full='true', per_page=1)
    r = (j or {}).get('results') or []
    if not r: return None
    r = r[0]; pick = lambda *ks: next((r[k] for k in ks if r.get(k) is not None), None)
    return {'raised': pick('receipts'), 'cash': pick('last_cash_on_hand_end_period', 'cash_on_hand_end_period'), 'through': (pick('coverage_end_date', 'last_report_date') or '')[:10] or None}


def main():
    if not KEY: print('FEC_API_KEY is not set'); sys.exit(1)
    today = pd.Timestamp(os.environ.get('SENATE_TODAY') or pd.Timestamp.now(tz='America/New_York').date()); L.setup(today)
    pages, seats = L.gather(today)
    people = []
    for s in seats:
        text = pages.get(L.race_title(s['state'], s['special']), {}).get('text', '')
        dem, rep, _ = L.ballot(text, s['state'], s, today) if text else (None, None, None)
        for nm, pt in ([(s['incumbent'], s['incumbent_party'])] if s['incumbent'] else []) + [(x['name'], x['party']) for x in s['declared']] + [(dem, 'D'), (rep, 'R')]:
            if nm and (s['state'], nm) not in {(p[0], p[1]) for p in people}: people.append((s['state'], nm, pt or ''))
    idp = os.path.join(L.OUT, 'fec_ids.json'); ids = json.load(open(idp)) if os.path.exists(idp) else {}
    out = {}
    for st, nm, pt in people:
        k = f'{st}|{nm}'
        if k not in ids: ids[k] = find(nm, st, pt)
        if ids[k]:
            t = totals(ids[k])
            if t: out[k] = {'name': nm, 'party': pt, 'fec_id': ids[k], **t}
    os.makedirs(L.OUT, exist_ok=True)
    json.dump(dict(sorted(ids.items())), open(idp, 'w'), indent=1)
    json.dump({'as_of': str(today.date()), 'year': L.YEAR, 'note': 'FEC totals for this election: receipts, and cash at the latest report. Shown on the Senate tab; not part of the forecast.',
               'candidates': dict(sorted(out.items()))}, open(os.path.join(L.OUT, 'money.json'), 'w'), indent=1)
    print(f'{len(people)} candidates, {sum(1 for v in ids.values() if v)} found at the FEC, {len(out)} with totals, {calls[0]} calls')


if __name__ == '__main__':
    main()
