"""Senate back-test, step 10: combining the race-by-race simulation with a national seat-change model. Research only.

The national model is Quinn, Brush and Smith's Senate equation without income (step 9 found income does not help out of
sample): the president's party's Senate seat change from approval, the midterm and how many of its seats are up, fitted
on 1948 up to the election before. It is applied with the approval known on each date (national.National.approval).

The combination moves every race by one shared amount, so that the simulation's expected Democratic seats land at a
weighted average of its own expectation and the national model's: w = 0 is the race model alone, w = 1 puts the seat
total where the national model puts it, with the races still deciding which seats. The weights tried were set before
scoring: 0, 0.25, 0.5, 0.75 and 1.

Scored on 2018-2024 (each year left out in turn) and 2026 (fitted on 2018-2024): the Democratic caucus after the
election (seats), the chance of control, and each race's margin and chance.

    python senate/combine_test.py      writes data/senate/combine_test.json
"""
import json, math, os, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import backtest as B, national as NA, simulate as S, test_2026 as T26

WEIGHTS = (0.0, 0.25, 0.5, 0.75, 1.0)
CAUCUS_AFTER = {**S.CAUCUS_AFTER, 2026: 56}
TIE_GOES_TO = {**S.TIE_GOES_TO, 2026: 'R'}
LEFT_OUT_DEM = {2018: 1, 2020: 0, 2022: 0, 2024: 0, 2026: 0}       # races outside the test, all one-sided (see build_data, test_2026)


national_seats, expected_seats, shift_for = S.national_seats, S.expected_seats, S.shift_for


def fits_for(X, T):
    """The working version's forecasts and error sizes for every test year and distance, as simulate.py and test_2026.py
    make them (the shared error never shrinking with distance)."""
    oos = {(y, d): S.forecast(X[(X.year != y) & (X.days == d)], X[(X.year == y) & (X.days == d)])[1] for y in B.YEARS for d in B.DAYS}
    out = {}
    for y in list(B.YEARS) + [2026]:
        tr = X[X.year != y] if y != 2026 else X; te = X[X.year == y] if y != 2026 else T
        fits = {d: S.fold(tr[tr.days == d], te[te.days == d].copy(), {yy: oos[(yy, d)] for yy in B.YEARS if yy != y}, 'others') for d in B.DAYS}
        near = 0.0
        for d in sorted(B.DAYS):
            bf, sn = fits[d]; sn2 = max(sn, near); near = sn2
            if sn2 > sn:
                bf['sd_total'] = np.maximum(bf.sd_total.values, sn2 + 0.1); bf['sd_own'] = np.maximum(S.OWN_FLOOR, np.sqrt(np.maximum(bf.sd_total.values ** 2 - sn2 ** 2, 0)))
            out[(y, d)] = (bf, sn2)
    return out


def main():
    X = B.build(); T = T26.features(T26.races()); nat = NA.National(); rng = np.random.default_rng(2028)
    F = fits_for(X, T); rows = []
    for (y, d), (bf, sn) in sorted(F.items()):
        won = (bf.dem2.values > 50).astype(float); actual_wins = int(won.sum())
        holdover = CAUCUS_AFTER[y] - actual_wins - LEFT_OUT_DEM[y]
        base = holdover + LEFT_OUT_DEM[y]
        ns = national_seats(nat, y, d)
        own = base + expected_seats(bf.m.values, bf.sd_total.values, 0.0)
        for w in WEIGHTS:
            b2 = S.combine(bf, base, ns, w); delta = float((b2.m - bf.m).iloc[0])
            sim = S.simulate(b2, sn, rng, True); total = base + (sim > 50).sum(axis=1)
            control = np.where(total > 50, 1.0, np.where(total == 50, 1.0 if TIE_GOES_TO[y] == 'D' else 0.0, 0.0)).mean()
            won_control = int(CAUCUS_AFTER[y] > 50 or (CAUCUS_AFTER[y] == 50 and TIE_GOES_TO[y] == 'D'))
            p = np.clip((sim > 50).mean(axis=0), 0.001, 0.999); err = 2 * (b2.m.values - b2.dem2.values)
            lo, hi = np.percentile(total, [10, 90]); pc = min(max(control, 0.001), 0.999)
            rows.append({'year': y, 'days': d, 'weight': w, 'national_seats': round(ns, 2), 'race_model_seats': round(own, 2), 'shift': round(delta, 3),
                         'seats_mean': round(float(total.mean()), 2), 'low80': int(lo), 'high80': int(hi), 'actual': CAUCUS_AFTER[y],
                         'seat_error': round(float(total.mean()) - CAUCUS_AFTER[y], 2), 'inside80': bool(lo <= CAUCUS_AFTER[y] <= hi),
                         'p_dem_control': round(float(control), 4), 'control_log_loss': float(-(won_control * math.log(pc) + (1 - won_control) * math.log(1 - pc))),
                         'margin_miss': float(np.sqrt(np.mean(err ** 2))), 'race_log_loss': float(-np.mean(won * np.log(p) + (1 - won) * np.log(1 - p))), 'races': len(b2)})
    R = pd.DataFrame(rows)
    pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
    def summ(Z):
        return Z.groupby(['weight', 'days']).apply(lambda x: pd.Series({
            'seat_rmse': float(np.sqrt((x.seat_error ** 2).mean())), 'inside80': float(x.inside80.mean()), 'control_log_loss': float(x.control_log_loss.mean()),
            'margin_miss': float(np.sqrt(np.average(x.margin_miss ** 2, weights=x.races))), 'race_log_loss': float(np.average(x.race_log_loss, weights=x.races))}), include_groups=False).reset_index()
    S5, S4 = summ(R), summ(R[R.year < 2026])
    for title, Z in (('all five years', S5), ('2018-2024', S4)):
        print(title)
        for m in ('seat_rmse', 'control_log_loss', 'margin_miss', 'race_log_loss', 'inside80'):
            print(m); print(Z.pivot(index='days', columns='weight', values=m).round(3).sort_index(ascending=False))
    print(R[(R.weight.isin([0.0, 0.5, 1.0])) & R.days.isin([365, 60, 1])][['year', 'days', 'weight', 'national_seats', 'race_model_seats', 'seats_mean', 'low80', 'high80', 'actual', 'p_dem_control']].to_string(index=False))
    with open(os.path.join(ROOT, 'data', 'senate', 'combine_test.json'), 'w') as f:
        json.dump({'note': 'Race simulation combined with a national seat-change model; seats are the Democratic caucus after the election.',
                   'summary_all_five': S5.round(4).to_dict('records'), 'summary_2018_2024': S4.round(4).to_dict('records'), 'by_year': R.round(4).to_dict('records')}, f, indent=1)
    return R


if __name__ == '__main__':
    main()
