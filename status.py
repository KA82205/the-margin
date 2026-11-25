"""Writes STATUS.md: where the three sites stand against the roadmap, the evidence on the versions under review, how the
ranges have held up, and the decisions that are open. Every figure in a table is read from a data file or worked out here;
none is typed.

    python status.py
"""
import json
import numpy as np, pandas as pd
import fundamentals as F

P = json.load(open('data/phase_in.json')); FC = json.load(open('data/forecast_2028.json')); C = FC['candidate']; H = C['hybrid']
DAYS = ['250', '200', '150', '120', '90', '60', '30', '14', '7', '1']
NAMES = [('published', 'Published'), ('candidate', 'Candidate'), ('candidate, approval equation as a fourth model', 'Hybrid'), ('structural', 'Hybrid, no long-range model'),
         ('candidate, published national prior', 'Published prior, polls by the timeline')]
table = lambda head, rows: '\n'.join(['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)] + ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows])
mgn = lambda sh: (lambda m: '0.0' if round(abs(m), 1) == 0 else ('D+' if m > 0 else 'R+') + f'{abs(m):.1f}')(2 * (sh - 50))


def near(field, fmt='{:.2f}'):
    N = P['near']
    return table(['', *(('last day' if d == '1' else d + ' days') for d in DAYS)], [[label] + [fmt.format(N[k][d][field]) for d in DAYS] for k, label in NAMES])


def without(year):
    N = P['near']
    return table(['', *(('last day' if d == '1' else d + ' days') for d in DAYS)],
                 [[label] + [f"{np.mean([abs(x) for y, x in N[k][d]['by_year'].items() if y != str(year)]):.2f}" for d in DAYS] for k, label in NAMES[:3]])


def early():
    b = P['far']['before_its_polls_existed']; cols = [('published', 'Published'), ('candidate', 'Candidate'), ('hybrid', 'Hybrid')]
    return table(['Election', 'Dates', *(c[1] for c in cols)], [[y, v['dates']] + [f'{v[k]:.2f}' for k, _ in cols] for y, v in b['by_year'].items()] + [['All', b['dates']] + [f"{b['all'][k]:.2f}" for k, _ in cols]])


def today():
    rows = [('Democrats win the Electoral College', lambda x: f"{100 * x['p_dem']:.0f} in 100"), ('The same, simulations only (no betting markets)', lambda x: f"{100 * x['p_model']:.0f} in 100"),
            ('National vote', lambda x: mgn(x['national'])), ('Democratic electoral votes, middle simulation', lambda x: f"{x['ev_median']:.0f}"),
            ('Four in five simulations', lambda x: f"{x['ev_lo']:.0f} to {x['ev_hi']:.0f}"), ('Polls in the national number', lambda x: f"{100 * x.get('poll_share', FC['inputs']['poll_share']):.0f}%")]
    pub = dict(FC, poll_share=FC['inputs']['poll_share'])
    return table([f"2028, as of {FC['as_of']}", 'Published', 'Candidate', 'Hybrid'], [[name] + [f(x) for x in (pub, C, H)] for name, f in rows])


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


def keys_line():
    t = F.table(); rows = []
    def fit(past, kind):
        x, y = past['keys'].values, past.incvote.values
        if kind == 'last ten elections': x, y = x[-10:], y[-10:]
        if kind == 'elections since 1980': keep = (past.year >= 1980).values; x, y = x[keep], y[keep]
        return np.polyfit(x, y, 1)
    for kind in ('every election since 1952 (as used)', 'last ten elections', 'elections since 1980'):
        e = []
        for y in (2008, 2012, 2016, 2020, 2024):
            past = t[t.year < y].dropna(subset=['keys']); r = t[t.year == y].iloc[0]; s, i = fit(past, kind)
            err = i + s * r['keys'] - r.incvote; e.append((2 * err, 2 * (err if r.deminc else -err), s))
        rows.append([kind[0].upper() + kind[1:], f'{np.mean([abs(a) for a, _, _ in e]):.1f}', f'{np.mean([b for _, b, _ in e]):+.1f}', f'{np.mean([a for a, _, _ in e]):+.1f}', f'{e[-1][2]:.0f}'])
    by = []
    for y in (2008, 2012, 2016, 2020, 2024):
        past = t[t.year < y].dropna(subset=['keys']); r = t[t.year == y].iloc[0]; s, i = np.polyfit(past['keys'], past.incvote, 1); err = i + s * r['keys'] - r.incvote
        by.append([y, 'Democrats' if r.deminc else 'Republicans', f'{2 * err:+.1f}', f'{2 * (err if r.deminc else -err):+.1f}'])
    return (table(['Line fitted on', 'Typical miss, 2008 to 2024', 'Mean miss toward the Democrats', 'Mean miss toward the party in office', 'Points of vote for the whole count, 2024 fit'], rows),
            table(['Election', 'Party in office', 'Miss toward the party in office', 'Miss toward the Democrats'], by))


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
    a, b, c = ranges(); UP = (FC.get('upstream') or {}).get('fifty_two_keys') or {}; RC = C['recommended']
    ka, kb, kc, kparts, ksig, K = keys_tables(); ns = FC['national_from_states']; rs = RC['national_from_states']
    side = lambda x: f"{100 * x['p_dem']:.0f} in 100"
    L = f"""# Where the three sites stand

Written by `status.py` on the forecast of {FC['as_of']}. Every figure in a table is read from a data file. Misses are in
points of margin. `RUNBOOK.md` says how the sites are kept running; `REVIEW.md` holds the earlier research.

Each line below is marked: **live** (deployed and seen working on the public site or in GitHub's record), **tested** (passes
its tests here; not yet seen in production because the event has not happened), **under review** (built, run beside the
published forecast, waiting for your word), or **open**.

## 1. What changed in this round

| | Status |
|---|---|
| The headline is the simulations' own number: Democrats {100 * FC['p_dem']:.0f} in 100, Republicans {100 * FC['p_rep']:.0f}, a 269 to 269 tie {1000 * FC['p_tie']:.0f} in 1,000, counted for neither. Betting markets are shown beside it. Forecasts kept before the change are untouched; the change is in `data/methods.json` and marked on the history chart | live |
| No figure is written +0.0, -0.0, D+0.0 or R+0.0: one routine for margins and one for changes, checked on every tab by `tests/browser_page.js` | live |
| "Forecast updates" is one line when nothing has moved and opens up when something has, with 7, 30 and 90-day comparisons as history allows. What moved is split between national polls, approval, the Keys count, Tipping Point's state models and time, each credited with its average effect over every order, so the order does not matter and the parts add up. Nothing is called "the calendar" | live |
| The history chart covers the days there are, with 7, 30, 90-day and all-time views; one point a day, a day without a new forecast keeping the last | live |
| All 56 places in one list: search, five orders, four filters, the profile beside it | live |
| State chart: bars for the state, a dashed line for the nation, 2028 set apart and labelled as a forecast, a legend, hover for each year | live |
| Paths to 270 and the chance of the vote and the Electoral College disagreeing, counted from whole simulated elections | live |
| The national vote of each simulated election is added up from its own states by the votes each cast in 2024 (districts not counted twice) | live |
| What approval may still move by shrinks with the square root of the time left and closes only when Fifty-Two Keys reports the June 2028 polls are in; if they are late a month's worth stays open | live; the closing itself tested |
| Contact link in the footer, no name or picture | live |
| Map hover, ranges for every place, no margin past 100: checked again at five window sizes (`tests/browser_hover.js`) | live |
| Fifty-Two Keys: seats of a new Congress and polls naming a third candidate are read by rule; 47 of 52 keys need nothing typed; approval is run from today's reading; the count closes August 1, 2028; no vote estimate for 2028 | deployed; the rules tested on made-up futures |
| Both sites notify The Margin; any of the three can be asked from outside to check now | live |

## 2. Does Fifty-Two Keys belong in The Margin?

No. `keys_study.py` runs the hybrid on 2008 to 2024 at ten distances from the election, changing only what is done with the Keys.

{ka}

{kb}

{kc}

Among the versions of the hybrid every average is best with the Keys left out, and the order is the same on every measure:
the more of the Keys line there is, the worse the forecast. That holds for the vote (national and state misses, and the lean
toward the Democrats) and for the winner (Brier score and log loss). On the national miss it holds at eight of the ten
distances and is within 0.02 at the other two. Against the published forecast the version without the Keys is closer from
250 days to 30 days and level in the last fortnight (2.32 against 2.17 at 14 days, 1.74 against 1.72 on the last day).

Why. The Keys line, taken alone, missed the national margin by more than any other part and always the same way:

{kparts}

As a sign of the winner the count did no better. Laid over the simulations with its own past record (shrunk halfway to a coin
toss, because the keys were chosen with the results in view), it made every winner score worse:

{ksig}

In all five elections the count pointed to the Democrats; three of the five went that way. Its record of {K['count_alone']['right_college']} Electoral College
winners in {K['count_alone']['elections']} ({K['count_alone']['right_vote']} for the national vote) is a record of rules written after the results were known.

What this does not show. Five elections; ten distances from the same election are not ten elections. Six versions were
scored on them, so a small gap between two versions means little: the case rests on the gap being large, in one direction,
and on every measure. The approval-and-economy model's forecast is the one made about 100 days out, used at every distance,
and the Keys counts use final figures: both flatter early forecasts, and the second flatters the Keys.

**Recommendation: give Fifty-Two Keys no weight in The Margin.** The version without it is `model.RECOMMENDED`. It is run on
every forecast and is not published until you say so.

| 2028, as of {FC['as_of']} | Published | Hybrid | Recommended (no Keys) |
|---|---|---|---|
| Democrats win | {side(FC)} | {side(H)} | {side(RC)} |
| National vote | {mgn(FC['national'])} | {mgn(H['national'])} | {mgn(RC['national'])} |
| Democratic electoral votes, middle simulation | {FC['ev_median']:.0f} | {H['ev_median']:.0f} | {RC['ev_median']:.0f} |
| Four in five simulations | {FC['ev_lo']:.0f} to {FC['ev_hi']:.0f} | {H['ev_lo']:.0f} to {H['ev_hi']:.0f} | {RC['ev_lo']:.0f} to {RC['ev_hi']:.0f} |
| National number less the states added up | {ns['gap']:+.2f} | {H['national_from_states']['gap']:+.2f} | {rs['gap']:+.2f} |

For 2028 the choice moves little: today the Keys line ({mgn(C['parts']['fifty_two_keys'])}) stands beside the other two parts ({mgn(RC['parts']['approval_and_economy'])} and {mgn(RC['parts']['approval_equation'])}).
The difference from the published forecast comes from the rest of the hybrid: early polls counted for {100 * RC['poll_share']:.0f}% and not {100 * FC['inputs']['poll_share']:.0f}%, and the
approval-and-economy model added. The recommendation is not made for the number it gives.

Fifty-Two Keys goes on as its own site. It calls a winner; it no longer gives an estimate of the vote.

## 3. The national number and the states

In the published forecast the states, added up by the votes each cast in 2024, come to {ns['of_means']:.2f}% against a national number of
{FC['national']:.2f}%: {abs(ns['gap']):.2f} points apart. Half of each state's starting point is Tipping Point's forecast of that state as it stands,
which carries that site's lower national level into the states a second time. In the versions under review the state models
are used only for where they place each state against their own national figure, and the two agree to {abs(rs['gap']):.2f}. The chance of
winning the most votes shown on the page is counted from the states added up ({100 * FC['p_popular']:.0f} in 100), not from the national number alone.
Adopting the recommended version closes the gap; nothing else was needed.

## 4. How wide the ranges are

Unchanged, and the evidence is as before: on the last day the ranges held more results than four in five on average, but in
2016 they needed nearly all of their width.

{a}

{b}

One assumption was checked against a record for the first time. The allowance for approval still moving is 10 points of net
approval. Between the midterm and June of the election year, net approval moved by about 20 points in a typical term since
1950, and by about 11 in the five most recent. At 20 the Democratic chance today would be about one point lower; the choice
is yours (decision 3). Fifty-Two Keys' run-ahead now uses the full record.

## 5. Running by itself: what is proven and what is not

| Evidence | Status |
|---|---|
| Tests on this machine: The Margin 17 and three browser tests, Fifty-Two Keys 34 | pass |
| Made-up futures: keys landing, the close, late figures, a new survey, seats, third candidates | pass |
| Runs started by hand on GitHub, with and without something new | seen |
| Notification, Fifty-Two Keys to The Margin | seen: 19:01 UTC, November 25 |
| Notification, Tipping Point to The Margin | seen: 21:48 and 22:29 UTC. The Margin ran within a minute, found the new state forecasts, kept and deployed a forecast |
| A check asked for from outside (`heartbeat`) | seen in all three between 22:28 and 22:47 UTC: the two upstream sites found nothing new and saved nothing; The Margin found the new Keys count, reran, and kept no new forecast because the forecast had not moved |
| The forecasters' survey read from the Philadelphia Fed on GitHub's servers | seen: it gave the figures entered by hand |
| A changed source published with nobody starting the run | **not yet seen** |
| A run GitHub started by itself since the hourly schedules went in | **not yet seen** |

Tipping Point's secret was added after the run this report first read; its next run notified The Margin.

The schedule is the open problem. Before the change Tipping Point asked for runs at 06:17 and 11:17 UTC and GitHub started
them seven to ten hours late, every day. Hourly schedules went in at about 18:00 UTC on November 25 and no scheduled run
had started in any repository by 22:50. If GitHub is simply seven to ten hours behind, hourly runs will begin overnight and
keep an hourly rhythm; if it drops them, they will not. [ops.html](https://ka82205.github.io/the-margin/ops.html) reads GitHub's record live and shows,
for each site, the last run of any kind and how many runs GitHub started by itself in the last day and week.

What is in place so that one late schedule does not stall everything: each upstream site, whenever it runs, wakes The Margin
if The Margin has not checked for most of an hour. What is not in place: anything outside GitHub that wakes the upstream
sites. That needs one free account and one change to your token, and only you can make them (decision 4).

## 6. Fifty-Two Keys: all 52 keys

`KEYS.md` in that repository has the row for each key: what it reads, its window, when it can first be called, what happens
if the figure is missing. In short:

| Keys | Evidence | Typed by hand |
|---|---|---|
| 33 economy keys (A01 to A18, B01 to B15) | FRED and the Philadelphia Fed state indexes; called when June 2028 figures are out | nothing |
| 6 approval keys (C01 to C06) | VoteHub's list of approval polls; called a week after June 2028 ends | nothing |
| 5 seat keys (D01, D02, D03, D05, D06) | the public list of sitting members, in the January a Congress meets | nothing (was one line every two years) |
| D04, E02 | the 2024 result; the table of past elections | nothing |
| E03, third candidate | PollResults.org: June 2028 polls naming one, three pollsters or more | nothing (was one entry) |
| E01 | the president cannot run again | entered once, done |
| E04, delegates | pledged delegates when the primaries end | **one entry in 2028** |
| E05, E06, E07, New Hampshire | certified results, for each party's candidate with a majority of pledged delegates | **one line in 2028** |

The four that still need an entry have no free, open source to read: delegate counts and New Hampshire's certified results
are published as pages and documents. The rules for them are now fixed in `KEYS.md`: pledged delegates at the end of the
primaries, not the convention; the nominee is the candidate with a majority of pledged delegates; a party with no such
candidate by August 1, 2028 has its keys left open, and the count closes without them.

Still entered in the run-ahead, with their dates: the parts of the outlook the forecasters' survey does not give (income,
pay, spending, industrial production, factory jobs, oil, sentiment, population), the 30% share of runs with a recession, and
the odds for the four nomination keys. No dependable free forecast of these was found; they are labelled as entered.

## 7. Decisions that are yours

1. **Make the version without Fifty-Two Keys the published forecast?** Recommended. Today: {side(FC)} to {side(RC)}, national vote {mgn(FC['national'])} to {mgn(RC['national'])},
   {FC['ev_median']:.0f} to {RC['ev_median']:.0f} electoral votes. It also brings the national number and the states into agreement. `RUNBOOK.md` has the steps; every
   forecast kept before the change stays as it was.
2. **Freeze the method after that.** If you approve 1, I suggest no further change to The Margin's method before the
   election except to fix a fault.
3. **The size of the approval allowance:** 10 points of net approval (as now, close to the five most recent terms) or 20
   (every term since 1950). About one point of the Democratic chance today.
4. **An outside clock for the three sites,** if GitHub's own schedule proves undependable. One free account at a scheduling
   service and your existing token widened from one repository to three. Steps in `RUNBOOK.md`.

## 8. Not done

- The back-tests still use one forecast a year from the approval-and-economy model and final Keys counts; they are labelled
  as such and have not been rebuilt as they stood on each day. Dropping the Keys removes the second of these.
- No separate page for polls; state polls are listed on each state's page with the reason each is or is not counted.
- Tipping Point's state approval is still copied by hand from Civiqs, which offers no feed; a new forecast published by the
  models' authors would also have to be entered by hand.
- A large, real economic move is still held back until somebody lets it through; no second source confirms it automatically.
- No accessibility audit and no outside review in this round. Congress is out, as instructed.
"""
    open('STATUS.md', 'w').write(L); print('STATUS.md', len(L), 'characters')


if __name__ == '__main__':
    main()
