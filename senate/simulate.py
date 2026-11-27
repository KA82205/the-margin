"""Senate back-test, step 6: the races simulated together, for the number of seats each party wins and the chance of
control. Research only: nothing here feeds the presidential forecast or appears on the site.

Each race's forecast is the working version of backtest.py (+track, +polls by volume), made as before from the other three
years. Its error is split in two, both sized from those other years:

    shared     one draw per simulated election, the same for every race: how far a year's races missed together (the 2020
               polling miss). Its size is the average product of two races' misses in the same year, which is what a
               shared error alone would make it. It is drawn from a t distribution with 5 degrees of freedom, as the
               presidential simulation draws its national error, so a large shared miss is possible.
    own        one draw per race per simulated election, the rest of the race's error.

The two together keep each race's own spread as it was (races with polls and races without), so the chance of each race
is about what it was; what changes is that the races now move together, which is what a seat count needs.

    python senate/simulate.py         writes data/senate/simulation.json
"""
import json, math, os, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import backtest as B

WORKING = '+track'                    # the fundamentals of the working version; its polls are blended by volume
SIMS = 40000
T_DF = 5
SHARED_FLOOR = 0.5                    # points of two-party share: the shared error is never taken as none at all
OWN_FLOOR = 1.0
# The Democratic caucus after each election (Georgia's 2021 runoffs counted with 2020), and who broke a 50-50 tie in the
# Congress it elected. The back-test takes the tie-breaker as known; a 2028 forecast would take it from the presidential
# simulation.
CAUCUS_AFTER = {2018: 47, 2020: 50, 2022: 51, 2024: 47}
TIE_GOES_TO = {2018: 'R', 2020: 'D', 2022: 'D', 2024: 'R'}


def shared_sd(e, years):
    """The size of the error a year's races share: the average, across years, of the product of two different races'
    misses in the same year. With only shared and own errors, that is the shared error's variance."""
    num = den = 0.0
    for y in np.unique(years):
        x = e[years == y]; n = len(x)
        if n < 2: continue
        num += (x.sum() ** 2 - (x ** 2).sum()); den += n * (n - 1)
    v = num / den if den else 0.0
    return max(SHARED_FLOOR, math.sqrt(max(v, 0.0)))


def forecast(a, b):
    """The working version's forecast of races b, fitted on races a."""
    cols = B.VERSIONS[WORKING]; coef, _ = B.fit(a, cols)
    af = a.assign(f=B.predict(coef, a, cols)); bf = b.assign(f=B.predict(coef, b, cols))
    p = B.volume_fit(af)
    af['m'] = B.blend(af, p); bf['m'] = B.blend(bf, p)
    return af, bf


def fold(a, b, oos, how='others'):
    """The working version's forecast of the test races (b) from the training races (a), with its errors' two parts.

    Misses inside the fit understate the shared part, because the fit bends toward each training year's national mood.
    So it is measured on misses made out of sample: those of the other years, each when it was the year left out ('oos').
    Those forecasts were fitted with the test year among their training years; the test year's own miss is never used.
    how: 'others' sizes the shared part from those misses and each race's whole spread from the fit, as before;
    'others, both' sizes both from those misses; 'inside' sizes both inside the fit (kept for comparison)."""
    af, bf = forecast(a, b)
    if how == 'inside':
        e, yrs, hp = af.m.values - af.dem2.values, af.year.values, af.poll.notna().values
    else:
        o = pd.concat([oos[y] for y in np.unique(a.year)]); e, yrs, hp = o.m.values - o.dem2.values, o.year.values, o.poll.notna().values
    sn = shared_sd(e, yrs)
    if how == 'others':
        e, hp = af.m.values - af.dem2.values, af.poll.notna().values
    tot = {True: float(np.sqrt(np.mean(e[hp] ** 2))), False: float(np.sqrt(np.mean(e[~hp] ** 2))) if (~hp).any() else float(np.sqrt(np.mean(e[hp] ** 2)))}
    tot = {k: max(v, sn + 0.1) for k, v in tot.items()}
    own = {k: max(OWN_FLOOR, math.sqrt(max(v ** 2 - sn ** 2, 0.0))) for k, v in tot.items()}
    bhp = bf.poll.notna().values
    bf['sd_total'] = np.where(bhp, tot[True], tot[False]); bf['sd_own'] = np.where(bhp, own[True], own[False])
    return bf, sn


def simulate(bf, sn, rng, joint=True):
    """Simulated Democratic two-party shares, SIMS x races. The t draw is scaled so that its spread matches sn."""
    n = len(bf)
    if joint:
        nat = rng.standard_t(T_DF, size=(SIMS, 1)) * sn * math.sqrt((T_DF - 2) / T_DF)
        own = rng.standard_normal((SIMS, n)) * bf.sd_own.values
        return bf.m.values + nat + own
    return bf.m.values + rng.standard_normal((SIMS, n)) * bf.sd_total.values


MONOTONE = True
HOW = {'others': 'together', 'others, both': 'together, both from out of sample', 'inside': 'together, from inside the fit'}


def main():
    X = B.build(); rng = np.random.default_rng(2028)
    ex = pd.read_csv(os.path.join(ROOT, 'data', 'senate', 'excluded.csv'))
    # the races left out of the test all went one way, and are counted as such: California 2018 to a Democrat; Arkansas 2020
    # and Alaska 2022 to Republicans
    ex_dem = {2018: 1, 2020: 0, 2022: 0, 2024: 0}
    # every year's out-of-sample forecast at every distance, made from the other three years
    oos = {(y, d): forecast(X[(X.year != y) & (X.days == d)], X[(X.year == y) & (X.days == d)])[1] for y in B.YEARS for d in B.DAYS}
    rows = []
    for y in B.YEARS:
        tr, te = X[X.year != y], X[X.year == y]
        for how in HOW:
          fits = {d: fold(tr[tr.days == d], te[te.days == d].copy(), {yy: oos[(yy, d)] for yy in B.YEARS if yy != y}, how) for d in B.DAYS}
          # the national mood is no easier to call further out: the shared part at a distance is at least what it is nearer
          nearer = 0.0
          for d in sorted(B.DAYS):
              bf, sn = fits[d]; sn2 = max(sn, nearer) if MONOTONE else sn; nearer = sn2
              if sn2 > sn:
                  tot = bf.sd_total.values; bf['sd_total'] = np.maximum(tot, sn2 + 0.1); bf['sd_own'] = np.maximum(OWN_FLOOR, np.sqrt(np.maximum(bf.sd_total.values ** 2 - sn2 ** 2, 0)))
              fits[d] = (bf, sn2)
          for d in B.DAYS:
                bf, sn = fits[d]
                actual = int((bf.dem2 > 50).sum())
                holdover = CAUCUS_AFTER[y] - actual - ex_dem[y]
                for joint in ((True, False) if how == 'others' else (True,)):
                    S = simulate(bf, sn, rng, joint)
                    seats = (S > 50).sum(axis=1)
                    total = seats + holdover + ex_dem[y]
                    control = np.where(total > 50, 1.0, np.where(total == 50, 1.0 if TIE_GOES_TO[y] == 'D' else 0.0, 0.0))
                    lo, hi = np.percentile(seats, [10, 90]); lo50, hi50 = np.percentile(seats, [25, 75])
                    p_exact = float(np.mean(seats == actual))
                    race_p = np.clip((S > 50).mean(axis=0), 0.001, 0.999); won = (bf.dem2.values > 50).astype(float)
                    rows.append({'year': y, 'days': d, 'model': (HOW[how] if joint else 'independent'), 'races': len(bf), 'shared_sd': round(sn, 3),
                                 'dem_seats_mean': round(float(seats.mean()), 2), 'low80': int(lo), 'high80': int(hi), 'low50': int(lo50), 'high50': int(hi50),
                                 'actual': actual, 'inside80': bool(lo <= actual <= hi), 'inside50': bool(lo50 <= actual <= hi50),
                                 'p_actual_count': round(p_exact, 4), 'p_dem_control': round(float(control.mean()), 4),
                                 'dem_won_control': int(CAUCUS_AFTER[y] > 50 or (CAUCUS_AFTER[y] == 50 and TIE_GOES_TO[y] == 'D')),
                                 'race_log_loss': round(float(-np.mean(won * np.log(race_p) + (1 - won) * np.log(1 - race_p))), 4)})
    R = pd.DataFrame(rows)
    R['log_score_count'] = -np.log(R.p_actual_count.clip(1e-4))
    pc = R.p_dem_control.clip(0.001, 0.999); R['log_loss_control'] = -(R.dem_won_control * np.log(pc) + (1 - R.dem_won_control) * np.log(1 - pc))
    summ = R.groupby(['model', 'days']).agg(shared_sd=('shared_sd', 'mean'), inside80=('inside80', 'mean'), inside50=('inside50', 'mean'),
                                           log_score_count=('log_score_count', 'mean'), log_loss_control=('log_loss_control', 'mean'), race_log_loss=('race_log_loss', 'mean')).reset_index()
    pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
    print(R[R.model == 'together'][['year', 'days', 'shared_sd', 'dem_seats_mean', 'low80', 'high80', 'actual', 'p_dem_control', 'dem_won_control']].to_string(index=False))
    print(summ.round(3).to_string(index=False))
    with open(os.path.join(ROOT, 'data', 'senate', 'simulation.json'), 'w') as f:
        json.dump({'note': 'Senate races simulated together, leave one year out. Seats are the Democratic side\'s wins among the races in the test.',
                   'sims': SIMS, 't_df': T_DF, 'by_year': R.to_dict('records'), 'summary': summ.round(4).to_dict('records')}, f, indent=1)
    return R, summ


if __name__ == '__main__':
    main()
