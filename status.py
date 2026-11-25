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


def main():
    a, b, c = ranges(); ka, kb, kc, kparts, ksig, K = keys_tables(); ns = FC['national_from_states']; I = FC['inputs']
    tf, tfr = texas_florida(); ta, tb, T = trend_study(); am, A = approval_moves(); E = A['effect_on_the_forecast_of_2026-11-25']
    S = M.SET; one = lambda v: f"{v:.0f} in 100"
    L = f"""# The three sites: the method as frozen, the evidence, and what runs by itself

Written by `status.py` on the forecast of {FC['as_of']}. Every figure in a table is read from a data file; misses are in
points of margin. `RUNBOOK.md` says how the sites are kept running. `REVIEW.md` holds the earlier research.

## 1. The official method

The Margin's forecast is made in this order. Nothing in it reads Fifty-Two Keys or betting markets.

1. **A national starting point, before polls.** The average of two things, and of a third once it exists:
   the approval equation (net approval in June of the election year, growth, and time in office, fitted on 1948 to the
   election before), today {mgn(I['approval_model'])}; Tipping Point's approval-and-economy model, today {mgn(I['approval_and_economy'])}; and Tipping
   Point's long-range model, which is built on polls and so is left out until November 7, 2027 and then phased in, today
   {'not in' if not I['long_range_weight'] else mgn(I['long_range']) + f" at weight {I['long_range_weight']:.2f}"}. Together: {mgn(I['fundamentals'])}.
2. **An allowance for approval still moving.** Net approval is {I['net_approval']:+.1f} now and the equation wants its June 2028 value. The
   allowance is 10 points of net approval at the midterm, shrinks with the square root of the time left, and closes only when
   The Margin itself finds at least ten June 2028 days in the Nowcast's approval series (from July 8, 2028). If June is late,
   a month's worth stays open. Today {100 * FC['approval_open']:.0f}% of it is open.
3. **National polls, by the calendar.** Polls count for what the record says polls at this distance have been worth:
   about 3% two years out, 11% at 250 days, 24% at 120, 61% on the last day. Today {100 * I['poll_share']:.0f}%, on {I['polls_n']} polls ({mgn(I['national_polls'])}).
   The national number is {mgn(FC['national'])}.
4. **The states.** Each state starts from the national number plus where the state sits against the nation: half from its
   lean in the last two elections (three parts 2024, one part 2020), half from where Tipping Point's two models place it
   against their own national figure. State polls move it by a share that grows with their number and with the calendar.
5. **{S['sims']:,} simulated elections.** One national error for all states, a regional error shared by neighbours, and each
   state's own. Every figure on the page is counted from these same simulated elections: who wins, the electoral votes, each
   state's range, the national vote (each election's states added up by the votes they cast in 2024), and the chance of
   winning the vote and losing the Electoral College.

| 2028, as of {FC['as_of']} | |
|---|---|
| Democrats win the Electoral College | {one(100 * FC['p_dem'])} |
| Republicans win | {one(100 * FC['p_rep'])} |
| A 269 to 269 tie, counted for neither | {1000 * FC['p_tie']:.0f} in 1,000 |
| National vote, from the simulated elections | {mgn(ns['mean'])}; four in five between {mgn(ns['hi'])} and {mgn(ns['lo'])} |
| Democrats win the most votes | {one(100 * FC['p_popular'])} |
| Democratic electoral votes | {FC['ev_median']:.0f}; four in five between {FC['ev_lo']:.0f} and {FC['ev_hi']:.0f} |
| Win the vote, lose the Electoral College | Democrats {100 * ns['p_vote_not_college']:.0f} in 100, Republicans {100 * ns['p_college_not_vote']:.0f} in 100 |
| The national number less the states added up | {ns['gap']:+.2f} points |

The method was adopted on November 25, 2026 and is frozen from that day (section 9). On the day of the change the Democratic
chance moved from 60 to 70 in 100. Almost none of that comes from dropping Fifty-Two Keys' line: with the line left in,
the same method gives {100 * H['p_dem']:.0f} in 100 today. It comes from the rest of the approved change: early polls counted for 3% and not
24%, the approval-and-economy model added, and state models used for placing only. Every forecast kept before the change is untouched in `docs/archive/`; the change is recorded in
`data/methods.json` and marked on the page's history chart. The method before it stays in the code as `model.PREVIOUS`, and
four other versions are still run on every forecast and written to the data file, so that in 2028 they can be scored beside
the official one. They are not shown as the forecast.

## 2. The evidence for it

The official method against the one before it, on 2008 to 2024 (`backtest.py`):

{backtests()}

Why Fifty-Two Keys is out (`keys_study.py`, ten distances from 250 days to the last day):

{ka}

The more of the Keys line there is, the worse every measure gets. Taken alone the line missed the national margin by {K['parts']['keys line']['size']:.1f}
points on average, each time toward the Democrats. Used only as a sign of the winner it made every winner score worse.

What this does not show. Five elections; ten distances from one election are not ten elections. The approval-and-economy
model's forecast is the one its authors' method gives about 100 days out, used at every distance, which flatters the
early distances. The real test is 2028, which is why the method is frozen now.

## 3. The states: Texas, Florida, and whether trends or midterms would help

**Why Texas is projected more Republican than Florida.** They voted alike in 2024. Nothing was adjusted by hand; this is
what each part says.

{tf}

The gap of about two points has two sources. About a quarter of it is the lean: 2020 counts for a quarter, and in 2020
Florida was 2.3 points less Republican against the nation than Texas. The rest is Tipping Point's two models, which
together place Florida about three points less Republican than Texas: the approval-and-economy model by four, with approval
a point higher in Florida, and the long-range model by under three, because it leans on earlier elections, when Florida was
a swing state. There are no
2028 polls of either state. A rule that carried Florida's rightward move forward would bring the leans level (last line of
the table), not put Texas ahead.

**Would such a rule have forecast better?** `state_trend_study.py` scores eleven ways of setting a state's lean on every
state and every election on record, each using only what was known beforehand. A fitted share is fitted on earlier
elections only. Midterm leans come from the House vote in districts both parties contested, against the national House
vote counted the same way, so uncontested seats and the difference between midterm and presidential turnout drop out.
Senate and governor's races are left out: one race a state, decided as much by the candidates as by the state.

{ta}

{tb}

- **Trends do not persist.** A state's move against the nation in one election says almost nothing about its move in the
  next: the correlation is {T['persistence']['correlation']:+.2f} over {T['persistence']['n']} cases and {T['persistence']['since_2008']:+.2f} since 2008. The share of a trend that would have been best to
  carry forward is slightly negative in every election ({min(T['fitted_shares']['trend'].values()):+.2f} to {max(T['fitted_shares']['trend'].values()):+.2f}). Carrying a quarter forward was no better; a half was worse.
- **Midterms do not help.** Moving a fifth of the way to the midterm House lean was worse in 5 of 7 elections, and the best
  share to use was about zero ({T['fitted_shares']['midterm level']['2024']:+.2f}).
- **The last election alone** was closer than the rule in use in 6 of 11 elections, by 0.12 points with a standard error of
  0.15: not distinguishable from no difference. With the state models in, every rule lands between 3.89 and 3.96.

**Conclusion: the framework is kept as it is.** No rule beat the one in use by more than chance would, and the two that
would move Texas and Florida closer (trends, the last election alone) have no reliable record. The 2026 House vote is not in
the source file yet and was not used. Tipping Point's models are untouched.

## 4. The allowance for approval still moving

It stays at 10 points, as instructed. What the record says (`data/approval_moves.json`):

{am}

The "20" and "11" quoted before were root-mean-square changes: the spread about no change at all, for every term and for
the five most recent. That is the right measure here, because the forecast assumes no trend and the allowance is used as one
standard deviation. If the allowance is right, about two terms in three should fall within it. At 10, a third of all terms
do and three of the last five; at 20, two thirds of all terms and all of the last five.

**Recommendation: 15.** Ten is below every estimate in the table, including the one from the five most polarised terms
(11.2), and five terms cannot pin a spread down: the range that five observations with that spread are consistent with
runs from about 7 to about 27. Twenty fits the whole record but includes the swings of 1980 and 1992, larger than anything
since approval hardened along party lines. Fifteen sits between the five-term figure and the seven-term figure (16.3), and
at 15 the count of recent terms inside it is the same as at 10. This was written before measuring what it does to the
forecast. For the record, measured afterwards: Democrats {100 * E['10']['democrats_win']:.0f} in 100 at 10, {100 * E['15']['democrats_win']:.0f} at 15, {100 * E['20']['democrats_win']:.0f} at 20; the range of the national
margin {E['10']['range_of_the_national_margin']}, {E['15']['range_of_the_national_margin']} and {E['20']['range_of_the_national_margin']} points wide. The closing rule is the same at any size. The change is one number in
`data/inputs.json` (`approval_drift`) and a line in `data/methods.json`; it is yours to make.

## 5. How wide the ranges are

On the last day the ranges held more results than four in five on average, but in 2016 they needed nearly all their width.
They are left as they are.

{a}

{b}

## 6. Running by itself

Each site checks its sources every hour, stops if nothing is new, and otherwise recalculates, archives and publishes. Tipping
Point and Fifty-Two Keys tell The Margin when they publish. The Margin now starts a new forecast only for what its forecast
reads: national polls, state polls, approval, Tipping Point's models, a new day, or a change of method. A new Fifty-Two Keys
count or new betting odds is shown on the next forecast and does not start one; if either cannot be read the page says so and
nothing fails.

| Seen in production, November 25, 2026 (UTC) | |
|---|---|
| Fifty-Two Keys notifies The Margin | 19:01 |
| Tipping Point notifies The Margin; The Margin runs within a minute and publishes | 21:48, 22:29, 23:06 |
| A check asked for from outside, the way an outside clock would ask (`workflow_dispatch`, check only) | Tipping Point 23:12, Fifty-Two Keys 23:12, The Margin 23:40 (sent the exact message in `RUNBOOK.md`; GitHub answered 204). Each ran as "Check: outside clock", found nothing new and saved nothing |
| A `heartbeat` check | all three, 22:28 to 22:47 |
| The official method published and kept | 23:14, `docs/archive/2026-11-25T2314Z.json` |
| The forecasters' survey read from the Philadelphia Fed | gave the figures that had been typed |
| The Bureau of Labor Statistics read as a second source | 23:28: "gives the same 11 figures" for the unemployment rate |
| Polls naming a third candidate read from PollResults.org | every Fifty-Two Keys run |
| The operations page on the public site | read at 23:41: it listed the outside-clock runs, the last saved update and no failures for The Margin |
| **A run GitHub started by its own schedule since the hourly schedules went in** | **none in the first five and a half hours** |

GitHub's schedule is the weak point. A schedule is a request; GitHub started Tipping Point's old twice-daily runs seven to
ten hours late every day. Three things stand behind it: the notifications above; each upstream site waking The Margin when
it has been quiet for 50 minutes; and an outside clock, which needs one free account and one new token that only you can
make (`RUNBOOK.md`, about ten minutes). [ops.html](https://ka82205.github.io/the-margin/ops.html) reads GitHub's record live and shows for each site the last good
check, the last saved update, the last run GitHub's schedule started, the last run an outside clock or a heartbeat started,
what The Margin last read from each source, failures, and whether a check is overdue.

Tests: The Margin 17 and three browser tests; Fifty-Two Keys 36, including made-up futures in which keys land, the count
closes, figures arrive late, and the range narrows as months are published; Tipping Point's own. Each workflow runs its
tests before it reads anything.

## 7. What is still done by hand

| What | When | Why it is not automatic |
|---|---|---|
| The nominee's share of pledged delegates (Fifty-Two Keys E04) | Once, June 2028 | No open, stable list of pledged delegates exists. The best public tally carries no terms for reuse and the news agencies' counts are licensed |
| The New Hampshire primary line (E05 to E07) | Once, when both parties have a presumptive nominee | The Secretary of State publishes certified results as spreadsheets at an address that changes each cycle, with write-in votes in a separate file; the one open collection of results has New Hampshire's primary for 2020 only. The line also needs to know who the nominees are |
| Who the nominees are (Tipping Point's candidate file) | Once, when both are known | A fact, not a feed |
| State approval from Civiqs (Tipping Point) | When a new copy is taken | Civiqs turns automatic reads away. Only the gaps between states are used, and those move slowly. No other open source covers fifty states |
| A forecast published by the authors of Tipping Point's models | If one appears | It would replace the site's own reading of their method |
| A large, real move in a series with no second source (industrial production, spending, housing starts, sentiment, oil, shares, jobless claims, the quarterly accounts) | If it happens | The run fails once a day and names the series; it is let in with `trust` after a look |
| The size of the approval allowance | Your decision (section 4) | |

No longer by hand, as of this round: the odds for the nomination keys and the third-candidate key (counted from the record,
with the count shown); the parts of the outlook no survey gives (taken from the published figures); the share of runs with
a recession (the record's, falling as months run out); a large move in unemployment, payrolls, factory jobs, consumer prices
or hourly pay (confirmed against the Bureau of Labor Statistics); the June 2028 approval reading (found by The Margin
itself). A missed entry never becomes a "no": the key is held, the run fails once a day until it is entered, and if it is
still missing when the count closes on August 1, 2028 (late figures accepted to August 15) the key stays open, the count is
reported as a lowest and a highest, a winner is called only if both agree, and no group is re-weighted.

## 8. Limits that cannot be removed

- **Five elections.** Every back-test rests on 2008 to 2024. Differences of a few tenths of a point between methods mean
  nothing; the choices here rest on differences that were large and pointed one way on every measure.
- **Back-tests are not real time.** They use final economic figures and one forecast a year from the approval-and-economy
  model, not the figures as first published on each day. Old vintages for every series and old poll releases by date are
  not available free in one place. The page says so. Dropping Fifty-Two Keys removed the worst case of this (final key counts).
- **No nominees.** Every 2028 poll pairs people who may never face each other. Polls count for 3% of the national number.
- **State models place only.** Where Tipping Point's models put a state against the nation drives half of each state's
  starting point; if those placings are off (section 3), so are the states.
- **GitHub decides when schedules run,** and third parties decide whether their feeds stay open: PollResults.org, VoteHub,
  FRED, the Philadelphia Fed, the Bureau of Labor Statistics, the public list of members of Congress. Each has a check that
  reports when it stops answering; none has a contract.
- **The accessibility check was automatic.** All three sites pass the WCAG 2 A and AA rules a program can test, in light
  and dark, at desktop and phone widths (every tab of The Margin and its operations page; the opening view of the other
  two). Nobody has gone through them with a screen reader.

## 9. Frozen

From November 25, 2026 the method is not changed before the election except to fix a fault, and a fix is recorded in
`data/methods.json` with what it changed. Data, polls and the calendar move the forecast; the code that turns them into a
forecast does not. Open to you and outside the freeze: the approval allowance (section 4). Congress is not forecast.
"""
    open('STATUS.md', 'w').write(L); print('STATUS.md', len(L), 'characters')


if __name__ == '__main__':
    main()
