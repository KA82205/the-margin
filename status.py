"""Writes STATUS.md: the method as frozen, the evidence behind it, the state-level and approval studies, what runs by
itself and what does not. Every figure in a table is read from a data file or worked out here; none is typed. The lines
about what was seen in production are a dated record and are typed.

    python status.py
"""
import json
import numpy as np, pandas as pd
import fundamentals as F

FC = json.load(open('data/forecast_2028.json')); C = FC['candidate']; H = C['hybrid']
import model as M
table = lambda head, rows: '\n'.join(['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)] + ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows])
mgn = lambda sh: (lambda m: '0.0' if round(abs(m), 1) == 0 else ('D+' if m > 0 else 'R+') + f'{abs(m):.1f}')(2 * (sh - 50))
mg = lambda m: '0.0' if round(abs(m), 1) == 0 else ('D+' if m > 0 else 'R+') + f'{abs(m):.1f}'


def backtests():
    """The method as published against the one before it, on 2008 to 2024, by days out."""
    A, B = pd.read_csv('data/backtest.csv'), pd.read_csv('data/backtest_previous.csv'); days = sorted(A.days.unique(), reverse=True)
    def row(name, d, f): return [name] + [f(d[d.days == x]) for x in days]
    nat = lambda g: f'{(2 * g.national_error).abs().mean():.2f}'; st = lambda g: f'{2 * g.state_mae.mean():.2f}'
    won = lambda g: f'{int(g.called.sum())} of {len(g)}'; ll = lambda g: f'{float(-np.log(g.p_winner.clip(1e-6)).mean()):.2f}'
    head = ['', *(('last day' if d == 1 else f'{d} days') for d in days)]
    return table(head, [row('National miss, official method', A, nat), row('National miss, method before', B, nat), row('State miss, official', A, st), row('State miss, before', B, st),
                        row('Favored the winner, official', A, won), row('Favored the winner, before', B, won), row('Log loss for the winner, official', A, ll), row('Log loss for the winner, before', B, ll)])


def texas_florida():
    t = open('data/nowcast.js').read(); nc = json.loads(t[t.index('{'):t.rindex('}') + 1]); us = nc['models']; T = json.load(open('data/state_trend_study.json'))['texas_florida']
    rows = {}
    for st in ('TX', 'FL'):
        n = next(x for x in nc['states'] if x['abbr'] == st); f = next(x for x in FC['states'] if x['state'] == st); tf = T[st]
        rows[st] = {'2020 result': mg(tf['margin']['2020']), '2024 result': mg(tf['margin']['2024']), '2020 against the nation': mg(tf['lean']['2020']), '2024 against the nation': mg(tf['lean']['2024']),
                    'Lean used (three parts 2024, one part 2020)': mg(tf['rules_2028']['as used: 0.75 and 0.25']), 'Approval-and-economy model, against its own national figure': mg(2 * (n['enns'] - us['enns']['demPopular'])),
                    'Long-range model, against its own national figure': mg(2 * (n['desart'] - us['desart']['demPopular'])), 'The two models together': mg(2 * (n['demShare'] - nc['summary']['demPopular'])),
                    'Presidential approval in the state': f"{n['approve']:.1f}%", 'State economy index': f"{n['econ']:+.2f}", 'Starting point against the nation: half lean, half the models': mg(2 * (f['prior'] - FC['national'])),
                    'National number': mgn(FC['national']), 'State polls for 2028': 'none', 'Forecast': mg(2 * (f['mean'] - 50)), 'Democrats win it': f"{100 * f['p_dem']:.0f} in 100",
                    'If the last election alone set the lean': mg(tf['rules_2028']['the last election alone']), 'If a quarter of the 2020 to 2024 move were carried forward': mg(tf['rules_2028']['trend, a quarter carried forward'])}
    return table(['', 'Texas', 'Florida'], [[k, rows['TX'][k], rows['FL'][k]] for k in rows['TX']]), rows


def trend_study():
    T = json.load(open('data/state_trend_study.json'))
    a = table(['Rule for a state\'s lean', 'Elections scored', 'Typical miss', 'The rule in use, same elections', 'Closer in', 'Difference (standard error)'],
              [[k[0].upper() + k[1:], f"{v['elections']} (from {v['since']})", f"{v['miss']:.2f}", f"{v['as_used_same_years']:.2f}", f"{v['better_in']} of {v['elections']}", f"{v['difference']:+.2f} ({v['se']})"] for k, v in T['rules'].items()])
    b = table(['With the state models in, 2008 to 2024', 'Typical miss'], [[k[0].upper() + k[1:], f"{v['miss']:.2f}"] for k, v in T['with_state_models'].items()])
    return a, b, T


def approval_moves():
    A = json.load(open('data/approval_moves.json'))
    return table(['Net approval, midterm reading to June of the election year', 'Terms', 'Mean change', 'Mean size of the change', 'Median size', 'Standard deviation', 'Root mean square', 'Within 10', 'Within 15', 'Within 20'],
                 [[k[0].upper() + k[1:], v['n'], f"{v['mean']:+.1f}", v['mean_abs'], v['median_abs'], v['sd'], v['rms'], *(f"{v['within'][w]} of {v['n']}" for w in ('10', '15', '20'))] for k, v in A['groups'].items()]), A


def ranges():
    S = pd.read_csv('data/backtest_states.csv'); S = S[S.state.str.len() == 2].copy()
    S['inside'] = (S.actual >= S.lo) & (S.actual <= S.hi); S['m'] = 2 * (S['mean'] - 50); S['width'] = 2 * (S.hi - S.lo)
    S['z'] = np.where(S.actual >= S['mean'], (S.actual - S['mean']) / (S.hi - S['mean']), (S['mean'] - S.actual) / (S['mean'] - S.lo))
    row = lambda name, m: [name, int(m.sum()), f"{S.inside[m].mean():.0%}", f"{(S.actual < S.lo)[m].mean():.0%}", f"{(S.actual > S.hi)[m].mean():.0%}", f"{S.width[m].mean():.1f}", f"{(2 * (S['mean'] - S.actual))[m].abs().mean():.1f}"]
    groups = [('All states and the District', S.year > 0), ('Projected within 10 points', S.m.abs() < 10), ('Projected 10 to 30 points apart', (S.m.abs() >= 10) & (S.m.abs() < 30)), ('Projected 30 points or more apart', S.m.abs() >= 30),
              ('Leaning Democratic', S.m > 0), ('Leaning Republican', S.m < 0)]
    a = table(['Last day, 2008 to 2024', 'Forecasts', 'Result inside the range', 'More Republican than the range', 'More Democratic', 'Width of the range, points', 'Typical miss'], [row(n, m) for n, m in groups])
    b = table(['Election', 'Result inside the range', 'More Republican than the range', 'More Democratic', 'Share of the range\'s width that would have held four results in five'],
              [[int(y), f"{g.inside.mean():.0%}", f"{(g.actual < g.lo).mean():.0%}", f"{(g.actual > g.hi).mean():.0%}", f"{g.z.quantile(0.8):.0%}"] for y, g in S.groupby('year')])
    R = pd.read_csv('data/backtest.csv').groupby('days').agg(cover=('cover80', 'mean'), width=('width80', 'mean'), nat=('nat_in80', 'sum')).sort_index(ascending=False)
    c = table(['Days out', 'State results inside the range', 'Width, points', 'National result inside its range, of 5'], [[int(d), f'{r.cover:.0%}', f'{r.width:.1f}', int(r.nat)] for d, r in R.iterrows()])
    return a, b, c


def keys_tables():
    K = json.load(open('data/keys_study.json')); D = [str(d) for d in K['days']]
    ways = [('published', 'Published'), ('hybrid', 'Hybrid: Keys as an equal part'), ('half', 'Keys at half weight'), ('recent line', 'Keys line fitted on the last ten elections'), ('no keys', '**No Keys (recommended)**'), ('as a signal', 'No Keys in the vote; the count used as a sign of the winner')]
    avg = lambda w, f: float(np.mean([K['ways'][w][d][f] for d in D]))
    a = table(['Mean over ten distances, 250 days to the last day', 'National miss', 'Of which toward the Democrats', 'State miss', 'Chance given to the winner', 'Brier score, winner', 'Log loss, winner', 'Favored the winner (of 5), fewest'],
              [[label, f"{avg(w, 'national'):.2f}", f"{avg(w, 'signed'):+.2f}", f"{avg(w, 'state'):.2f}", f"{avg(w, 'p_winner'):.0%}", f"{avg(w, 'brier'):.3f}", f"{avg(w, 'log_loss'):.3f}", min(K['ways'][w][d]['favored'] for d in D)] for w, label in ways])
    b = table(['National miss', *(('last day' if d == '1' else d + ' days') for d in D)], [[label] + [f"{K['ways'][w][d]['national']:.2f}" for d in D] for w, label in ways[:5]])
    c = table(['Log loss for the winner', *(('last day' if d == '1' else d + ' days') for d in D)], [[label] + [f"{K['ways'][w][d]['log_loss']:.2f}" for d in D] for w, label in ways])
    parts = table(['Each part alone, miss on the national margin', '2008', '2012', '2016', '2020', '2024', 'Typical size', 'Mean, toward the Democrats'],
                  [[k[0].upper() + k[1:]] + [f"{v['by_year'][y]:+.1f}" for y in ('2008', '2012', '2016', '2020', '2024')] + [f"{v['size']:.1f}", f"{v['signed']:+.1f}"] for k, v in K['parts'].items()])
    sig = table(['Election', 'Count', 'The count called', 'Right?', 'Its record before, as used'], [[y, f"{K['count_alone']['since_2008'][y]['count']:.0%}", 'Democrats' if v['calls_democrats'] else 'Republicans', 'yes' if v['call_was_right'] else 'no', f"{v['record_used']:.0%}"] for y, v in K['signal'].items()])
    return a, b, c, parts, sig, K


def intervals():
    J = json.load(open('data/interval_study.json')); p0 = lambda x: f'{100 * x:.0f}%'
    days = sorted(J['states_by_days'], key=lambda d: -int(d))
    a = table(['Days out', '50% interval held', '80% held', '90% held', '95% held', 'Width of the 80% interval', 'Interval score', 'Missed on the Republican side', 'On the Democratic side'],
              [['last day' if d == '1' else d, p0(v['cover50']), p0(v['cover80']), p0(v['cover90']), p0(v['cover95']), v['width80'], v['wis'], p0(v['more_republican_than_80']), p0(v['more_democratic_than_80'])] for d in days for v in [J['states_by_days'][d]]])
    b = table(['Way of sizing a state\'s error', 'Interval score', 'Better than the earlier sizing in', '50% held', '80% held', '95% held', 'Width of the 80%', '80% held, by election, last day', 'Narrowest and widest state'],
              [[k[0].upper() + k[1:], v['wis'], f"{v['better_than_the_earlier_sizing_in']} of 5", p0(v['cover50']), p0(v['cover80']), p0(v['cover95']), v['width80'], ', '.join(p0(x) for x in v['last_day']['cover80_by_year'].values()), ' to '.join(str(x) for x in v['last_day']['narrowest_and_widest_state'])] for k, v in J['variants'].items()])
    h = J['alternatives']['held_out']
    c = table(['Left out', 'National error scaled by', 'State error scaled by', 'Interval score', 'As published', '80% held', 'As published', '95% held', 'As published'],
              [[y, v['national_scale'], v['state_scale'], v['wis'], v['wis_as_published'], p0(v['cover80']), p0(v['cover80_as_published']), p0(v['cover95']), p0(v['cover95_as_published'])] for y, v in h.items()])
    return a, b, c, J


def market_tables():
    S = json.load(open('data/market_study.json')); K = FC.get('markets') or {}
    a = table(['2024, mean over nine distances', 'Log loss', 'Brier score', 'States called', 'Chance given to the winner', 'Better than the forecast at'],
              [[k[0].upper() + k[1:], f"{v['log_loss']:.3f}", f"{v['brier']:.3f}", f"{v['called']:.1f}", '' if v['winner_of_the_electoral_college'] is None else f"{100 * v['winner_of_the_electoral_college']:.0f}%", '' if k == 'the forecast alone' else f"{v['better_log_loss_than_the_forecast_at']} of {v['of']}"] for k, v in S['mean_over_days'].items()])
    us = (K.get('places') or {}).get('US') or {}; inf = K.get('informed') or {}
    rows = [['Official forecast', f"{100 * FC['p_dem']:.1f}%", 'no markets']] + [[p['provider'], f"{100 * p['p']:.1f}%", ('$' + format(int(p['volume']), ',') + ' traded') if p.get('real_money') and p.get('volume') else (str(p.get('traders')) + ' traders, play money')] for p in us.get('providers') or []]
    if us.get('p') is not None: rows.append(['Markets together, by quality', f"{100 * us['p']:.1f}%", ''])
    if inf: rows.append(['Market-informed run (experimental)', f"{100 * inf['p_dem']:.1f}%", f"{inf['events']} prices; {100 * inf['effective']:.0f}% of the simulated elections effectively kept"])
    for k, v in (K.get('other_ways') or {}).items(): rows.append(['Market-informed, ' + k, f"{100 * v['p_dem']:.1f}%", f"{v['events']} prices"])
    b = table(['Democrats win, ' + str(K.get('read', '')), '', ''], rows)
    return a, b, S, K


def main():
    a, b, c = ranges(); ka, kb, kc, kparts, ksig, K = keys_tables(); ns = FC['national_from_states']; I = FC['inputs']
    tf, tfr = texas_florida(); ta, tb, T = trend_study(); am, A = approval_moves()
    ia, ib, ic, IV = intervals(); ma, mb, MS, MK = market_tables(); MC = json.load(open('data/method_change.json')); P = MC['parts']; P2 = MC['second_change']['parts']
    S = M.SET; pct = lambda v: f"{v:.0f}%"; two = IV['two_years_out']; pts = lambda v: f"{100 * v:+.1f}"
    places = (MK.get('places') or {}); priced = sum(1 for k, v in places.items() if k != 'US' and v.get('p') is not None)
    L = f"""# The three sites: the method as frozen, the evidence, and what runs by itself

Written by `status.py` on the forecast of {FC['as_of']}. Every figure in a table is read from a data file; misses are in
points of margin. `RUNBOOK.md` says how the sites are kept running. `REVIEW.md` holds the earlier research.

## 1. The official method

The Margin's forecast is made in this order. It gives no weight to Fifty-Two Keys or to prediction markets.

1. **A national starting point, before polls.** The average of the approval equation (net approval in June of the election
   year, growth, and time in office, fitted on 1948 to the election before), today {mgn(I['approval_model'])}, and Tipping Point's
   approval-and-economy model, today {mgn(I['approval_and_economy'])}. Tipping Point's long-range model joins from November 7, 2027, when the
   polls it is built on exist. Together today: {mgn(I['fundamentals'])}.
2. **An allowance for approval still moving: 15 points of net approval** at the midterm, shrinking with the square root of
   the time left, closing only when The Margin itself finds ten June 2028 days in the Nowcast's approval series. It counts
   by the structural models' share of the national number, so it is not added to the part polls already carry. Today {100 * FC['approval_open']:.0f}%
   of it is open.
3. **National polls, by the calendar:** what the record says polls at this distance have been worth. Today {100 * I['poll_share']:.0f}%, on {I['polls_n']}
   polls ({mgn(I['national_polls'])}). The national number is {mgn(FC['national'])}.
4. **The states.** The national number plus where each state sits against the nation: half its lean in the last two elections,
   half where Tipping Point's two models place it. State polls move it by a share that grows with their number and the calendar.
5. **Each state's own error,** sized from how far that state has landed from its starting point in the last five elections,
   pulled toward the common size as if by four more elections. Small and lopsided states get wider intervals than large,
   close ones.
6. **{S['sims']:,} simulated elections,** with one national error, a regional one and each state's own. Everything shown is
   counted from the same simulated elections: who wins, the electoral votes, each state's 80% prediction interval, the
   national vote, and the chance of winning the vote and losing the Electoral College.

| 2028, as of {FC['as_of']} | |
|---|---|
| Democrats win the Electoral College | {100 * FC['p_dem']:.1f}% |
| Republicans win | {100 * FC['p_rep']:.1f}% |
| A 269 to 269 tie, counted for neither | {100 * FC['p_tie']:.1f}% |
| National vote, from the simulated elections | {mgn(ns['mean'])}; 80% prediction interval {mgn(ns['hi'])} to {mgn(ns['lo'])} |
| Democrats win the most votes | {100 * FC['p_popular']:.0f}% |
| Democratic electoral votes | {FC['ev_median']:.0f}; 80% prediction interval {FC['ev_lo']:.0f} to {FC['ev_hi']:.0f} |
| The national number less the states added up | {ns['gap']:+.2f} points |

**Where the change of November 25 came from** (`method_change.py`). The Democratic chance went from {100 * MC['before']:.1f}% to {100 * MC['after']:.1f}% that day.
Nothing had happened in the race. Run on the day's inputs with each change of method switched on and off in every combination,
on the same random draws, and each credited with its average effect over every order:

| Change | Points of Democratic chance |
|---|---|
| State models used for where they place each state, not for their forecast as it stands | {pts(P['centring'])} |
| Early polls counted for 3%, not 24% | {pts(P['polls'])} |
| Fifty-Two Keys taken out | {pts(P['Keys'])} |
| The approval-and-economy model added | {pts(P['Enns'])} |
| **Together** | **{pts(MC['change'])}** |
| Later the same day: the approval allowance from 10 to 15, counted by the structural share | {pts(P2['allowance'])} |
| Later the same day: each state's error sized on its own recent record | {pts(P2['state error'])} |

The two ends of the first block are the forecasts kept that day ({', '.join(f'{100 * v:.1f}%' for v in MC['kept_that_day'].values())}). The largest part is not the one the
change was known for: Tipping Point's models carry their own, lower, national level, and using them only for where they
place each state removed that pull on every state at once. The headline had also been taken off betting markets earlier
that day (62% to 60%); that was a change to what was shown and is not split here. Every kept forecast is untouched in
`docs/archive/`; the first one under the new method is labelled "a new day" where it should read "the method", and
`docs/archive/notes.json` carries that correction without touching the forecast.

## 2. The evidence for the method

The official method against the one before it, on 2008 to 2024 (`backtest.py`):

{backtests()}

Why Fifty-Two Keys is out (`keys_study.py`, ten distances from 250 days to the last day):

{ka}

Five elections; ten distances from one election are not ten elections. The approval-and-economy model's forecast is the one
its authors' method gives about 100 days out, used at every distance, which flatters the early distances.

## 3. Prediction markets: read, kept, shown, not weighted

**What was built** (`markets.py`). Every check finds each provider's open markets on 2028 by searching and by the pattern of
their names: the national winner by party, every state, the District, the districts of Maine and Nebraska, the popular vote,
and the markets on margins, electoral votes and nominations. Nothing is listed by hand, and a market that opens next year
is picked up the day it opens. Each market is scored from 0 to 1 on how much is staked, how recently it traded and how
tight its prices are; play money is scored on traders, not volume, and counts for half. For each place the best market of
each provider is averaged by quality, different providers for different states as their markets warrant. Exchanges trade
on the same news, so together they count for the best of them and a quarter of the rest, never the sum; Election Betting
Odds, an average of the same exchanges, is shown on its own line and not counted again. Two real-money exchanges more than
25 points apart on one question are not averaged. Prices go into `docs/markets/` whenever they move; the record began on
November 26, 2026 (UTC). A move in the markets alone refreshes the comparison and does not make a new official forecast.

Read {MK.get('read')}: {', '.join(f'{k} {v}' for k, v in (MK.get('counts') or {}).items())} markets; {priced} of the 56 states and districts priced.

{mb}

**The experimental run** (`markets.informed`). It never moves a headline. It weights the official simulated elections so
that each priced event's chance moves toward the market's by half the market's quality on the log-odds scale; a thin market
moves next to nothing. Whole elections are weighted, so the chance of winning, ties, each state, the electoral votes, the
national vote and its interval stay consistent. If fewer than a quarter of the elections would effectively remain, every
pull is halved. A winning chance does not fix a margin: nothing is said about any margin except through which simulated
elections count for more.

**What history can say** (`market_study.py`). State markets with a readable price history exist for one election, 2024.
On the states Polymarket priced, at nine distances from 200 days to the last day:

{ma}

The forecast scored better than the markets on the whole and the markets better in the last two weeks; every way of mixing
them in landed between and was better than the forecast at 3 of 9 distances. That is one election, in which the states
shared one national miss, and the forecast's early figures are flattered by final data. Not checkable at all: any earlier
election at state level, any distance beyond about 250 days, and the quality rule itself (the record gives each market's
final volume, not its volume on the day).

**Recommendation: no weight.** The evidence does not show markets adding to the forecast, and could not show it either
way. The official forecast stays statistical. The market-informed run is made beside it on every forecast and kept, so by
November 2028 there is a record to judge on. The largest disagreement today is Texas: markets {100 * (places.get('TX') or {}).get('p', 0):.0f}%, forecast {100 * next(x['p_dem'] for x in FC['states'] if x['state'] == 'TX'):.0f}%.

## 4. Prediction intervals

**What was found** (`interval_study.py`; states, 2008 to 2024, as the method now stands):

{ia}

The intervals hold more than they claim: the 80% interval held {100 * IV['states_by_days']['1']['cover80']:.0f}% of state results on the last day and more further out.
The national vote fell inside its 80% interval every time and the electoral votes in {100 * IV['EV']['all']['cover80']:.0f}% of cases. Misses fall on the
Republican side far more often than the Democratic: the polls' miss of 2016, 2020 and 2024.

**The parts, and whether any is counted twice.**

| Part | Size, and what was checked |
|---|---|
| National error | The error a mix of polls and structural models has made at each distance since 1976. On the last day about 3.4 points of margin against a realized 2.0 over five elections; five values cannot tell 2.0 from 3.4 |
| Approval still moving | 15 points of net approval, which is {2 * I['fundamentals_sd']:.1f} points of margin today. Counted by the structural share, so it does not sit on top of the drift the polls' own error already holds. The record's structural error is measured with June approval known, so the allowance is not in it twice |
| Two years out, checked independently | The approval equation run with the midterm's approval in place of June's missed by {two['miss_with_midterm_approval']} points over {two['elections']} elections and {two['since_2000']['miss_with_midterm_approval']} since 2000; approval moving accounts for {two['from_approval_moving']} and {two['since_2000']['from_approval_moving']}. The forecast allows about 6.4 in all and {2 * I['fundamentals_sd']:.1f} for approval: in line with the record since 2000, well under the longer one |
| Economic and candidate uncertainty | Not separate terms. They are inside the record's error for the structural models; candidates enter through the spread between poll pairings, which lowers the polls' weight and adds no width |
| State polls | Each state's poll error is measured against the national average, so the national miss is not in it twice |
| Regional error | 40% of each state's own error is shared with its region; it changes how states move together, not how wide one state's interval is |
| State's own error | Was one size for all, measured since 1980. Now each state's own, from the last five elections (below) |
| Model disagreement | The two structural models are averaged; their gap is not added as width |
| Prediction markets | Not in the forecast |

**The one thing that was too wide, and is changed.** A state's error was sized on every election since 1980 with one figure
for all states. States moved about more then than since 2000, and some states are steadily harder to place than others
(small and lopsided ones miss by about 7.4 points, large and close ones by about 5.4; a state's size of miss in one half
of the record predicts its size in the other, correlation {IV['by_state']['first_half_against_second']}). Eight ways of sizing it were written down and run
through the whole simulation, each using only earlier elections:

{ib}

Sizing each state on its own recent record, pulled toward the common size, scored better in all five elections and is
adopted. Intervals are about 7% narrower on average, and no longer the same for every state.

**Why not narrower still.** Scaling the national and state errors down, choosing the scales on four elections and scoring
on the fifth, brings average coverage to the nominal 80% and improves the score in four elections:

{ic}

and in the fifth, 2016, the 80% intervals would have held {100 * IV['alternatives']['held_out']['2016']['cover80']:.0f}% and the 95% intervals {100 * IV['alternatives']['held_out']['2016']['cover95']:.0f}%. Every held-out choice
also put the national scale at the lowest value on offer, which says the five national misses were small, not that the
next one will be. Fifty states share an election's national miss, so this is five tests, and one of the five says the
width was needed. The remaining over-coverage is left in. That is a judgment between two risks and is stated as one.

**Cannot be validated yet:** anything about intervals more than 250 days out for states (the back-test has no polls that
early and runs the structural models on final figures), and the shape of the allowance's shrinking between now and June 2028.

## 5. The states: Texas, Florida, and whether trends or midterms would help

Closed, and not reopened. The framework is kept: no rule for a state's lean beat the one in use by more than chance would,
trends do not persist (correlation {T['persistence']['correlation']:+.2f} between a state's move in one election and the next), and midterm House results
did not help. `state_trend_study.py` and `data/state_trend_study.json` hold the study.

{tf}

## 6. Running by itself

Each site checks its sources every hour, stops if nothing is new, and otherwise recalculates, archives and publishes. A new
official forecast is made only for what the forecast reads; a move in prediction markets alone refreshes the comparison.

| Seen in production, November 25 and 26, 2026 (UTC) | |
|---|---|
| A run started by GitHub's own schedule | The Margin, November 26, 01:56. The first since the hourly schedules went in eight hours earlier: the schedule works, late |
| Tipping Point and Fifty-Two Keys notify The Margin; it runs within a minute | 19:01, 21:48, 22:29, 23:06 |
| A check asked for the way the outside clock will ask | all three sites, 23:12 to 23:40: each found nothing new and saved nothing |
| Prediction markets read at three providers, kept, and shown | November 26, 02:42: Polymarket 51, Kalshi 61, Manifold 61 markets; all 56 places priced |
| The nomination reader on the live pages of 2016, 2020 and 2024 | November 26, 02:45: the locked table's answers for all three; 2028: "not yet" for all four keys |
| Second sources answering | Bureau of Labor Statistics, University of Michigan, Energy Information Administration, share prices: the same figures as FRED. Department of Labor: within its tolerance after a fix. The Federal Reserve Board's table did not match FRED's industrial production and is not used |
| The official method published and kept | `docs/archive/`, with the settings of each forecast |

[ops.html](https://ka82205.github.io/the-margin/ops.html) reads GitHub's record live. For each site: the last good check, the last saved update, the last run GitHub's
schedule started, the last run the outside clock or a heartbeat started, the last deployment of the public site, failures,
and whether a check is overdue. For The Margin also the last official forecast kept, the last reading of the markets, the last
notification from a sister site, and what was read from each source. A request that was accepted is not counted as an
update: the page reads runs, commits and deployments, each on its own.

The outside clock (`RUNBOOK.md`) is yours to set up: one token that can only start runs, three jobs. It is the fallback for
hours when GitHub's schedule is late, and costs only checks that find nothing new.

## 7. What is done by hand

**Routine entry of data: none.** All 52 keys are read or worked out by rule; the nominees are read; polls, approval, the
economy, the forecasters' outlook, seats in Congress and prediction markets are read; odds are counted from the record.

**Left to a person, because they are exceptions and not routine:**

| What | When it would arise | What happens until then |
|---|---|---|
| The two sources for a nomination key disagree, or cannot be read by the close | Only if The Green Papers and Wikipedia differ on a nominee, a winner, a share or the side of two-thirds | The key stays open with the reason; never counted as no. An entry by hand settles it and is compared with the sources |
| A large, real move in industrial production or housing starts | A shock in one of the two series with no second source | The run fails once a day and names the series; `trust` lets it in after a look. Every other series is confirmed automatically |
| A forecast published by the authors of Tipping Point's models | If one appears. Crossref is searched daily and the run says so when one does | The site runs its own reading of the method. Putting a published table in is one command; it is not automatic because a table in an article cannot be read safely unseen |
| State approval for Tipping Point | Civiqs refuses automatic reads, its rules file included. No other open source covers fifty states, and estimating it would change an academic model | The last validated figures are used and dated on the page; each run asks again and takes a new copy if one is given |
| Tokens | The outside clock's token, if given an expiry | GitHub e-mails before it lapses; the sites' own schedules and notifications carry on |
| A change to a frozen method | A fault, a source that dies, or new evidence | Recorded in `data/methods.json` |

## 8. Limits that cannot be removed

- **Five elections.** Every back-test rests on 2008 to 2024. The choices made rest on differences that pointed one way in
  every election; differences that did not were left alone.
- **Back-tests are not real time.** They use final economic figures and one forecast a year from the approval-and-economy
  model. Old vintages of every series and poll lists as they stood each day are not available free in one place.
- **No nominees.** Every 2028 poll pairs people who may never face each other. Polls count for {100 * I['poll_share']:.0f}% of the national number.
- **Markets are thin.** Most state markets have a few thousand dollars or a few dozen traders in them. They are scored for
  it, and the scoring rule is a stated judgment with no record to test it on.
- **The 2028 nomination pages do not exist with results in them yet.** The reader gives the right answers for 2016, 2020 and
  2024 on today's live pages. That it will on 2028's cannot be shown before 2028. If a page changes shape the key stays open
  and says why.
- **Third parties.** GitHub decides when schedules run. PollResults.org, VoteHub, FRED, the Philadelphia Fed, the statistical
  agencies, Wikipedia, The Green Papers, Polymarket, Kalshi, Manifold and Crossref can change or close. Each has a check that
  reports when it stops answering and a last good copy to fall back on; none has a contract.
- **Accessibility was checked by program.** All three sites pass the WCAG 2 A and AA rules a program can test, in light
  and dark, at desktop and phone widths. Nobody has gone through them with a screen reader.

## 9. Frozen

From November 26, 2026 the method is not changed before the election except to fix a fault, replace a source that has
died, or act on evidence strong enough to be written up here first. A change is recorded in `data/methods.json` with what
it changed. Data, polls and the calendar move the forecast; the code that turns them into a forecast does not. Congress is
not forecast.
"""
    open('STATUS.md', 'w').write(L); print('STATUS.md', len(L), 'characters')


if __name__ == '__main__':
    main()
