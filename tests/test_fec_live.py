"""The FEC money job (senate/fec_live.py) against a made-up FEC: totals read and saved; a candidate not found looked for
again on the next run; one whose totals cannot be read keeping the last ones; and an FEC that cannot be reached
stopping the run with the totals in place untouched. No call leaves the machine.
    python tests/test_fec_live.py
"""
import io, json, os, sys, tempfile, urllib.error, urllib.parse
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, os.path.join(ROOT, 'senate')); sys.path.insert(0, ROOT)
import fec_live as FL

SEATS = [{'state': 'GA', 'special': False, 'incumbent': 'Jon Ossoff', 'incumbent_party': 'D', 'declared': []},
         {'state': 'NC', 'special': False, 'incumbent': 'Thom Tillis', 'incumbent_party': 'R', 'declared': [{'name': 'New Person', 'party': 'D'}]}]
FEC = {'OSSOFF': {'candidate_id': 'S8GA00180', 'name': 'OSSOFF, T. JONATHAN', 'party': 'DEM'},
       'TILLIS': {'candidate_id': 'S4NC00162', 'name': 'TILLIS, THOM R. SEN.', 'party': 'REP'}}
TOTALS = {'S8GA00180': 25_000_000, 'S4NC00162': 9_000_000}
state = {'down': False, 'broken': set(), 'registered': set()}


class Resp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): self.close()


def fake_urlopen(req, timeout=None):
    if state['down']: raise urllib.error.URLError('down')
    u = urllib.parse.urlparse(req.full_url); q = urllib.parse.parse_qs(u.query)
    assert q['api_key'] == ['test-key']
    if u.path.endswith('/candidates/search/'):
        name = q['q'][0]
        hits = [FEC[name]] if name in FEC else ([{'candidate_id': 'S8NC00999', 'name': 'PERSON, NEW', 'party': 'DEM'}] if name == 'PERSON' and 'PERSON' in state['registered'] else [])
        return Resp(json.dumps({'results': hits}).encode())
    cid = u.path.split('/')[-3]
    if cid in state['broken']: raise urllib.error.HTTPError(req.full_url, 500, 'x', {}, None)
    return Resp(json.dumps({'results': [{'receipts': TOTALS.get(cid, 1000), 'last_cash_on_hand_end_period': 5, 'coverage_end_date': '2027-03-31T00:00:00'}]}).encode())


def run():
    FL.calls[0] = 0; FL.tally.update(ok=0, failed=0, in_a_row=0)
    FL.main()
    return json.load(open(os.path.join(FL.L.OUT, 'money.json'))), json.load(open(os.path.join(FL.L.OUT, 'fec_ids.json')))


def main():
    bad = []; check = lambda ok, msg: ok or bad.append(msg)
    os.environ['SENATE_TEST_DIR'] = tempfile.mkdtemp(); os.environ['SENATE_TODAY'] = '2027-06-01'   # never the real files
    FL.KEY = 'test-key'; FL.urllib.request.urlopen = fake_urlopen; FL.time.sleep = lambda s: None
    FL.L.gather = lambda today: ({}, SEATS)
    m, ids = run()
    check(set(m['candidates']) == {'GA|Jon Ossoff', 'NC|Thom Tillis'} and m['candidates']['GA|Jon Ossoff']['raised'] == 25_000_000 and ids['NC|New Person'] is None, f'first run: {m["candidates"].keys()}, {ids}')
    state['registered'].add('PERSON')
    m, ids = run()
    check(ids['NC|New Person'] == 'S8NC00999' and 'NC|New Person' in m['candidates'], f'a candidate not found is looked for again: {ids}')
    TOTALS['S8GA00180'] = 30_000_000; state['broken'].add('S4NC00162')
    m, ids = run()
    check(m['candidates']['GA|Jon Ossoff']['raised'] == 30_000_000 and m['candidates']['NC|Thom Tillis']['raised'] == 9_000_000, f'totals that cannot be read keep the last ones: {m["candidates"]}')
    before = open(os.path.join(FL.L.OUT, 'money.json')).read()
    state['down'] = True
    try:
        run(); check(False, 'an FEC that cannot be reached must stop the run')
    except RuntimeError as e:
        check('could not be reached' in str(e) and 'test-key' not in str(e), f'the stop names the problem and not the key: {e}')
    check(open(os.path.join(FL.L.OUT, 'money.json')).read() == before, 'the totals in place are untouched when the FEC cannot be reached')
    print('FAIL: ' + '; '.join(bad) if bad else 'OK: the FEC money job'); sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
