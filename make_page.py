"""Builds docs/index.html from template.html and the model's output. The page is one self-contained file."""
import numpy as np
import base64, json, os, re
from model import SET as M_SET
import pandas as pd

TITLE = 'The Margin'
CONTACT = {'label': 'Contact', 'url': 'https://www.linkedin.com/in/kleinahmetaj/'}      # the same address as on Tipping Point; no name or picture beside it
NAMES = {v['name']: k for k, v in json.load(open('data/results_2024.json')).items()}
ABBR = {k.replace('-', ''): n for n, k in NAMES.items()}

def main():
    f = json.load(open('data/forecast_2028.json')); bt = pd.read_csv('data/backtest.csv')
    for s in f['states']: s['name'] = ABBR.get(s['state'], s['state'])
    last = bt[bt.days == 1]
    back = {'final': [{'year': int(r.year), 'p_dem': round(r.p_dem, 3), 'p_winner': round(r.p_winner, 3), 'called': bool(r.called), 'national': round(r.national, 2), 'national_actual': round(r.national_actual, 2),
                       'ev': round(r.ev_median), 'ev_lo': round(r.ev_lo), 'ev_hi': round(r.ev_hi), 'ev_actual': int(r.ev_actual), 'states': int(r.states_called), 'of': int(r.of), 'state_mae': round(r.state_mae, 1)} for r in last.itertuples()],
            'by_day': [{'days': int(d), 'called': int(g.called.sum()), 'p_winner': round(g.p_winner.mean(), 3), 'national': round(2 * g.national_error.abs().mean(), 1), 'state_mae': round(2 * g.state_mae.mean(), 1),
                        'states': int(g.states_called.sum()), 'of': int(g.of.sum()), 'cover80': round(g.cover80.mean(), 3)} for d, g in bt.groupby('days')],
            'paths': {str(int(y)): [{'days': int(r.days), 'p_winner': round(r.p_winner, 3)} for r in g.sort_values('days', ascending=False).itertuples()] for y, g in bt.groupby('year')}}
    # the statements the page makes, checked against the numbers
    assert last.called.sum() == 4 and list(last.year[~last.called]) == [2016], 'the page says the final forecast favored the winner in four of five, missing 2016'
    assert 0.85 < last.cover80.mean() < 0.97
    inside = [bool(r.ev_lo <= r.ev_actual <= r.ev_hi) for r in last.itertuples()]
    assert inside == [True, True, False, True, True], 'the page says the electoral-vote result fell inside the range in every year but 2016'
    r24 = last[last.year == 2024].iloc[0]; assert r24.ev_median < 270 < r24.ev, 'the page explains 2024: the middle run was a Republican win, the average a narrow Democratic one'
    st = pd.read_csv('data/backtest_states.csv'); st['miss'] = (st.p_dem > 0.5) != (st.actual > 50)
    for r in back['final']: r['missed'] = [ABBR.get(s, s) for s in st[(st.year == r['year']) & st.miss].state]
    ck = json.load(open('data/checks.json'))
    # every miss on the page is in points of margin (twice the points of vote share the scripts work in)
    for r in ck['ratings']: r['state_miss'] = round(2 * r['state_miss'], 2); r['close_miss'] = round(2 * r['close_miss'], 2)
    for s in ck['settings'] + [ck['base']]:
        for d in ('1', '30'): s[d]['state_miss'] = round(2 * s[d]['state_miss'], 2)
    r0, r15 = ck['ratings'][0], ck['ratings'][1]
    assert r15['called'] <= r0['called'] and r15['close_miss'] >= r0['close_miss'] and f['settings']['rating_weight'] == 0, 'the page says expert ratings did not help and are left out'
    miss = [s['1']['state_miss'] for s in ck['settings']]
    assert max(miss) - min(miss) < 0.4
    hist = pd.read_csv('data/history.csv'); assert hist.date.iloc[-1] == f['as_of'], 'the day-by-day record does not end on the forecast date'
    sm = json.load(open('data/state_model_check.json'))      # the share of a state's starting point given to the state-level models, tried on 2008-2024
    pick = lambda key, field: {str(x['w']): x[field] for x in sm['runs'][key]}
    ck['state_model'] = {'used': M_SET['state_model_weight'], 'start': pick('average/share', 'start_miss'), 'start_close': pick('average/share', 'start_miss_close'),
                         'one_model': pick('approval_economy/share', 'start_miss'), 'lean_best': min(x['start_miss'] for x in sm['runs']['average/lean']),
                         'eve': {str(x['w']): x['miss']['1'] if '1' in x['miss'] else x['miss'][1] for x in sm['runs']['average/share']}, 'polls_share': sm['polls_share_close'], 'n_close': sm['n_close']}
    s0, s5 = ck['state_model']['start']['0'], ck['state_model']['start'][str(ck['state_model']['used'])]
    assert s5 < s0 and abs(ck['state_model']['start']['0.6'] - ck['state_model']['start']['0.5']) < 0.1 and ck['state_model']['one_model']['1.0'] > ck['state_model']['one_model']['0.4'], 'the page says the state models help and that half to four fifths does equally well'
    ks = json.load(open('data/keys_study.json')); kmean = lambda w, k: float(np.mean([ks['ways'][w][str(d)][k] for d in ks['days']]))
    ck['keys_study'] = {'hybrid': {'national': kmean('hybrid', 'national')}, 'half': {'national': kmean('half', 'national')}, 'none': {'national': kmean('no keys', 'national')}, 'line': ks['parts']['keys line']['size']}
    f.pop('candidate', None); f.pop('state_poll_sources', None)      # the forecast under review is kept in the data file and is not part of the page
    data = {'f': f, 'back': back, 'checks': ck, 'contact': CONTACT, 'research': json.load(open('data/research.json')), 'history': [{'date': r.date, 'p': round(r.p_dem, 4), 'sim': round(r.p_model, 4), 'national': r.national, **({'rep': round(r.p_rep, 4)} if 'p_rep' in hist.columns and r.p_rep == r.p_rep else {})} for r in hist.itertuples()],
            'methods': json.load(open('data/methods.json'))}
    try:
        kept = json.load(open('docs/archive/index.json')); data['archive'] = {'n': len(kept), 'first': kept[0]['made'][:10]} if kept else None
        notes = {n['file']: n['note'] for n in (json.load(open('docs/archive/notes.json')) if os.path.exists('docs/archive/notes.json') else [])}      # corrections to what was recorded about a kept forecast; the forecast itself is never touched
        data['kept'] = [{'made': k['made'], 'p': k['p_dem'], 'national': k['national'], 'ev': k['ev_median'], 'why': k.get('why') or [], 'note': notes.get(k.get('file'))} for k in kept]
    except FileNotFoundError:
        data['archive'] = None
    res = pd.read_csv('data/results.csv'); res = res[res.year >= 1976]; years = sorted(res.year.unique())      # how each state has voted, for its profile
    wide = res.pivot(index='state', columns='year', values='dem2')
    data['hist'] = {'years': [int(y) for y in years], 'nat': [round(float(res.nat2[res.year == y].iloc[0]), 2) for y in years],
                    's': {s: [None if pd.isna(v) else round(float(v), 2) for v in wide.loc[s]] for s in wide.index}}
    assert all(s['state'] in data['hist']['s'] for s in f['states']), 'a state on the map has no history'
    shapes = open('data/us-states.js').read(); shapes = shapes[shapes.index('window.US_STATES'):]
    fonts = ''
    for fam, file in (('Newsreader', 'newsreader-latin-wght-normal.woff2'), ('Instrument Sans', 'instrument-sans-latin-wght-normal.woff2')):
        fonts += "@font-face{font-family:'%s';font-weight:200 900;font-display:swap;src:url(data:font/woff2;base64,%s) format('woff2')}\n" % (fam, base64.b64encode(open('fonts/' + file, 'rb').read()).decode())
    t = open('template.html').read()
    if os.path.exists('data/interval_study.json'):        # how the prediction intervals have held up, and the markets on 2024
        iv = json.load(open('data/interval_study.json')); pub = next(v for k, v in iv['variants'].items() if k.startswith('as published')); was = next(v for k, v in iv['variants'].items() if k.startswith('until'))
        data['intervals'] = {'days': {d: {k: v[k] for k in ('cover50', 'cover80', 'cover90', 'cover95', 'width80', 'more_republican_than_80', 'more_democratic_than_80')} for d, v in iv['states_by_days'].items()},
                             'last_day_by_year': {y: v['cover80'] for y, v in iv['states_by_year_last_day'].items()}, 'national': iv['US']['all'], 'ev': iv['EV']['all'],
                             'now': {k: pub[k] for k in ('wis', 'cover80', 'width80')}, 'before': {k: was[k] for k in ('wis', 'cover80', 'width80')}, 'better_in': pub['better_than_the_earlier_sizing_in'],
                             'two_years_out': {k: v for k, v in iv['two_years_out'].items() if k != 'by_election'}}
    if os.path.exists('data/market_study.json'):
        ms = json.load(open('data/market_study.json')); data['market_study'] = {'ways': ms['mean_over_days'], 'days': ms['days_scored'], 'states': ms['by_days'][str(ms['days_scored'][-1])]['states'] if str(ms['days_scored'][-1]) in ms['by_days'] else ms['by_days'][ms['days_scored'][-1]]['states']}
    if os.path.exists('data/method_change.json'): data['method_change'] = json.load(open('data/method_change.json'))
    t = t.replace('{{TITLE}}', TITLE).replace('/*FONTS*/', fonts).replace('/*SHAPES*/', shapes).replace('/*DATA*/', 'const DATA = ' + json.dumps(data, separators=(',', ':')) + ';')
    assert not re.search(r'\{\{|/\*(FONTS|SHAPES|DATA)\*/', t)
    open('docs/index.html', 'w').write(t); print('docs/index.html', len(t), 'bytes')

if __name__ == '__main__':
    main()
