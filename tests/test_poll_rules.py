"""The rules a poll is counted or set aside by, on made-up polls of the kinds 2027 and 2028 will bring: new names, the
nominees chosen, people who cannot run written in other ways, several reasons at once, and things the feed gets wrong.

    python tests/test_poll_rules.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import polls as P

HOME = {'josh shapiro': 'PA', 'gavin newsom': 'CA', 'jd vance': 'OH', 'gretchen whitmer': 'MI'}


def row(dem='Gavin Newsom', rep='JD Vance', place='MI', end='2028-09-20', d=46.0, r=44.0, partisan='', internal=False, n_dem=1, n_rep=1):
    return {'place': place, 'place_read_from': 'state', 'end': end, 'n_dem': n_dem, 'n_rep': n_rep, 'dem': dem, 'rep': rep, 'partisan': partisan, 'internal': internal, 'dem_pct': d, 'rep_pct': r}


def check(name, r, want, nominees=None):
    got = P.reasons(r, HOME, nominees)
    ok = got == want if isinstance(want, list) else (bool(got) == (not want))
    if not ok: raise SystemExit(f'FAIL {name}: {got!r}, wanted {want!r}')
    u = P.usable(r, HOME, nominees)
    if u[0] != (not got) or u[1] != (got[0] if got else ''): raise SystemExit(f'FAIL {name}: usable() disagrees with reasons(): {u}')


check('a pairing never seen before, nominees unknown', row('Andy Beshear', 'Glenn Youngkin'), [])
check('a home-state poll, nominees unknown', row('Gretchen Whitmer', 'JD Vance', place='MI'), ["Gretchen Whitmer's own state, while the nominees are not known"])
check('the same poll once both nominees are known', row('Gretchen Whitmer', 'JD Vance', place='MI'), [], nominees=('Gretchen Whitmer', 'JD Vance'))
check('another pairing once the nominees are known', row('Gavin Newsom', 'Marco Rubio'), ['not the two nominees, Gretchen Whitmer and JD Vance'], nominees=('Gretchen Whitmer', 'JD Vance'))
check('a national poll of the nominees', row('Gretchen Whitmer', 'JD Vance', place='US'), [], nominees=('Gretchen Whitmer', 'JD Vance'))
for name in ('Donald Trump', 'Donald J. Trump', 'DONALD JOHN TRUMP', 'Barack H. Obama', 'George W. Bush', 'William Jefferson Clinton'):
    check('cannot run: ' + name, row('Gavin Newsom', name), [f'{name} cannot be elected again'])
check('Donald Trump Jr. is someone else', row('Gavin Newsom', 'Donald Trump Jr.'), [])
check('a generic ballot', row('Generic Democrat', 'Generic Republican'), ['no named candidates (a generic ballot)'])
check('several reasons at once', row('Barack Obama', 'Donald Trump', partisan='REP'), ['Barack Obama cannot be elected again', 'Donald Trump cannot be elected again', 'paid for by a party or a campaign'])
check('a third candidate in the question', row(n_dem=1, n_rep=2), ['not one Democrat against one Republican'])
check('percentages that cannot be', row(d=70, r=45), ['the percentages do not add up'])
check('missing percentages', row(d=None, r=44), ['the percentages do not add up'])
check('few chose either', row(d=22, r=20), ['under half of those asked chose either candidate'])
check('no place and no date', row(place=None, end=None), ['its place could not be read: state', 'no end date'])
check('paid for by a campaign, nominees known', row(internal=True), ['paid for by a party or a campaign', 'not the two nominees, Andy Beshear and JD Vance'], nominees=('Andy Beshear', 'JD Vance'))
assert len(P.RULES) == 9 and all(isinstance(t, str) and t for _, t in P.RULES)
print('ok (the poll rules: new names, nominees chosen, people who cannot run written several ways, several reasons at once, bad figures)')
