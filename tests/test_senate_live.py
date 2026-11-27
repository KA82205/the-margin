"""The live Senate forecast meets each case on its own (senate/live.py), on made-up Wikipedia pages: a senator who has not
said, one running again, one running for governor, a primary lost, a seat left vacant, two nominees of one party, an
independent standing against a Republican, a side with no candidate by September, both nominees chosen with their polls
(one paid for by a campaign), a table outside the race summary, and pages that do not look right.
    python tests/test_senate_live.py
"""
import json, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, os.path.join(ROOT, 'senate')); sys.path.insert(0, ROOT)

FILLER = ['Alabama', 'Arkansas', 'Connecticut', 'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana', 'Maryland',
          'Missouri', 'Nevada', 'New Hampshire', 'New York', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon', 'Pennsylvania', 'South Carolina',
          'South Dakota', 'Utah', 'Vermont', 'Washington', 'Wisconsin']
PARTY = {'Alabama': 'R', 'Arkansas': 'R', 'Idaho': 'R', 'Indiana': 'R', 'Iowa': 'R', 'Kansas': 'R', 'Kentucky': 'R', 'Louisiana': 'R', 'Missouri': 'R',
         'North Dakota': 'R', 'Oklahoma': 'R', 'South Carolina': 'R', 'South Dakota': 'R', 'Utah': 'R', 'Wisconsin': 'R'}
NAME = {'D': 'Democratic', 'R': 'Republican'}


def row(state, first, last, party, status, cands='*TBD', special=False):
    link = f'[[2028 United States Senate {"special election" if special else "election"} in {state}|{state}]]'
    sen = f'{{{{Sortname|{first}|{last}}}}}' if first else 'To be appointed'
    return (f'|-\n! {link}\n| {sen}\n| {{{{Party shading/{NAME[party]}}}}} | {NAME[party]}\n| data-sort-value=2022 | 2022\n'
            f'| {{{{Party shading/{NAME[party]}}}}} data-sort-value=1 | 1% X\n| data-sort-value=0 | {status}\n| nowrap | {{{{Plainlist|\n{cands}\n}}}}\n')


def overview(extra_seat=True, broken=False):
    head = ('{{Infobox election\n| election_name = 2028 United States Senate elections\n| party1 = Democratic Party (United States)\n| seats_before1 = 54\n'
            '| party2 = Republican Party (United States)\n| seats_before2 = 44\n| party3 = Independent politician\n| seats_before3 = 2\n}}\n'
            'Intro.\n\n==Race summary==\n=== Special elections during the preceding Congress ===\n{| class="wikitable"\n! State\n')
    special = row('Tennessee', None, None, 'R', "Interim appointee's intent unknown", '*{{Party stripe|Republican Party (US)}}[[Tim Burchett]] (Republican)', True) + '|}\n'
    rows = [row('Georgia', 'Raphael', 'Warnock', 'D', "Incumbent's intent unknown"), row('North Carolina', 'Ted', 'Budd', 'R', 'Incumbent running.'),
            row('Colorado', 'Michael', 'Bennet', 'D', 'Incumbent running for Governor of Colorado.'), row('California', 'Alex', 'Padilla', 'D', 'Incumbent running.'),
            row('Nebraska', 'Pete', 'Ricketts', 'R', 'Incumbent running.'), row('Florida', 'Ashley', 'Moody', 'R', 'Incumbent running.'),
            row('Alaska', 'Lisa', 'Murkowski', 'R', 'Incumbent running.', '*{{Party stripe|Republican Party (US)}}[[Lisa Murkowski]] (Republican)'),
            row('Arizona', 'Mark', 'Kelly', 'D', 'Incumbent retiring.')]
    rows += [row(s, 'Pat', s.split()[0] + 'son', PARTY.get(s, 'D'), "Incumbent's intent unknown") for s in (FILLER[:4] if broken else FILLER)]
    body = ('=== Elections leading to the next Congress ===\n{| class="wikitable"\n! State\n' + ''.join(rows) + '|}\n')
    after = '\n== Predictions ==\n{| class="wikitable"\n|-\n! [[2028 United States Senate election in Texas|Texas]]\n| {{Sortname|Some|One}}\n| x | Republican\n| 1\n| 1\n| data-sort-value=0 | Incumbent running.\n| x\n|}\n'
    return head + special + body + after


def race(dem, rep, polls=(), more=()):
    """A race page: the box with its nominees, and a table of general-election polls."""
    noms = [(dem, 'Democratic'), (rep, 'Republican'), *more]
    box = '{{Infobox election\n| election_name = x\n' + ''.join(f'| nominee{i} = [[{n}]]\n| party{i} = {p} Party (United States)\n' for i, (n, p) in enumerate(noms, 1) if n) + '}}\n'
    if not polls: return box + 'Text.'
    t = ('\n==General election==\n===Polling===\n{| class="wikitable"\n! Poll source\n! Date(s) administered\n! Sample size\n! Margin of error\n'
         f'! {dem.split()[0]}<br />{dem.split()[-1]} (D)\n! {rep.split()[0]}<br />{rep.split()[-1]} (R)\n! Undecided\n')
    for src, date, n, d, r in polls: t += f'|-\n| {src}\n| {date}\n| {n} (LV)\n| ± 3.0%\n| {d}%\n| {r}%\n| 5%\n'
    return box + t + '|}\n'


def pages():
    P = json.load(open(os.path.join(HERE, 'fixtures', 'approval_2026-11-27.json')))
    P['2028 United States Senate elections'] = {'title': '2028 United States Senate elections', 'timestamp': '2026-11-27T00:00:00Z', 'text': overview()}
    pg = lambda t, txt: {'title': t, 'timestamp': '2026-11-27T00:00:00Z', 'text': txt}
    T = lambda s: f'2028 United States Senate election in {s}'
    P[T('North Carolina')] = pg(T('North Carolina'), race('Roy Cooper', 'Ted Budd', [('Siena College', 'October 1–4, 2028', 800, 50, 45), ('Elon University', 'September 20–25, 2028', 700, 49, 46),
                                                                                    ('Cooper Campaign (D)', 'September 10–12, 2028', 600, 53, 42)]))
    P[T('California')] = pg(T('California'), race('Alex Padilla', None, more=[('Ro Khanna', 'Democratic')]))
    P[T('Nebraska')] = pg(T('Nebraska'), race(None, 'Pete Ricketts', more=[('Dan Osborn', 'Independent politician')]))
    P[T('Florida')] = pg(T('Florida'), race('Jared Moskowitz', 'Byron Donalds'))
    return P


def run(today, P, d):
    os.environ['SENATE_TODAY'] = today; os.environ['SENATE_TEST_DIR'] = d
    f = os.path.join(d, 'pages.json'); json.dump(P, open(f, 'w'))
    import importlib, live; importlib.reload(live)
    out = live.main(f); return out, {r['state']: r for r in out['races']}, json.load(open(os.path.join(d, 'senate.json')))


def main():
    bad = []; check = lambda ok, msg: ok or bad.append(msg)
    with tempfile.TemporaryDirectory() as d:
        out, R, page = run('2028-10-10', pages(), d)
        check(out['year'] == 2028 and out['chamber_now']['seats_up'] == 36, f"36 seats up in 2028, not {out['chamber_now']['seats_up']}: the table under Predictions must not be read")
        check(out['chamber_now']['dem_caucus'] == 56 and out['chamber_now']['vacant_up'] == ['TN'], f"chamber {out['chamber_now']}")
        check(R['GA']['short'] == 'Has not said' and 0.7 < R['GA']['incumbent_runs'] < 0.85, f"Georgia: {R['GA']['short']} {R['GA']['incumbent_runs']}")
        check(R['CO']['short'] == 'Not running' and R['CO']['incumbent_runs'] == 0, f"Colorado (running for governor): {R['CO']['short']}")
        check(R['AZ']['short'] == 'Not running', f"Arizona (retiring): {R['AZ']['short']}")
        check(R['TN']['short'] == 'Appointee not yet named' and R['TN']['incumbent_runs'] == 0, f"Tennessee: {R['TN']['short']}")
        check(R['CA']['fixed'] == 'D' and R['CA']['p_dem'] == 1 and R['CA']['margin'] is None, f"California, two Democrats: {R['CA']['fixed']} {R['CA']['p_dem']}")
        check(R['NE']['dem'] == 'Dan Osborn' and R['NE']['fixed'] is None, f"Nebraska, an independent against a Republican: {R['NE']['dem']} {R['NE']['fixed']}")
        check(R['FL']['short'] == 'Lost the nomination' and R['FL']['incumbent_runs'] == 0 and R['FL']['dem'] == 'Jared Moskowitz', f"Florida, a primary lost: {R['FL']['short']}")
        check(R['NC']['short'] == 'Nominees chosen' and R['NC']['polls'] == 2 and R['NC']['polls_margin'] is not None, f"North Carolina: {R['NC']['short']}, {R['NC']['polls']} polls counted")
        nc = [p for p in out['polls'] if p['state'] == 'NC']
        check(len(nc) == 3 and sum(p['counted'] for p in nc) == 2 and any(p['why'] == 'Paid for by a party or a campaign' for p in nc), f"North Carolina's listed polls: {[(p['pollster'], p['counted'], p['why']) for p in nc]}")
        check(R['AK']['fixed'] == 'R' and R['AK']['p_dem'] == 0, f"Alaska from September, no Democrat at all: {R['AK']['fixed']}")
        check(page['races'] and page['model'] and 'backtests' in page and page['polls'], 'the page data lacks a part')
        check(abs(sum(out['caucus_distribution'].values()) - 1) < 1e-3, 'the caucus distribution does not add to one')
        out2, R2, _ = run('2027-06-01', pages(), d)
        check(R2['AK']['fixed'] is None, 'Alaska in June 2027: the seat is not decided before September of the election year')
        check(out2['days_out'] > 365 and out2['distance_used'] == 365, 'more than a year out the year-out fit is used')
        P = pages(); P['2028 United States Senate elections']['text'] = overview(broken=True)
        try:
            run('2027-06-01', P, d); bad.append('a page with too few seats was not stopped')
        except RuntimeError as e:
            check('does not look right' in str(e), f'stopped for another reason: {e}')
    print('FAIL: ' + '; '.join(bad) if bad else 'OK: the Senate forecast meets each case on its own'); sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
