"""Builds docs/index.html from template.html and the model's output. The page is one self-contained file."""
import base64, json, re
import pandas as pd

TITLE = 'The Margin'
CONTACT = None            # {'label': 'Contact on LinkedIn', 'url': 'https://www.linkedin.com/in/...'} once there is an address to link to
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
    data = {'f': f, 'back': back, 'checks': ck, 'contact': CONTACT, 'research': json.load(open('data/research.json')), 'history': [{'date': r.date, 'p': round(r.p_dem, 4), 'national': r.national} for r in hist.itertuples()]}
    shapes = open('data/us-states.js').read(); shapes = shapes[shapes.index('window.US_STATES'):]
    fonts = ''
    for fam, file in (('Newsreader', 'newsreader-latin-wght-normal.woff2'), ('Instrument Sans', 'instrument-sans-latin-wght-normal.woff2')):
        fonts += "@font-face{font-family:'%s';font-weight:200 900;font-display:swap;src:url(data:font/woff2;base64,%s) format('woff2')}\n" % (fam, base64.b64encode(open('fonts/' + file, 'rb').read()).decode())
    t = open('template.html').read()
    t = t.replace('{{TITLE}}', TITLE).replace('/*FONTS*/', fonts).replace('/*SHAPES*/', shapes).replace('/*DATA*/', 'const DATA = ' + json.dumps(data, separators=(',', ':')) + ';')
    assert not re.search(r'\{\{|/\*(FONTS|SHAPES|DATA)\*/', t)
    open('docs/index.html', 'w').write(t); print('docs/index.html', len(t), 'bytes')

if __name__ == '__main__':
    main()
