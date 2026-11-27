"""The after-election readers (senate/after_election.py) on made-up Wikipedia pages in each layout they meet: a race with
a runoff (Georgia's box: a first round and a runoff), a page with a regular and a special election in one box
(California's), two Democrats in the general (a top-two primary), an independent against a Republican, a plain race;
a presidential results table; the House's national vote; the Senate's seats before and after; and the scoring of a new
year's candidates' records. The full path was also run on 2026 as if it had just been held (senate/README.md).
    python tests/test_after_election.py
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, os.path.join(ROOT, 'senate')); sys.path.insert(0, ROOT)
import pandas as pd
import after_election as AE


def box(fields):
    return '{{Infobox election\n| election_name = x\n' + ''.join(f'| {k} = {v}\n' for k, v in fields) + '}}\nText.'


RUNOFF = box([('candidate1', "'''[[Raphael Warnock]]'''"), ('party1', 'Democratic Party (United States)'), ('1data1', '1,946,117<br />49.44%'), ('2data1', "'''1,820,633<br />51.40%'''"),
              ('candidate2', '[[Herschel Walker]]'), ('party2', 'Republican Party (United States)'), ('1data2', '1,908,442<br />48.49%'), ('2data2', '1,721,244<br />48.60%'),
              ('1blank', 'First round'), ('2blank', '[[Two-round system|Runoff]]'), ('before_election', '[[Raphael Warnock]]'), ('before_party', 'Democratic Party (United States)')])
TWO = box([('candidate1', "'''[[Alex Padilla]]'''"), ('party1', 'Democratic Party (United States)'), ('candidate2', 'Mark Meuser'), ('party2', 'Republican Party (United States)'),
           ('1blank', 'Regular election'), ('2blank', 'Special election'), ('1data1', '6,621,621<br />61.06%'), ('1data2', '4,222,029<br />38.94%'), ('2data1', '6,559,308<br />60.89%'), ('2data2', '4,212,450<br />39.11%'),
           ('before_election', '[[Alex Padilla]]'), ('before_party', 'Democratic Party (United States)')])
DD = box([('nominee1', '[[Ro Khanna]]'), ('party1', 'Democratic Party (United States)'), ('popular_vote1', '6,000,000'), ('nominee2', '[[Katie Porter]]'), ('party2', 'Democratic Party (United States)'), ('popular_vote2', '5,000,000')])
IND = box([('nominee1', '[[Pete Ricketts]]'), ('party1', 'Republican Party (United States)'), ('popular_vote1', '520,000'), ('nominee2', '[[Dan Osborn]]'), ('party2', 'Independent politician'), ('popular_vote2', '480,000'),
           ('before_election', '[[Pete Ricketts]]'), ('before_party', 'Republican Party (United States)')])
PLAIN = box([('nominee1', '[[Jon Ossoff]]'), ('party1', 'Democratic Party (United States)'), ('popular_vote1', '2,600,000'), ('nominee2', '[[Mike Collins]]'), ('party2', 'Republican Party (United States)'), ('popular_vote2', '2,400,000'),
             ('nominee3', 'Someone Else'), ('party3', 'Libertarian Party (United States)'), ('popular_vote3', '50,000')])
STATES = ''.join(f'|-\n| [[2028 United States presidential election in {n}|{n}]]\n| {r:,}\n| 50%\n| 9\n| {d:,}\n| 45%\n| –\n'
                 for n, r, d in [(s, 1000 + 10 * i, 900 + 15 * i) for i, s in enumerate(list(AE.W28.ABBR)[:50])]) + '|-\n| D.C.\n| 100\n| 10%\n| –\n| 900\n| 90%\n| 3\n'
PRES = ('==Results==\n===Results by state===\n{| class="wikitable"\n! rowspan=2 | State\n! colspan="3" | Vance/Rubio<br />Republican\n! colspan="3" | Buttigieg/Shapiro<br />Democratic\n|-\n! Votes\n! %\n! EV\n! Votes\n! %\n! EV\n'
        + STATES + '|-\n| Total\n| 1\n| 1%\n| 1\n| 1\n| 1%\n| 1\n|}\n')
HOUSE = '{{Infobox legislative election\n| party1 = Democratic Party (United States)\n| popular_vote1 = 67,070,205 {{cite web|url=x}}\n| party2 = Republican Party (United States)\n| popular_vote2 = 50,250,343\n}}'
SENATE = ('{{Infobox election\n| party1 = Democratic Party (United States)\n| seats_before1 = 45{{efn|x}}\n| seats_after1 = 54<!-- note -->\n| party2 = Republican Party (United States)\n| seats_before2 = 53\n| seats_after2 = 44\n'
          '| party4 = Independent politician\n| seats_before4 = 2\n| seats_after4 = 2\n}}')


def main():
    bad = []; check = lambda ok, msg: ok or bad.append(msg)
    r = AE.result(RUNOFF, 'GA', False)
    check(r['dr'] and abs(r['dem2'] - 100 * 1820633 / (1820633 + 1721244)) < 1e-6 and abs(r['dem2_first'] - 100 * 1946117 / (1946117 + 1908442)) < 1e-6 and r['won'] == 'D', f'runoff: {r}')
    reg, spc = AE.result(TWO, 'CA', False), AE.result(TWO, 'CA', True)
    check(abs(reg['dem2'] - 100 * 6621621 / (6621621 + 4222029)) < 1e-6 and abs(spc['dem2'] - 100 * 6559308 / (6559308 + 4212450)) < 1e-6, f'regular and special: {reg["dem2"]}, {spc["dem2"]}')
    dd = AE.result(DD, 'CA', False)
    check(not dd['dr'] and dd['won'] == 'D', f'two Democrats: left out of the table, won by the Democratic side: {dd}')
    ind = AE.result(IND, 'NE', False)
    check(ind['dr'] and ind['dem'] == 'Dan Osborn' and ind['dem_party'] == 'I' and abs(ind['dem2'] - 48.0) < 1e-6 and ind['won'] == 'R', f'independent against a Republican: {ind}')
    pl = AE.result(PLAIN, 'GA', False)
    check(pl['dr'] and abs(pl['dem2'] - 52.0) < 1e-6, f'a plain race: {pl}')
    st, nat = AE.pres_results(PRES)
    check(st is not None and len(st) == 51 and abs(st['DC'] - 90.0) < 1e-6 and abs(st['AL'] - 100 * 900 / 1900) < 1e-6, f'presidential results: {None if st is None else len(st)} places')
    tot_d = sum(900 + 15 * i for i in range(50)) + 900; tot_r = sum(1000 + 10 * i for i in range(50)) + 100
    check(nat is not None and abs(nat - 100 * tot_d / (tot_d + tot_r)) < 1e-6, f'the nation summed from the states: {nat}')
    check(abs(AE.house_vote(HOUSE) - 100 * 67070205 / (67070205 + 50250343)) < 1e-6, 'the House vote')
    s = AE.senate_seats(SENATE)
    check(s['D'] == (45, 54) and s['R'] == (53, 44) and s['I'] == (2, 2), f'the Senate seats: {s}')
    new = pd.DataFrame([{'year': 2028, 'state': 'NM', 'special': False, 'dem': 'BEN RAY LUJAN', 'rep': 'SOMEONE NEW', 'dem2': 58.0, 'lean': 4.0},
                        {'year': 2028, 'state': 'GA', 'special': False, 'dem': 'NEW PERSON', 'rep': 'OTHER PERSON', 'dem2': 51.0, 'lean': -1.0}])
    sc = AE.score_past(new)
    check(abs(sc.dem_over.sum()) < 1e-3, 'a year\'s records add to zero, as past_races scores them')
    fit = __import__('json').load(open(os.path.join(ROOT, 'data', 'senate', 'past_races_fit.json')))
    x0 = 58.0 - fit['lean'] * 4.0 - fit['dem_had_won']; x1 = 51.0 - fit['lean'] * -1.0
    check(abs(sc.dem_over.iloc[0] - round(x0 - (x0 + x1) / 2, 3)) < 1e-3, 'Lujan, who won New Mexico in 2020, counts as having won the state before')
    print('FAIL: ' + '; '.join(bad) if bad else 'OK: the after-election readers read each layout'); sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
