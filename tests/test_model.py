"""The published forecast is the one on record, and the candidate's rules do what they say.

    python tests/test_model.py
"""
import os, sys

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, HERE)
os.chdir(HERE)
import numpy as np, pandas as pd                                            # noqa: E402
import backtest as B, fundamentals as F, model as M, timeline as T          # noqa: E402


def test_the_published_forecast_is_the_one_on_record():
    """The last-day forecasts of 2008 to 2024, run now, are the ones in data/backtest.csv to the last digit. A change to
    the code that moves the published forecast fails here, whatever else it was meant to do."""
    assert (M.SET['national_prior'], M.SET['poll_weight'], M.SET['state_poll_weight'], M.SET['state_model_mode'], M.SET['state_model_weight'], M.SET['prior_polls']) == ('fundamentals', 'precision', 'volume', 'share', 0.5, 1.5)
    now = B.run(days=[1]).set_index('year'); rec = pd.read_csv('data/backtest.csv'); rec = rec[rec.days == 1].set_index('year')
    for col in ('p_dem', 'national', 'ev_median', 'ev_lo', 'ev_hi', 'state_mae', 'states_called', 'cover80'):
        assert np.allclose(now[col].astype(float), rec[col].astype(float), rtol=0, atol=1e-9), (col, now[col].tolist(), rec[col].tolist())


def setup(year=2024, days=300):
    res, polls, errs = B.load(); t = F.table(); asof = pd.Timestamp(M.ELECTION[year]) - pd.Timedelta(days=days)
    fd, fsd, parts = F.forecast(year, t); extra, two = B.state_models(year)
    return dict(year=year, asof=asof, polls=polls, res=res, tables=M.error_tables(year, res, errs), ev=M.ev_table(year, res), extra_prior=extra, timeline=T.curves(year)), two, parts


def candidate(kw, prior, **more):
    old = dict(M.SET); M.SET.update(M.CANDIDATE)
    try:
        return M.forecast(kw['year'], kw['asof'], kw['polls'], kw['res'], kw['tables'], (prior, 0.0), ev=kw['ev'], extra_prior=kw['extra_prior'], timeline=kw['timeline'], **more)
    finally:
        M.SET.clear(); M.SET.update(old)


def test_polls_already_in_the_prior_are_counted_once():
    kw, two, parts = setup(); prior = F.three_models(two['US'][0], two['US'][1], parts['keys_model'])
    out, info = candidate(kw, prior)
    rec = info['poll_share_record']; assert 0 < rec < 0.2 and abs(info['poll_share'] - rec) < 1e-12 and abs(info['poll_share_total'] - rec) < 1e-12
    out2, info2 = candidate(kw, prior, prior_poll_load=0.03)                          # the prior carries less than the record gives: the average gets the rest
    assert 0 < info2['poll_share'] < rec and abs(info2['poll_share_total'] - rec) < 1e-12
    out3, info3 = candidate(kw, prior, prior_poll_load=0.174)                         # the prior carries more: the average gets nothing, and the range is wider for it
    assert info3['poll_share'] == 0 and abs(out3['national'] - prior) < 1e-12 and abs(info3['poll_share_total'] - 0.174) < 1e-12 and out3['national_sd'] > out['national_sd']
    out4, info4 = candidate(kw, prior, pairing_spread=3.0)                            # nominees not known: the same polls count for less
    assert info4['poll_share'] < info['poll_share']


def test_the_long_range_model_before_and_after_its_polls_exist():
    res, polls, errs = B.load(); tl = T.curves(2024); third = M.LONG_RANGE_POLLS / 3
    def at(day, before):
        old = dict(M.SET); M.SET['long_range_before'] = before
        try: return M.long_range_weight(2024, day, tl, polls)
        finally: M.SET.clear(); M.SET.update(old)
    assert at('2023-06-01', 'out') == (0.0, 0.0)                                       # left out: nothing of it, and no polls in the prior
    w, g = at('2023-06-01', 'full'); assert w == 1.0 and abs(g - third) < 1e-12
    w1, g1 = at('2023-03-01', 'part'); w2, g2 = at('2023-09-01', 'part')
    assert 0 < w1 < w2 < 1 and 0 < g1 < g2 < third                                      # in part: more of it as its own polls come nearer
    for before in ('out', 'part', 'full'):                                               # once its polls are fixed the setting no longer matters
        w, g = at('2023-11-20', before); assert w == 1.0 and 0.2 * third < g <= third     # the October polls still weigh in the average
        w, g = at('2024-06-01', before); assert w == 1.0 and g < 0.01 * third             # and by summer they have aged out of it
    assert abs(F.three_models(52.0, 49.0, 53.0) - (52 + 49 + 53) / 3) < 1e-12 and abs(F.three_models(52.0, 49.0, 53.0, 0.0) - 52.5) < 1e-12


def test_early_state_polls_stay_under_the_ceiling():
    kw, two, parts = setup(2024, 700); r = kw['res'][kw['res'].year == 2024].set_index('state')
    fake = pd.DataFrame([{'year': 2024, 'state': 'PA', 'pollster': f'Poll {i}', 'end': kw['asof'] - pd.Timedelta(days=2 + i), 'n': 800, 'pop': 'lv', 'dem2': float(r.dem2['PA']) + 5.0} for i in range(10)])
    kw['polls'] = pd.concat([kw['polls'][(kw['polls'].year == 2024) & (kw['polls'].state == 'US')], fake])
    prior = F.three_models(two['US'][0], two['US'][1], parts['keys_model'])
    ceiling = float(M.curve(kw['timeline']['state'], 700) / M.curve(kw['timeline']['state'], 1))
    pa = candidate(kw, prior)[0]['states'].set_index('state').loc['PA']
    assert 0 < pa.poll_share <= ceiling < 0.2, (pa.poll_share, ceiling)                 # ten fresh polls two years out: a small share of the state
    pub = M.forecast(kw['year'], kw['asof'], kw['polls'], kw['res'], kw['tables'], (prior, 2.5), ev=kw['ev'], extra_prior=kw['extra_prior'])[0]['states'].set_index('state').loc['PA']
    assert pub.poll_share > 0.8                                                         # the published rule would give them most of it: the reason state polls are not counted yet
    kw2, _, _ = setup(2024, 1); assert abs(float(M.curve(kw2['timeline']['state'], 1) / M.curve(kw2['timeline']['state'], 1)) - 1) < 1e-12      # no ceiling on the last day


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_') and callable(fn):
            fn(); print('ok', name)
