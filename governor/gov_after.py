"""After each year's governor elections, on their own: the races become training data and the model is refitted, so the
next forecast learns from the last races. Run every week by .github/workflows/governor-after.yml; it does nothing until a
year's results have settled (seven weeks after election day, past runoffs and the states' certification) and Wikipedia
has every race's result, and nothing again once that year is in the training table.

For the year just held, from Wikipedia (CC BY-SA 4.0): the overview's table of the races (the governor who held each
seat, their party, what became of the seat, the candidates, their shares and the winner); each race's page and the
polling pages it points to, for the polls of the two nominees, averaged at each distance from election day
(gov_polls.py). Each race becomes a row of data/governor/training.csv as gov_data.py makes them; then gov_fit.py refits
the model. Before writing anything it checks that every race has a winner and, where both parties ran, a share for each.

    python governor/gov_after.py                       the years due and not yet in the table
    python governor/gov_after.py --year 2026           that year, again if it is already in (its rows are replaced)
    python governor/gov_after.py --year 2026 --pages FILE --test [--save]
                                                       reads saved pages (tools/fetch_governor_pages.py) and forecasts that
                                                       year from the years before it, scored on its results; writes
                                                       nothing but, with --save, the test and the year's poll averages
"""
import json, os, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import gov_data as GD, gov_polls as GP, gov_simulate as S, wiki_governor as WG

D = os.path.join(ROOT, 'data', 'governor')
WAIT_DAYS = 49


def election_day(y):
    d = pd.Timestamp(f'{y}-11-01'); return d + pd.Timedelta(days=(7 - d.weekday()) % 7 + 1)


def gather(year, saved=None):
    """The overview, then each race's page and the polling pages they point to."""
    if saved:
        P = json.load(open(saved)); get = lambda ts: {t: P[t] for t in ts if t in P}
    else:
        import wiki_house as WH
        get = WH.fetch
    pages = get([WG.overview(year)])
    if WG.overview(year) not in pages: raise RuntimeError(f'The page "{WG.overview(year)}" could not be read')
    R = WG.races(pages[WG.overview(year)]['text'], year)
    pages.update(get([WG.race_title(year, r['state']) for r in R if WG.race_title(year, r['state']) not in pages]))
    links = sorted({l for r in R for l in GP.poll_links(pages.get(WG.race_title(year, r['state']), {}).get('text', ''), year)} - set(pages))
    if links: pages.update(get(links))
    return pages, R


def rows(year, R):
    """Each race in the training table's columns, from the overview's account and the candidates' shares."""
    lean = GD.leans(); nf = S.votes()
    out = []
    for r in R:
        gen = [c for c in r['candidates'] if c['round'] == 'general']; run = [c for c in r['candidates'] if c['round'] == 'runoff']
        share = lambda p: sum(c['share'] for c in gen if c['party'] == p and c['share'] is not None) if any(c['party'] == p and c['share'] is not None for c in gen) else None
        ds, rs = share('D'), share('R')
        has_d, has_r = any(c['party'] == 'D' for c in gen), any(c['party'] == 'R' for c in gen)
        won = [c['party'] for c in (run or gen) if c['won']]
        dn = next((c['name'] for c in gen if c['party'] == 'D'), None); rn = next((c['name'] for c in gen if c['party'] == 'R'), None)
        on = bool(r['governor']) and any(c['party'] == r['party'] and WG.same_person(r['governor'], c['name']) for c in gen)
        out.append({'year': year, 'state': r['state'], 'special': r['special'], 'dem': np.nan, 'rep': np.nan,
                    'dem2': round(100 * ds / (ds + rs), 3) if has_d and has_r and ds is not None and rs is not None and ds + rs > 0 else np.nan,
                    'contested': has_d and has_r, 'winner': won[0] if won else None, 'lean': lean(year, r['state']),
                    'inc_d': int(on and r['party'] == 'D'), 'inc_r': int(on and r['party'] == 'R'), 'vote': nf.get(year, np.nan),
                    'governor': r['governor'], 'governor_party': r['party'], 'status': r['status'], 'dem_candidate': dn, 'rep_candidate': rn})
    return pd.DataFrame(out)


def check(R, X):
    bad = []
    if len(X) == 0: bad.append('no race read')
    if X.winner.isna().any(): bad.append('no winner yet in ' + ', '.join(X.state[X.winner.isna()]))
    c = X[X.contested]
    if c.dem2.isna().any(): bad.append('no shares yet in ' + ', '.join(c.state[c.dem2.isna()]))
    if X.lean.isna().any(): bad.append('no lean for ' + ', '.join(X.state[X.lean.isna()]))
    return bad


def year_polls(year, pages, X):
    """The year's race polls of the two nominees, averaged at each distance, into data/governor/polls_by_date.csv."""
    nominees = {r.state: (r.dem_candidate, r.rep_candidate) for r in X.itertuples() if r.dem_candidate and r.rep_candidate}
    titles = {st: [WG.race_title(year, st)] + GP.poll_links(pages.get(WG.race_title(year, st), {}).get('text', ''), year) for st in nominees}
    P = GP.from_pages(pages, year, nominees, titles)
    A = GP.averages(P, year) if len(P) else pd.DataFrame(columns=['year', 'state', 'days', 'poll', 'poll_w', 'polls'])
    p = os.path.join(D, 'polls_by_date.csv'); old = pd.read_csv(p) if os.path.exists(p) else A.iloc[:0]
    pd.concat([old[old.year != year], A], ignore_index=True).sort_values(['year', 'state', 'days'], ascending=[True, True, False]).to_csv(p, index=False)
    print(f'{year}: {len(P)} race polls ({int((P.partisan.fillna("") == "").sum()) if len(P) else 0} not partisan) in {A.state.nunique() if len(A) else 0} races')
    return A


def test(year, X):
    """The year forecast from the even years before it, none of it fitted on the year, at each distance."""
    import gov_fit
    T = S.load(); X = X.copy(); X['usable'] = X.contested & X.lean.notna() & X.dem2.notna()
    T2 = pd.concat([T[T.year != year], X], ignore_index=True, sort=False)
    R, races = S.run(polls=True, T0=T2, tests=[year], fit_years=[y for y in gov_fit.years_fitted(T) if y < year])
    return R, races


def save_test(year, X, R, races):
    bp = os.path.join(D, 'backtest.json'); B = json.load(open(bp)) if os.path.exists(bp) else {}
    import gov_fit
    B.setdefault('tests', {})[str(year)] = {
        'note': f'{year} forecast from the elections before it ({", ".join(str(y) for y in gov_fit.years_fitted(S.load()) if y < year)}), none of it fitted on {year}',
        'read': str(pd.Timestamp.now(tz='America/New_York').date()), 'dem_won': int((X.winner == 'D').sum()), 'rep_won': int((X.winner == 'R').sum()), 'races_n': int(len(X)),
        'rows': R[['days', 'races', 'called', 'avg_miss', 'brier', 'dem_won_mean', 'dem_won_low', 'dem_won_high', 'dem_won', 'inside']].round(4).to_dict('records'),
        'races': gov_fit.records(races[races.days.isin([365, 120, 60, 14, 1])])}
    with open(bp, 'w') as f: json.dump(B, f, indent=1)
    print('saved the test of', year, 'to', bp)


def due(today, T):
    have = set(T.year)
    return [y for y in range(2026, today.year + 1) if y not in have and today >= election_day(y) + pd.Timedelta(days=WAIT_DAYS)]


def add(year, saved=None):
    tp = os.path.join(D, 'training.csv'); T = pd.read_csv(tp)
    pages, R = gather(year, saved)
    X = rows(year, R)
    bad = check(R, X)
    if bad:
        print(f'{year}: not added yet: ' + '; '.join(bad)); return False
    pd.concat([T[T.year != year], X], ignore_index=True).sort_values(['year', 'state', 'special']).to_csv(tp, index=False)
    year_polls(year, pages, X)
    print(f'{year}: {len(X)} races added; won', X.winner.value_counts().to_dict())
    import gov_fit
    gov_fit.main()
    return True


def main(argv):
    a = argv[1:]
    year = int(a[a.index('--year') + 1]) if '--year' in a else None
    saved = a[a.index('--pages') + 1] if '--pages' in a else None
    if '--test' in a:
        pages, R = gather(year, saved); X = rows(year, R)
        print('checks:', check(R, X) or 'all pass', '| races', len(X), '| won', X.winner.value_counts().to_dict(), '| governors on the ballot: D', int(X.inc_d.sum()), 'R', int(X.inc_r.sum()))
        if '--save' in a: year_polls(year, pages, X)
        Rt, races = test(year, X)
        print(Rt[['year', 'days', 'races', 'called', 'avg_miss', 'brier', 'dem_won_mean', 'dem_won', 'dem_won_low', 'dem_won_high']].round(3).to_string(index=False))
        if '--save' in a: save_test(year, X, Rt, races)
        return Rt
    today = pd.Timestamp(os.environ.get('GOVERNOR_TODAY') or pd.Timestamp.now(tz='America/New_York').date())
    T = pd.read_csv(os.path.join(D, 'training.csv'))
    years = [year] if year else due(today, T)
    if not years: print('No governor election is due to be added.'); return
    for y in years: add(y, saved)


if __name__ == '__main__':
    main(sys.argv)
