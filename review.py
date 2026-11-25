"""Writes REVIEW.md: the findings of the review of November 2026, with every figure read from the files the scripts wrote.

    python state_geography_check.py    data/state_geography.json
    python backtest.py                 data/backtest.csv
    python backtest.py candidate       data/backtest_candidate.csv
    python validate_phase_in.py        data/phase_in.json
    python review.py                   REVIEW.md

Nothing here changes the forecast. Misses are in points of margin (twice the points of vote share the scripts work in).
"""
import json
import numpy as np, pandas as pd
import model as M, fundamentals as F, backtest as B, timeline as T

G = json.load(open('data/state_geography.json')); PH = json.load(open('data/phase_in.json')); SP = json.load(open('data/state_polls.json'))
FC = json.load(open('data/forecast_2028.json')); C = FC['candidate']
BT = pd.read_csv('data/backtest.csv'); BC = pd.read_csv('data/backtest_candidate.csv')
YEARS = [str(y) for y in B.YEARS]


def table(head, rows, right=None):
    right = right if right is not None else range(1, len(head))
    line = lambda cells: '| ' + ' | '.join(str(c) for c in cells) + ' |'
    return '\n'.join([line(head), '|' + '|'.join('---:' if i in right else '---' for i in range(len(head))) + '|'] + [line(r) for r in rows])


f2 = lambda x: f'{x:.2f}'; f1 = lambda x: f'{x:.1f}'; sg = lambda x: f'{x:+.2f}'; pc = lambda x: f'{100 * x:.0f}%'
mg = lambda share: 'Even' if abs(share - 50) < 0.025 else ('D+' if share > 50 else 'R+') + f'{abs(2 * (share - 50)):.1f}'

NAMES = [('lean', 'The lean alone (this forecast\'s own rule)'), ('enns absolute', 'Approval model, as it stands'), ('combined absolute', 'Combined model, as it stands'),
         ('desart absolute', 'Long-range model, as it stands'), ('enns centred', 'Approval model, centred'), ('combined centred', 'Combined model, centred'),
         ('desart centred', 'Long-range model, centred'), ('enns centred 50% + lean', 'Half lean, half approval model centred'),
         ('combined centred 50% + lean', 'Half lean, half combined model centred'), ('enns absolute 50% + lean', 'Half lean, half approval model as it stands'),
         ('combined absolute 50% + lean', 'Half lean, half combined model as it stands (the published setting)')]
SETS = [('all', 'All 51'), ('close', 'Decided by under 10 points'), ('closer', 'Decided by under 5'), ('close_before', 'Under 10 points last time'), ('battle', 'The seven of 2024')]


def geography():
    O, A = G['oracle'], G['available']; out = []
    n = {s: sum(G['n'][s].values()) for s, _ in SETS}
    out.append(table(['Actual national result given (oracle)'] + [f'{label} ({n[s]})' for s, label in SETS], [[label] + [f2(O[s][k]['miss']) for s, _ in SETS] for k, label in NAMES]))
    out.append(table(['All 51 states, oracle'] + YEARS + ['Mean'] + [f'Without {y}' for y in YEARS], [[label] + [f2(O['all'][k]['by_year'][y]) for y in YEARS] + [f2(O['all'][k]['miss'])] + [f2(O['all'][k]['without'][y]) for y in YEARS] for k, label in NAMES]))
    out.append(table(['Decided by under 10 points, oracle'] + YEARS + ['Mean'] + [f'Without {y}' for y in YEARS], [[label] + [f2(O['close'][k]['by_year'][y]) for y in YEARS] + [f2(O['close'][k]['miss'])] + [f2(O['close'][k]['without'][y]) for y in YEARS] for k, label in NAMES]))
    vs = lambda t, k: f"{t[k]['vs_lean']['mean']:+.2f} ({t[k]['vs_lean']['se']:.2f}), {t[k]['vs_lean']['better_in']} of 5"
    out.append(table(['Against the lean alone: mean difference (standard error), elections better in', 'All 51, oracle', 'Under 10 points, oracle', 'All 51, 120 days out', 'All 51, last day'],
                     [[label, vs(O['all'], k), vs(O['close'], k), vs(A['120']['all'], k), vs(A['1']['all'], k)] for k, label in NAMES[1:]]))
    days = ['120', '60', '30', '1']
    out.append(table(['The national number this forecast held on the day (a real forecast)'] + [f'All 51, {d} days' for d in days] + [f'Under 10 points, {d} days' for d in days],
                     [[label] + [f2(A[d]['all'][k]['miss']) for d in days] + [f2(A[d]['close'][k]['miss']) for d in days] for k, label in NAMES]))
    sp = G['split']; lab = {'enns': 'Approval model', 'desart': 'Long-range model', 'combined': 'Combined'}
    out.append(table(['National miss of each model, and its miss on the states once that is taken out'] + YEARS, [[f'{lab[k]}: national'] + [sg(sp[k][y]['national']) for y in YEARS] for k in lab] +
                     [[f'{lab[k]}: states, centred'] + [f2(sp[k][y]['geography']) for y in YEARS] for k in lab] + [['The lean alone: states'] + [f2(O['all']['lean']['by_year'][y]) for y in YEARS]]))
    return out


def components():
    res, polls, errs = B.load(); t = F.table(); rows = {}
    for y in B.YEARS:
        fd, fsd, parts = F.forecast(y, t); _, two = B.state_models(y); act = float(res[res.year == y].nat2.iloc[0])
        b = BT[BT.year == y].set_index('days')
        rows[y] = {'Approval equation (published fundamentals, half)': parts['approval_model'] - act, 'Fifty-Two Keys line': parts['keys_model'] - act, 'Published fundamentals (the two averaged)': fd - act,
                   'Nowcast: approval and economy model': two['US'][0] - act, 'Nowcast: long-range model': two['US'][1] - act, 'Nowcast combined': (two['US'][0] + two['US'][1]) / 2 - act,
                   'Candidate prior (the two Nowcast models and the Keys line, a third each)': F.three_models(two['US'][0], two['US'][1], parts['keys_model']) - act,
                   'The same with the approval equation as a fourth': (two['US'][0] + two['US'][1] + parts['keys_model'] + parts['approval_model']) / 4 - act,
                   'National polling average, 120 days out': b.national_polls[120] - act, 'National polling average, last day': b.national_polls[1] - act}
    names = list(rows[2008]); rm = lambda k: float(np.sqrt(np.mean([(2 * rows[y][k]) ** 2 for y in B.YEARS])))
    kl = [2 * rows[y]['Fifty-Two Keys line'] for y in B.YEARS]; en = [rows[y]['Nowcast: approval and economy model'] for y in B.YEARS]; ds = [rows[y]['Nowcast: long-range model'] for y in B.YEARS]
    tab = table(['Forecast of the national margin less the result (+ = too Democratic)'] + YEARS + ['Typical size'], [[k] + [sg(2 * rows[y][k]) for y in B.YEARS] + [f2(rm(k))] for k in names])
    # the long record of the two equations, each fitted on earlier elections
    e1, e2 = [], []
    for y in t.year[(t.year >= 1976)]:
        f, a, k = F.one(t, y); act = float(t.incvote[t.year == y].iloc[0]); e1.append(2 * (a - act))
        if k is not None: e2.append(2 * (k - act))
    same = lambda a, b: int(sum(1 for x, z in zip(a, b) if x * z > 0))          # elections in which two forecasts missed on the same side
    ea, ee = [rows[y]['Approval equation (published fundamentals, half)'] for y in B.YEARS], [rows[y]['Nowcast: approval and economy model'] for y in B.YEARS]
    ed = [rows[y]['Nowcast: long-range model'] for y in B.YEARS]
    long = {'approval': float(np.sqrt(np.mean(np.square(e1)))), 'keys': float(np.sqrt(np.mean(np.square(e2)))), 'n': len(e1), 'n_keys': len(e2),
            'same_keys': same(e1[-len(e2):], e2), 'same_enns': same(ea, ee), 'same_long': same(ea, ed),
            'keys_dem': int(sum(1 for x in kl if x > 0)), 'keys_mean': float(np.mean(kl)), 'nowcast_opposite': 5 - same(en, ds), 'combined': rm('Nowcast combined'), 'prior': rm('Candidate prior (the two Nowcast models and the Keys line, a third each)')}
    return tab, long


def near_table(keys, names):
    d_all = ['250', '200', '150', '120', '90', '60', '30', '14', '7', '1']; N = PH['near']; out = []
    for field, title in (('national', 'National miss'), ('state', 'State miss'), ('called', 'States and districts called, of 280'), ('favored', 'Elections in which the winner was favored, of 5'), ('cover80', 'State results inside the 80% range')):
        fmt = (lambda v: pc(v)) if field == 'cover80' else (lambda v: f2(v) if isinstance(v, float) else str(v))
        out.append(table([title + ', by days before the election'] + d_all, [[names[k]] + [fmt(N[k][d][field]) for d in d_all] for k in keys]))
    return out


def main():
    geo = geography(); comp, long = components(); c28 = T.curves(2028); W = PH['weights']; far = PH['far']; fl = PH['flood']
    P, CN, AS, NR = 'published', 'candidate', 'candidate, state models as published', PH['near']
    by = lambda R, col, f=lambda x: x.mean(): {int(d): float(f(g[col])) for d, g in R.groupby('days')}
    pub_nat, cand_nat = by(BT, 'national_error', lambda x: 2 * x.abs().mean()), by(BC, 'national_error', lambda x: 2 * x.abs().mean())
    pub_st, cand_st = by(BT, 'state_mae', lambda x: 2 * x.mean()), by(BC, 'state_mae', lambda x: 2 * x.mean())
    last = BT[BT.days == 1]
    final = table(['Election', 'Favored on the last day', 'National margin: forecast, result', 'Democratic electoral votes: middle run, range, result', 'States and districts called'],
                  [[int(r.year), f"{'Democrats' if r.p_dem > 0.5 else 'Republicans'}, {round(100 * max(r.p_dem, 1 - r.p_dem))} in 100" + ('' if r.called else ' (missed)'), f'{mg(r.national)}, {mg(r.national_actual)}',
                    f'{int(r.ev_median)}, {int(r.ev_lo)} to {int(r.ev_hi)}, {int(r.ev_actual)}' + ('' if r.ev_lo <= r.ev_actual <= r.ev_hi else ' (outside)'), f'{int(r.states_called)} of {int(r.of)}'] for r in last.itertuples()], right=[])
    near_names = {'published': 'Published forecast', 'candidate': 'Candidate', 'candidate, polls by the published rule': 'Candidate, but polls weighed by the published rules',
                  'candidate, published national prior': 'Candidate, but the published fundamentals as the prior', 'candidate, state models as published': 'Candidate, but the state models as they stand (the published setting)',
                  'candidate, approval equation as a fourth model': 'Candidate, with the approval equation as a fourth model'}
    near = near_table(list(near_names), near_names)
    rec = c28['raw']; hs = [str(h) for h in T.H] if isinstance(next(iter(rec)), str) else T.H
    record = table(['Days before the election'] + [str(h) for h in T.H], [['Elections on record'] + [rec[h]['n'] for h in hs], ['Typical miss of the national polling average'] + [f1(2 * rec[h]['poll']) for h in hs],
                   ['Best weight on the polls against the fundamentals, in hindsight'] + [pc(rec[h]['best']) for h in hs], ['Weight given by the curve'] + [pc(float(M.curve(c28['national'], int(h)))) for h in hs]])
    rs = c28['raw_state']
    record_s = table(['Days before the election'] + [str(h) for h in T.H], [['State averages on record'] + [rs[h]['n'] for h in hs], ['Typical miss of a state polling average, against the nation'] + [f1(2 * rs[h]['poll']) for h in hs],
                     ['Typical miss of the lean'] + [f1(2 * rs[h]['lean']) for h in hs], ['Best weight on the state polls against the lean, in hindsight'] + [pc(rs[h]['best']) for h in hs], ['Ceiling given by the curve'] + [pc(float(M.curve(c28['state'], int(h)) / M.curve(c28['state'], 1))) for h in hs]])
    wd = ['1', '30', '60', '120', '200', '250', '365', '500', '715']
    weights = table(['Days before the election'] + wd, [['National polls: weight the record gives them'] + [pc(W['national'][d]) for d in wd], ['State polls: ceiling on their share of a state'] + [pc(W['state_ceiling'][d]) for d in wd]])
    cur = PH['curves']
    curves = table(['Forecast year', 'Elections behind the national curve', 'National: weight on the last day, days to half of it, power', 'State: the same'],
                   [[y, cur[y]['elections'], f"{pc(cur[y]['national'][0])}, {cur[y]['national'][1]}, {cur[y]['national'][2]}", f"{pc(cur[y]['state'][0])}, {cur[y]['state'][1]}, {cur[y]['state'][2]}"] for y in cur], right=[1])
    fr = far['rows']; cell = lambda r, k: f"{r[k]['miss']:+.1f} ({pc(r[k]['total'])})"
    far_tab = table(['Election, days out', 'Early polls alone', 'Published', 'Candidate (long-range model left out)', 'Long-range model in part', 'Long-range model in full', 'With hindsight'],
                    [[f"{r['year']}, {r['days']}" + ('' if r['long_range_live'] else ' *'), f"{r['polls']:+.1f}", cell(r, 'published'), cell(r, 'candidate'), cell(r, 'in_part'), cell(r, 'in_full'), cell(r, 'hindsight')] for r in fr])
    bf = far['before_its_polls_existed']; cols = ['published', 'candidate', 'in_part', 'in_full', 'hindsight']
    far_mean = table(['Mean size of the national miss before the long-range model\'s own polls existed', 'Published', 'Candidate (left out)', 'In part', 'In full', 'With hindsight'],
                     [[f"All {bf['dates']} dates"] + [f2(bf['all'][k]) for k in cols]] + [[f"{y} ({v['dates']} dates)"] + [f2(v[k]) for k in cols] for y, v in bf['by_year'].items()])
    st_rows = [r for r in fr if r['published_states']['n'] >= 5]
    far_states = table(['Election, days out', 'States with polls', 'Starting point alone', 'Early state polls alone', 'Published rule: miss (average share to polls, largest)', 'Candidate rule: miss (average share, largest)'],
                       [[f"{r['year']}, {r['days']}", r['published_states']['n'], f1(r['candidate_states']['start']), f1(r['published_states']['polls']),
                         f"{r['published_states']['blend']:.1f} ({pc(r['published_states']['share'])}, {pc(r['published_states']['max_share'])})", f"{r['candidate_states']['blend']:.1f} ({pc(r['candidate_states']['share'])}, {pc(r['candidate_states']['max_share'])})"] for r in st_rows])
    pm = lambda k: float(np.mean([r[f'{k}_states']['blend'] for r in st_rows]))
    flood = table(['Days before the election', 'Published rule: share to the ten polls, state moves by', 'Candidate rule', 'Candidate rule, nominees not known'],
                  [[r['days'], f"{pc(r['published']['share'])}, {r['published']['moved']:+.1f}", f"{pc(r['candidate']['share'])}, {r['candidate']['moved']:+.1f}", f"{pc(r['candidate']['share_unsure'])}, {r['candidate']['moved_unsure']:+.1f}"] for r in fl])
    f = SP['found']; O = G['oracle']; A = G['available']; ow = C.get('other_ways') or {}
    def pair(t, a='combined absolute 50% + lean', b='combined centred 50% + lean'):
        dd = np.array([t[a]['by_year'][y] - t[b]['by_year'][y] for y in YEARS])
        return f'{dd.mean():+.2f} ({dd.std(ddof=1) / np.sqrt(len(dd)):.2f}), {int((dd < 0).sum())} of 5'
    ways = ('long_range_in_part', 'long_range_in_full')
    side = table(['2028, as of ' + FC['as_of'], 'Published forecast', 'Candidate (long-range model left out for now)', 'Candidate, long-range model in part', 'Candidate, long-range model in full'],
                 [['Democrats win the Electoral College', pc(FC['p_dem']), pc(C['p_dem'])] + [pc(ow[k]['p_dem']) if k in ow else '' for k in ways],
                  ['National margin', mg(FC['national']), mg(C['national'])] + [mg(ow[k]['national']) if k in ow else '' for k in ways],
                  ['Democratic electoral votes, middle run', int(FC['ev_median']), int(C['ev_median'])] + [ow[k]['ev_median'] if k in ow else '' for k in ways],
                  ['How much of the national number moves with today\'s national polls', pc(FC['inputs']['poll_share']) + ' (and see below)', pc(C['poll_share_total'])] + [pc(ow[k]['polls_in_national']) if k in ow else '' for k in ways]])
    bare = B.run(days=[1], with_state_models=False)                     # the published forecast without the state models, for the comparison in section 5
    pub_states_load = 0.5 * FC['inputs']['poll_share'] + 0.5 * 0.5 * M.LONG_RANGE_POLLS
    doc = f"""# Findings for review

November 25, 2026. Written by `review.py` from the files the other scripts wrote; rerun it and the figures follow.

**Nothing in the published forecast has changed.** Its settings, its state model and its rules are the ones it had, and
for the same inputs it gives the same numbers to the last digit. This document reports research, a candidate built to
the brief and run beside the published forecast every time it runs, and the checks made on both. The candidate is kept
in `data/forecast_2028.json` under `candidate` and in two columns of `data/history.csv`. It is not on the page.

Misses are in points of margin, the gap between the two parties. An election counts once, however many of its states
are close. There are five elections with state-level models on record, 2008 to 2024. Five is few, and the standard
errors below should be read before any of the differences.

## 1. Do the state models know the states, or only the country?

A state forecast can be wrong about the country or wrong about the state's place in it. `state_geography_check.py`
takes the two apart for the approval and economy model (Enns and colleagues), the long-range model (DeSart) and their
average, the combined model that Tipping Point publishes. Each is scored as it stands (its own national level
included) and centred (moved so that its national figure equals a common one, so that only where it places the state
counts), alone and mixed with this forecast's own lean.

**With the actual national result given to everything.** This is an oracle: nobody had the result, so these are not
forecasts. It removes every national error and leaves the placing of the states.

{geo[0]}

By election, all 51 states, and with each election left out in turn:

{geo[1]}

The same for states decided by under 10 points:

{geo[2]}

**As a real forecast.** Here each rule is given the national number this forecast itself held on the day, from polls
and fundamentals available then. A model taken as it stands keeps its own national level.

{geo[4]}

Each rule against the lean alone, election by election:

{geo[3]}

Where each model's miss comes from:

{geo[5]}

**What this shows.**

- Centring helps the approval model: {f2(O['all']['enns absolute']['miss'])} as it stands, {f2(O['all']['enns centred']['miss'])} centred. So part of its error was the country, as suspected. But centred it is still no better
  than the lean alone ({f2(O['all']['lean']['miss'])}), and in states decided by under 10 points it is worse ({f2(O['close']['enns centred']['miss'])} against {f2(O['close']['lean']['miss'])}). Its placing of the states does not
  carry information the lean lacks on this record.
- The combined model's placing is about as good as the lean's ({f2(O['all']['combined centred']['miss'])} against {f2(O['all']['lean']['miss'])}; a difference of {O['all']['combined centred']['vs_lean']['mean']:+.2f} with a standard error of {O['all']['combined centred']['vs_lean']['se']:.2f}).
  Its clear lead as a real forecast far from the election ({f2(A['120']['all']['combined absolute']['miss'])} against {f2(A['120']['all']['lean']['miss'])} at 120 days) is mostly national: the two models' national figures, averaged, were closer than this
  forecast's own national number at that distance. Give both the same national number and most of the lead goes
  ({f2(A['120']['all']['combined centred']['miss'])} against {f2(A['120']['all']['lean']['miss'])}).
- The long-range model places the states best ({f2(O['all']['desart centred']['miss'])}; better than the lean in {O['all']['desart centred']['vs_lean']['better_in']} of 5). It is also nearly the lean itself: its placing is
  the last result with a home-state term, and the two correlate at {G['alike']['desart']['placing_with_lean']}.
- All three placings are close to one thing measured three ways. Against the lean they correlate at {G['alike']['enns']['placing_with_lean']} (approval model), {G['alike']['combined']['placing_with_lean']} (combined) and {G['alike']['desart']['placing_with_lean']} (long-range), and their
  errors at {G['alike']['enns']['errors_with_lean']}, {G['alike']['combined']['errors_with_lean']} and {G['alike']['desart']['errors_with_lean']}. Averaging them with the lean cannot be expected to gain much, and it does not: the best mix beats the lean by
  {abs(O['all']['combined centred 50% + lean']['vs_lean']['mean']):.2f} to {abs(O['all']['combined absolute 50% + lean']['vs_lean']['mean']):.2f} points.
- **2020 decides the approval model's result.** Without 2020 its centred miss is {f2(O['all']['enns centred']['without']['2020'])} against {f2(O['all']['lean']['without']['2020'])} for the lean; with it, {f2(O['all']['enns centred']['miss'])} against {f2(O['all']['lean']['miss'])}. Its 2020 entry
  is the forecast its authors published that year, made with an earlier version of the model and read from a chart in
  their article. The current model's own forecast of 2020 is not on record here: rebuilding it needs the authors'
  replication files, which are not in the repositories. 2020 is kept in every figure above; the columns "Without" are
  there to show its weight, not to drop it.
- The published setting (half lean, half combined model as it stands) against the centred alternative: {pair(O['all'])} on
  the oracle test, {pair(A['120']['all'])} at 120 days and {pair(A['1']['all'])} on the last day (mean difference, standard error, elections in which
  the published setting was the closer). Its lead at 120 days is the models' national level again, which the centred
  version does not use.

**What follows, and what does not.** The record supports keeping the combined model and not the approval model alone.
It does not pick between taking the state models as they stand and taking only their placing: the lowest figure in
these tables moves with the test and with one election. The choice is one of design. Where the Nowcast's national
figure is already used for the national number, as in the candidate below, taking the state models as they stand counts
that national figure a second time, so the candidate takes only their placing. **The published state model is
unchanged.**

## 2. A national number from the Nowcast, the Keys and the polls

**The parts, and how far each stood from the result.**

{comp}

Two things stand out. The Nowcast's two models missed on opposite sides in {long['nowcast_opposite']} elections of 5, which is why their
average ({f2(long['combined'])}) does better than either. And the Fifty-Two Keys line missed toward the Democrats in {long['keys_dem']} of 5, by {f1(long['keys_mean'])}
points on average. Adding it to the Nowcast's figure makes the prior a little worse on these five elections ({f2(long['prior'])}
against {f2(long['combined'])}). That is the cost, on this record, of having the Keys in the foundation.

Over the longer record, each fitted only on the elections before, the approval equation alone has missed by {f1(long['approval'])} points in a
typical year ({long['n']} elections since 1976) and the Fifty-Two Keys line by {f1(long['keys'])} ({long['n_keys']} elections).

**The candidate** (`model.CANDIDATE`):

1. *Structural forecast.* The Nowcast's two national models and the Fifty-Two Keys line, a third each. The Nowcast's
   combined figure is the average of its two models, so this is two parts Nowcast and one part Keys. No weights are
   fitted: two of the three have five elections on record.
2. *The Keys as a distribution.* The line is read at the middle of that site's run ahead (its mean index, {C['keys_index']} today)
   and the spread of the run ahead goes into the range. The published forecast reads the line at the single likeliest
   count.
3. *National polls, phased in.* Their weight comes from what the polling average has been worth at each distance from
   the election (section 3), not from treating polls and prior as unrelated.
4. *Approval* comes only through the Nowcast's approval model and the keys that use it. The separate approval equation
   is left out.

**The Nowcast already holds national polls, and the candidate counts them once.** The Nowcast's combined figure is the
average of two models, and one of them, the long-range model, is built on national head-to-head polls: it moves {M.LONG_RANGE_POLLS}
points for every point in their average. At a third of the structural forecast that is {pc(M.LONG_RANGE_POLLS / 3)} of the national number moving
with the polls before this forecast looks at a poll, at any distance from the election. The record gives polls {pc(C['poll_share_record'])} today.
Two things are done about it.

- *Before its own polls exist, the long-range model is left out.* The model is built on polls taken in October 2027 and
  has made no forecast until then. What the Nowcast shows for it today is the model run early, on today's polls, which
  is early polling with a coefficient of a half. So until November 7, 2027 the candidate's structural forecast is the
  Nowcast's approval model and the Keys line, half each, and polls reach the national number only by the weight the
  record gives them. From that day the Nowcast's combined figure is in, in full. That brings a step on that day: it is
  the day a new forecast comes into being.
- *After its polls are fixed,* the October polls are in the model and, for a few months, still in this forecast's own
  average. The average is then given only the weight the model does not already carry: if the record says polls
  deserve w and the prior already moves g with them, the average gets (w - g) / (1 - g), and nothing when g is the
  larger. The back-test does this too.

The two other treatments are run beside it, in the table at the end of this section and in test B below: the early run
counted in full, as the Nowcast shows it, and counted in part (for as much of its third as polls this far out are worth
against polls on the day the model reads them: {pc(PH['far']['rows'][0]['part'])} at {PH['far']['rows'][0]['days']} days in {PH['far']['rows'][0]['year']}, all of it by the day its polls are
fixed). In both, the polls are counted once by the rule above and the excess over the record's weight is added to the
range.

**Is a separate approval equation redundant?** By its inputs, yes: June approval is in the Nowcast's approval model and
in six of the 52 keys. By its errors, no: over 2008 to 2024 it missed on the same side as the Nowcast's approval model in
{long['same_enns']} elections of 5 and as the long-range model in {long['same_long']}, and over {long['n_keys']} elections on the same side as the Keys line in {long['same_keys']}. Adding
it as a fourth model lowered the candidate's national miss at every distance in test A below. Most of that gain is one
election: in 2020 it missed toward the Republicans while both Nowcast models missed toward the Democrats. Over the
longer record it is the less accurate of the two equations that have one. It is left out of the candidate and shown as
a variant.

**The two forecasts today.**

{side}

The published forecast's national number gives today's polls {pc(FC['inputs']['poll_share'])}. Its map moves with them by more than that: half of
each state's starting point is the Nowcast's forecast of the state, which holds the long-range model, so a point in the
national polls moves a typical state by about {pub_states_load:.2f} points. The candidate's map moves by {C['poll_share_total']:.2f}.

## 3. Phasing polls in

**What is known.** Erikson and Wlezien's work on the timeline of presidential elections finds that polls at the start
of the election year bear almost no relation to the result and that the relation tightens through the campaign as
voters come into line with the fundamentals; Wlezien and Erikson (2002) put the typical gap between poll leads and the
result at about 6.5 points 200 days out and 2.2 at the end, and Jennings, Lewis-Beck and Wlezien put the useful lead
time of a forecast at two to three months. `timeline.py` measures the same thing on the record in hand:
FiveThirtyEight's published polling averages for 1972 to 2016 and this model's own for 2020 and 2024.

{record}

The weights are noisy from one distance to the next (twelve or thirteen elections each), so a smooth curve is fitted
through all of them, using only elections before the one being forecast: a weight on the last day, the distance at
which it has halved, and how fast it falls beyond.

{curves}

For 2028:

{weights}

Beyond 250 days there is no long record. The curve is carried on by its own shape, and tested below on the three
elections that have early polls on file.

**The state record,** each state's polling average and its lean set against the national result:

{record_s}

Far from the election only the closely fought states have polls, which is why the lean looks better there: it is being
scored on fewer and closer states.

**Six things that are kept apart.**

| | Where it enters |
|---|---|
| Recency | A poll's weight halves every (days to the election / 5) days, between 7 and 30. Unchanged. |
| Volume | A state's polls against a starting point worth 1.5 polls. Unchanged, and kept: it is how polls build up in a state. |
| Horizon | New. The national weight follows the curve above. A state's polls are held under a ceiling that follows the state curve, whatever their number. |
| Candidate certainty | New. Until both nominees are known, polls are of pairings that may never happen. The spread between pairings ({(C['pairing_spread'] or 0):.1f} points of share today, never taken as less than {M.SET['pairing_spread_floor']}) is added to the polls' error, which cuts their weight. Polls of somebody's home state are left out until the nominees are known. |
| Pollster quality | Not modelled, here or in the published forecast. The feed's pollster grades are empty, and house effects need a cycle's polls to estimate. Sample size, the kind of voter asked and a pollster's repeat polls are counted. |
| Historical usefulness | New. The curves are the record itself, refitted before each election from the ones before it. |

**Test A: the distances with a record, 2008 to 2024.** The published forecast, the candidate, and the candidate with
one piece put back at a time.

{near[0]}

{near[1]}

{near[2]}

{near[3]}

{near[4]}

**Test B: far from the election.** Early polls are on file for 2016, 2020 and 2024 only. In each cell: the national
miss (+ is too Democratic) and, in brackets, how much of the national number moved with the polls of the day. Before the
long-range model's own polls existed it is rebuilt as it would have been run that day (an approximation, explained in
`validate_phase_in.py`). Rows marked * are after its polls were fixed.

{far_tab}

{far_mean}

The states that had early polls, each against the nation:

{far_states}

**Test C: a state flooded with early polls.** Ten made-up polls of Pennsylvania, all 10 points too Democratic.

{flood}

**What this shows.**

- With a record behind it (250 days and nearer) neither forecast is ahead throughout. The candidate's national number
  is closer far out ({f2(NR[CN]['250']['national'])} against {f2(NR[P]['250']['national'])} at 250 days), level in the middle ({f2(NR[CN]['120']['national'])} against {f2(NR[P]['120']['national'])} at 120) and further off at
  the end ({f2(NR[CN]['1']['national'])} against {f2(NR[P]['1']['national'])} on the last day). Its state miss is higher at every distance ({f2(NR[CN]['120']['state'])} against {f2(NR[P]['120']['state'])} at 120 days,
  {f2(NR[CN]['1']['state'])} against {f2(NR[P]['1']['state'])} on the last day). It calls more states far out ({NR[CN]['250']['called']} against {NR[P]['250']['called']} at 250 days) and the same number
  at the end. Part of the gap in the state miss is the state models: taken as they stand, as in the published
  forecast, the candidate's state miss is {f2(NR[AS]['120']['state'])} at 120 days and {f2(NR[AS]['1']['state'])} on the last day. Five elections cannot
  separate differences of this size.
- Far out, the published rule let early state polls take {pc(float(np.mean([r['published_states']['share'] for r in st_rows])))} of a polled state on average and up to {pc(max(r['published_states']['max_share'] for r in st_rows))}; the candidate
  held them to {pc(float(np.mean([r['candidate_states']['share'] for r in st_rows])))} and at most {pc(max(r['candidate_states']['max_share'] for r in st_rows))}. On the states that had early polls the candidate's miss averaged {f2(pm('candidate'))} and the
  published rule's {f2(pm('published'))}. In the flood test the published rule follows ten bad polls almost all the way at any distance;
  the candidate follows them {pc(fl[0]['candidate']['share'])} of the way at {fl[0]['days']} days and {pc(fl[-1]['candidate']['share'])} at {fl[-1]['days']}.
- **Far out, the candidate's national number did worse than the published one** on these three elections: {f2(bf['all']['candidate'])} against
  {f2(bf['all']['published'])}. It is 2020: the Nowcast's approval model was {G['split']['enns']['2020']['national']:+.1f} points off that year and the published fundamentals happened
  to miss the other way ({f2(bf['by_year']['2020']['candidate'])} against {f2(bf['by_year']['2020']['published'])}). In 2016 and 2024 the two are within half a point of each other.
- **The long-range model's early run made the far-out number worse the more it counted:** left out {f2(bf['all']['candidate'])}, in part {f2(bf['all']['in_part'])}, in
  full {f2(bf['all']['in_full'])}. It carries the early polls into the number. Three elections cannot settle this, but they agree with the
  timeline literature and they do not argue for giving the early run its third.
- The early polls on file are of the two people who went on to be nominated. Real early polls are spread over pairings
  that never happen and are worse than these. The test flatters every rule that leans on them.

## 4. State polls

The sources were checked directly on November 25, 2026.

- **PollResults.org** does serve state-level general-election polls through the feed Tipping Point already reads
  (`/v1.0/politics/results/president`). Each poll carries its state, each question its stage (primary or general), the
  group asked and the sample. Paging is by cursor, 100 polls a page at most; the data are The New York Times's, CC BY
  4.0. The feed's pollster grades are empty.
- **VoteHub** (CC BY 4.0) lists these poll types: governor, U.S. House, presidential primary, U.S. Senate, generic
  ballot, favorability, a California ballot measure, mayor, attorney general and approval. None is the presidential general
  election. The script reads the list on every run and warns if one appears.
- **RealClearPolling** listed national pairings only among its 2028 general-election races. It is not read: its data
  are not openly licensed.

Found today: {f['general_election_questions']} general-election questions in the feed, {f['national_polls']} national polls and **{f['state_polls']} polls of single states** ({', '.join(f['states_polled'])}),
{f['state_questions']} questions in all. {f['usable_state_polls']} meets the rules. The rest: {'; '.join(f'{v} {k}' for k, v in f['not_usable'].items())}.

So there were state polls, and the forecast was not retrieving them: it read only the Nowcast's national list. They are
now read, placed, counted once and listed on each state's page with the reason each is or is not usable
(`polls.py`, README "State polls"). The published forecast still counts none, because its rule for them is the one
test C shows failing; the candidate counts them under its ceiling ({pc(C['state_poll_ceiling'])} of a state today).

## 5. The main back-test

`backtest.py` now runs what the live forecast runs: the polls as they stood, the national prior, the state-level models
and the error sizes, through the same code. Before this it ran on the national number and each state's lean alone.

{final}

On the last day the published forecast favored the winner in {int(last.called.sum())} of 5, missed a state by {f2(pub_st[1])} points in a typical case and
called {int(last.states_called.sum())} of {int(last.of.sum())} states and districts; {pc(float(last.cover80.mean()))} of state results fell inside ranges meant to hold 80%. Without the state
models the last-day state miss was {f2(2 * bare.state_mae.mean())} and the count of calls {int(bare.states_called.sum())}. `python backtest.py candidate` runs the candidate
the same way, with its structural forecast, its phase-in and the state models' placing.

**What could not be rebuilt as it stood, and is used all the same or left out.** These are limits of the validation,
not footnotes to it.

- *The state-level models have one forecast a year on record, not one a day.* The approval model's is made about 100
  days out, so the test at 120 days sees it three weeks early; the long-range model's is made a year out and is truly
  available at every distance tested.
- *For 2008, 2012 and 2016 the state-level models are refits,* each on the elections before, with that year's final
  inputs. For 2020 and 2024 they are the forecasts the authors published. The approval model's 2020 entry is from the
  earlier version of the model, read from a chart.
- *The Fifty-Two Keys count for a past year uses that year's final figures* and today's revised economic data. Most of
  it was known by late summer; at 120 days and beyond the test sees a little more than could have been known.
- *Betting odds are not in the back-test.* Checkable election-eve odds for 2008 to 2024 have not been collected. The
  25% given to markets in the 2028 number is not validated.
- *The far-out test rests on three elections,* with early polls of pairings picked in hindsight and a long-range model
  rebuilt by approximation. It can show a rule failing. It cannot show one working.
- *The candidate's range two years out is not validated.* The drift allowed in its inputs (ten points of net approval,
  the spread of the keys' run ahead) is a stated size, not a measured one. The same is true of the published forecast.
- *Approval two years out is taken at today's value,* with a range for drift, in both forecasts. Whether it should be
  pulled toward its usual level this far out has not been tested.
- *Pollster quality is not modelled* in either forecast.

## 6. Updates

All three sites now check their sources every hour and rerun only when something they read has changed. Each keeps
every forecast that differs from the one before it in a file that is never rewritten. The details are in each
repository's README.

| | Checks | Reruns when | Keeps |
|---|---|---|---|
| Fifty-Two Keys | Approval polls every hour. The economic series on working days at 8, 9, 10 and 11 a.m. Eastern, every day at 2 and 8 p.m., and on the day's first run | A figure the run ahead reads has changed, a figure is newly held back, or the day has changed | `archive/`: each run whose projection says something new |
| Tipping Point | The poll feeds every hour. The state indexes at the same hours as above | The models' inputs, the settings or the code have changed, or the day has changed. Its cutoffs are untouched | `docs/record/`: each Nowcast that differs from the last |
| The Margin | The Nowcast, the Keys feed, the betting odds and the state polls every hour | A poll, the Nowcast's forecasts, approval, the keys, odds a point from the price in use, or the day | `docs/archive/`: each forecast that differs from the last |

A change in Fifty-Two Keys or Tipping Point reaches The Margin at its next hourly run. It can be immediate: both send
The Margin an event when they publish, if their repositories hold a secret named `DISPATCH_TOKEN`. That takes a token
only the owner can create, so it is built and switched off until the secret is there.

**The checks on new economic figures.** The allowance made for 2020 and 2021 in the quarterly series does not loosen
the check on a newly published figure. The figures already in the tables are checked only for having been revised; a
figure for a new date is held to a tight limit against the one before it. A wrong unit, a slipped decimal point, a
flipped sign, a zero, a missing value or a re-based history is held back, and so is a real move as large as spring 2020
until somebody has looked at it (`tests/test_update.py` in the Fifty-Two Keys repository).

## 7. Decisions that are yours

1. **Whether the candidate's national number replaces the published one.** With a record behind it neither is ahead
   throughout. Far out the candidate did worse on three elections, through 2020.
2. **How the long-range model counts before its own polls exist.** Left out until November 2027 (the candidate), in
   part, or in full (the Nowcast as it stands, which lets early polls move {pc(M.LONG_RANGE_POLLS / 3)} of the national number). The brief asks
   for the Nowcast's combined figure and for early polls to count for very little. Before October 2027 those two pull
   against each other, and this is where the candidate comes down.
3. **Whether the state models are taken as they stand or only for their placing.** As they stand is the published
   setting. The record does not separate the two.
4. **Whether state polls are counted, and by which rule.** The published forecast counts none today. Counting them by
   the published rule is what test C warns against.
5. **Whether the approval equation stays** as a fourth model.
6. **The range.** In the published forecast the allowance for drift in approval and the keys does not shrink as the
   election nears; only the chart of the narrowing range assumes it does. The candidate shrinks it to nothing by late
   June 2028. This is not changed in the published forecast.
7. **Whether to create the token** that lets Fifty-Two Keys and Tipping Point tell The Margin at once when they change
   (section 6). Without it the delay is up to an hour.

## Reading

- Wlezien and Erikson, "The timeline of presidential election campaigns", Journal of Politics, 2002.
- Erikson and Wlezien, The Timeline of Presidential Elections, University of Chicago Press, 2012.
- Jennings and Wlezien, "The timeline of elections: a comparative perspective", American Journal of Political Science,
  2016: https://eprints.soton.ac.uk/377393/1/JenningsWlezienMPSA2015_20FINAL.pdf
- Wlezien, Jennings and Erikson, "The 'timeline' method of studying electoral dynamics", Electoral Studies, 2017:
  https://eprints.soton.ac.uk/407581/1/ES_TimelineMethod.pdf
- Jennings, Lewis-Beck and Wlezien, "Election forecasting: too far out?", International Journal of Forecasting, 2020:
  https://eprints.soton.ac.uk/436948/1/ForecastingLeadTime_IJF_for_publication_Final.docx
- Enns, Colner, Kumar and Lagodny, the state presidential approval and state economy model, PS: Political Science and
  Politics, 2024, doi:10.1017/S1049096524000994.
- DeSart, "Long-range state-level 2024 presidential election forecast", PS: Political Science and Politics, 2025,
  doi:10.1017/S1049096524000805.
- PollResults.org, API documentation: https://pollresults.org/api/ . VoteHub: https://api.votehub.com
"""
    open('REVIEW.md', 'w').write(doc)
    print('REVIEW.md', len(doc), 'characters')


if __name__ == '__main__':
    main()
