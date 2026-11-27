"""Senate back-test, step 8: the national fundamentals (approval, income, midterm) as the race model's national input.
Research only.

For each year and distance, a forecast of the national House vote is made from what was known on that date: the
president's latest approval (Gallup's average over the past 30 days; after Gallup stopped at the end of 2025, the
RealClearPolling average turned into a Gallup equivalent by Quinn, Brush and Smith's proxy), the latest two quarters of
real disposable income growth published by then (revised figures: the first-published ones are not kept here), and
whether it is a midterm. The equation is fitted on 1948 up to the election before, never on the year itself or later.

The race model then takes, in place of the generic ballot alone:

    fund      the fundamentals forecast alone
    blend     the average of the fundamentals forecast and the generic-ballot average, half each (not fitted)

Each is scored leave one year out on 2018-2024, as before, and on 2026 fitted on 2018-2024 only (test_2026.py).

    python senate/national_test.py     writes data/senate/national_test.json
"""
import json, math, os, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import backtest as B, simulate as S, test_2026 as T26

from national import ELECTION, National, add


VERSIONS = {'generic (current)': ['lean', 'generic', 'inc_d', 'inc_r', 'track'],
            'fund': ['lean', 'fund', 'inc_d', 'inc_r', 'track'],
            'blend': ['lean', 'blend', 'inc_d', 'inc_r', 'track'],
            'fund, approval only': ['lean', 'fund_approval', 'inc_d', 'inc_r', 'track'],
            'blend, approval only': ['lean', 'blend_approval', 'inc_d', 'inc_r', 'track']}


def forecast(a, b, cols):
    coef, _ = B.fit(a, cols)
    af = a.assign(f=B.predict(coef, a, cols)); bf = b.assign(f=B.predict(coef, b, cols))
    p = B.volume_fit(af); af['m'] = B.blend(af, p); bf['m'] = B.blend(bf, p)
    return af, bf


def scored(bf, sd):
    p = np.array([B.cdf((m - 50) / s) for m, s in zip(bf.m, sd)]).clip(0.001, 0.999); won = (bf.dem2.values > 50).astype(float)
    err = 2 * (bf.m.values - bf.dem2.values)
    return {'margin_miss': float(np.sqrt(np.mean(err ** 2))), 'bias': float(np.mean(err)), 'called': int(((bf.m.values > 50) == (won == 1)).sum()),
            'log_loss': float(-np.mean(won * np.log(p) + (1 - won) * np.log(1 - p))), 'races': len(bf)}


def main():
    nat = National()
    X = add(B.build(), nat); T = add(T26.features(T26.races()), nat)
    rows = []
    for name, cols in VERSIONS.items():
        for d in B.DAYS:
            for y in list(B.YEARS) + [2026]:
                if y == 2026: a, b = X[X.days == d], T[T.days == d]
                else: a, b = X[(X.year != y) & (X.days == d)], X[(X.year == y) & (X.days == d)]
                af, bf = forecast(a, b, cols)
                e = af.m.values - af.dem2.values; hp = af.poll.notna().values
                sp, sn = float(np.sqrt(np.mean(e[hp] ** 2))), float(np.sqrt(np.mean(e[~hp] ** 2)))
                sd = np.where(bf.poll.notna().values, sp, sn)
                rows.append({'version': name, 'days': d, 'year': y, **scored(bf, sd)})
    R = pd.DataFrame(rows)
    pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
    loyo = R[R.year < 2026].groupby(['version', 'days']).apply(lambda x: pd.Series({
        'margin_miss': float(np.sqrt(np.average(x.margin_miss ** 2, weights=x.races))), 'log_loss': float(np.average(x.log_loss, weights=x.races)),
        'called': int(x.called.sum())}), include_groups=False).reset_index()
    y26 = R[R.year == 2026][['version', 'days', 'margin_miss', 'bias', 'log_loss', 'called']]
    allf = R.groupby(['version', 'days']).apply(lambda x: pd.Series({
        'margin_miss': float(np.sqrt(np.average(x.margin_miss ** 2, weights=x.races))), 'log_loss': float(np.average(x.log_loss, weights=x.races)),
        'called': int(x.called.sum())}), include_groups=False).reset_index()
    for title, Z in (('2018-2024, leave one year out', loyo), ('2026, fitted on 2018-2024', y26), ('all five years', allf)):
        print(title)
        for m in ('margin_miss', 'log_loss', 'called') + (('bias',) if 'bias' in Z else ()):
            print(m); print(Z.pivot(index='days', columns='version', values=m).round(3).sort_index(ascending=False))
    natl = pd.DataFrame([{'year': y, 'days': d, 'fund': round(nat.forecast(y, d), 2), 'fund_approval': round(nat.forecast(y, d, income=False), 2)} for y in ELECTION for d in B.DAYS])
    natl['generic'] = [pd.concat([X, T]).query('year == @y and days == @d').generic.iloc[0] for y, d in zip(natl.year, natl.days)]
    natl['actual_house_vote'] = [float(nat.N.house_vote_dem[y]) for y in natl.year]
    with open(os.path.join(ROOT, 'data', 'senate', 'national_test.json'), 'w') as f:
        json.dump({'note': 'Senate race model with the national fundamentals as its national input; margins in points, Democratic side minus Republican.',
                   'loyo_2018_2024': loyo.round(4).to_dict('records'), 'test_2026': y26.round(4).to_dict('records'), 'all_five': allf.round(4).to_dict('records'),
                   'by_year': R.round(4).to_dict('records'), 'national': natl.round(3).to_dict('records')}, f, indent=1)
    return R, natl


if __name__ == '__main__':
    main()
