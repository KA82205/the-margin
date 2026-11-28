"""Every report of money raised by the House candidates in the training table (data/house/training.csv: both parties'
candidates in each contested race, by their FEC numbers), from the FEC's API, for testing money as it stood on each
date. Run by the samples workflow (script tools/fetch_house_money.py, names: the cycles to fetch, such as "2012 2014");
the API key is read from the FEC_API_KEY secret and never written or printed.

    python tools/fetch_house_money.py <folder> [cycles]   ->  <folder>/house_money/reports_<cycle>.csv

Each report as the FEC holds it now (the latest version of an amended one is marked most_recent): the candidate, the
committee, the dates it covers, the date the FEC received it, and the money raised in the period it covers.
"""
import csv, json, os, sys, time, urllib.error, urllib.parse, urllib.request

KEY = os.environ.get('FEC_API_KEY', '')
API = 'https://api.open.fec.gov/v1'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIELDS = ['candidate_id', 'committee_id', 'cycle', 'report_type', 'coverage_start_date', 'coverage_end_date', 'receipt_date', 'total_receipts_period', 'most_recent', 'is_amended']
BATCH, START = 25, time.time()
calls = [0]


def get(params):
    q = urllib.parse.urlencode(params + [('api_key', KEY)])
    err = None
    for i in range(6):
        try:
            calls[0] += 1
            with urllib.request.urlopen(urllib.request.Request(f'{API}/reports/house-senate/?{q}', headers={'User-Agent': 'election-research'}), timeout=90) as r:
                out = json.loads(r.read())
            time.sleep(3.6)                                        # under 1,000 calls an hour
            return out
        except urllib.error.HTTPError as e:
            err = f'HTTP {e.code}'; time.sleep(60 if e.code == 429 else 10 * (i + 1))
        except Exception as e:                                     # noqa: BLE001 - retried, then reported without the address
            err = type(e).__name__; time.sleep(10 * (i + 1))
    print('a request failed:', err); return None


def main(out, cycles):
    d = os.path.join(out, 'house_money'); os.makedirs(d, exist_ok=True)
    rows = list(csv.DictReader(open(os.path.join(ROOT, 'data', 'house', 'training.csv'))))
    for cycle in cycles:
        ids = sorted({r[k] for r in rows if r['year'] == str(cycle) and r['contested'] == 'True' for k in ('dem_fec', 'rep_fec') if r[k]})
        got, failed = [], 0
        for i in range(0, len(ids), BATCH):
            if time.time() - START > 52 * 60: print('stopped for time at', cycle, i, 'of', len(ids)); break
            batch, page = ids[i:i + BATCH], 1
            while True:
                j = get([('candidate_id', c) for c in batch] + [('cycle', cycle), ('per_page', 100), ('page', page), ('sort', 'coverage_end_date')])
                if j is None: failed += 1; break
                got += [{k: r.get(k) for k in FIELDS} for r in j.get('results', [])]
                if page >= (j.get('pagination') or {}).get('pages', 1): break
                page += 1
        with open(os.path.join(d, f'reports_{cycle}.csv'), 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(got)
        print(cycle, len(ids), 'candidates,', len(got), 'reports,', failed, 'batches failed,', calls[0], 'calls so far')


def links(out):
    """The FEC's candidate-committee links for each cycle (public domain bulk files), since a report names its committee
    and not always its candidate."""
    import io, zipfile
    d = os.path.join(out, 'house_money'); os.makedirs(d, exist_ok=True)
    for y in range(2012, 2028, 2):
        try:
            with urllib.request.urlopen(urllib.request.Request(f'https://www.fec.gov/files/bulk-downloads/{y}/ccl{str(y)[2:]}.zip', headers={'User-Agent': 'election-research'}), timeout=120) as r:
                z = zipfile.ZipFile(io.BytesIO(r.read()))
            open(os.path.join(d, f'ccl{str(y)[2:]}.txt'), 'wb').write(z.read(z.namelist()[0])); print('links', y)
        except Exception as e:                                     # noqa: BLE001
            print('links', y, 'could not be read:', type(e).__name__)


if __name__ == '__main__':
    a = sys.argv[1:]
    if not KEY: print('FEC_API_KEY is not set'); sys.exit(1)
    links(a[0] if a else 'samples')
    main(a[0] if a else 'samples', [int(x) for x in a[1:]] or [2012, 2014, 2016, 2018, 2020, 2022, 2024])
