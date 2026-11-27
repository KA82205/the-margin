"""The Senate jobs' health files (senate/health.py): a run that worked, a failure after it (the error kept, the day it
began failing kept through later failures), a run that ended well but did not add a due election, a run that never
started, the FEC key masked however it appears, a file left alone when nothing changed, and when the hourly job starts
the daily and weekly ones.
    python tests/test_senate_health.py
"""
import json, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, os.path.join(ROOT, 'senate'))
import health as HL
TMP = tempfile.mkdtemp()

KEY = 'Zq8TfakeKEYfakeKEYfakeKEYfakeKEYfake1234'


def log(text):
    p = os.path.join(TMP, 'run.log')
    with open(p, 'w') as f: f.write(text)
    return p


def main():
    bad = []; check = lambda ok, msg: ok or bad.append(msg)
    HL.OUT = TMP                                                   # never the real files
    os.environ['SENATE_TODAY'] = '2027-03-01'
    a = HL.record('senate-forecast', 'success', log('{"as_of": "2027-03-01"}\n'))
    check(a['ok'] and a['last_run'] == a['last_success'] == '2027-03-01' and a['overdue_after'] == '2027-03-02' and a['error'] is None, f'a run that worked: {a}')
    t0 = os.path.getmtime(HL.path('senate-forecast'))
    b = HL.record('senate-forecast', 'success', log('again\n'))
    check(b == a and os.path.getmtime(HL.path('senate-forecast')) == t0, 'the same day, the same health: the file is left alone')

    os.environ['SENATE_TODAY'] = '2027-03-02'
    tb = ('Traceback (most recent call last):\n  File "senate/live.py", line 313, in validate\n'
          "    raise RuntimeError('What was read does not look right, so the last forecast stays: ' + '; '.join(bad))\n"
          'RuntimeError: What was read does not look right, so the last forecast stays: 29 seats up\n')
    c = HL.record('senate-forecast', 'failure', log(tb))
    check(not c['ok'] and c['last_success'] == '2027-03-01' and c['overdue_after'] == '2027-03-02' and c['failing_since'] == '2027-03-02'
          and c['error'] == 'RuntimeError: What was read does not look right, so the last forecast stays: 29 seats up', f'a failure: {c}')
    os.environ['SENATE_TODAY'] = '2027-03-03'
    d = HL.record('senate-forecast', 'failure', log('RuntimeError: Wikipedia could not be read: HTTPError\n'))
    check(d['failing_since'] == '2027-03-02' and d['error'] == 'RuntimeError: Wikipedia could not be read: HTTPError' and d['last_run'] == '2027-03-03', f'a second failure keeps the day it began: {d}')
    e = HL.record('senate-forecast', 'success', log('ok\n'))
    check(e['ok'] and e['failing_since'] is None and e['error'] is None and e['last_success'] == '2027-03-03', f'working again: {e}')

    f = HL.record('senate-after', 'success', log('2028: not added yet (results for 20 of 35 races); the next run tries again.\n'))
    check(not f['ok'] and 'not added yet' in f['error'] and f['last_success'] is None and f['overdue_after'] is None, f'a due election not added is a failure: {f}')
    g = HL.record('senate-after', 'success', log('No election to add: the last one is in the training table, or its results have not settled yet.\n'))
    check(g['ok'] and g['overdue_after'] == '2027-03-11', f'nothing due is working: {g}')
    h = HL.record('senate-money', 'skipped', None)
    check(not h['ok'] and 'never started' in h['error'], f'a run that never started: {h}')

    os.environ['FEC_API_KEY'] = KEY
    m = HL.record('senate-money', 'failure', log(f'urllib.error.HTTPError: HTTP Error 403 for https://api.open.fec.gov/v1/x/?q=A&api_key={KEY}&per_page=5\n'))
    check(KEY not in m['error'] and 'api_key=***' in m['error'], f'the key masked in an address: {m["error"]}')
    os.environ['FEC_API_KEY'] = ''
    n = HL.record('senate-money', 'failure', log(f'RuntimeError: bad key {KEY}\n'))
    check(KEY not in n['error'], f'a long token masked even without the key at hand: {n["error"]}')
    with open(HL.path('senate-money')) as fh: saved = fh.read()
    check(KEY not in saved, 'the key is in no saved file')

    os.remove(HL.path('senate-money'))
    check(HL.due('senate-money'), 'no record yet: the money job is due')
    HL.record('senate-money', 'success', log('36 candidates\n'))
    check(not HL.due('senate-money'), 'the money job ran today: not due')
    os.environ['SENATE_TODAY'] = '2027-03-04'
    check(HL.due('senate-money'), 'the money job ran yesterday: due')
    check(not HL.due('senate-after'), 'the after-election job ran yesterday: not due')
    os.environ['SENATE_TODAY'] = '2027-03-10'
    check(HL.due('senate-after'), 'the after-election job ran a week ago: due')
    for job in HL.JOBS:
        with open(HL.path(job)) as fh: j = json.load(fh)
        check(j['workflow'].endswith(HL.JOBS[job][1]) and j['how_to_read'], f'{job}: names its workflow and says how to read it')
    print('FAIL: ' + '; '.join(bad) if bad else 'OK: the Senate jobs\' health files'); sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
