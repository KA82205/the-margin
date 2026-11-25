# Findings for review

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

| Actual national result given (oracle) | All 51 (255) | Decided by under 10 points (73) | Decided by under 5 (36) | Under 10 points last time (80) | The seven of 2024 (35) |
|---|---:|---:|---:|---:|---:|
| The lean alone (this forecast's own rule) | 4.17 | 3.42 | 3.64 | 3.88 | 3.24 |
| Approval model, as it stands | 5.18 | 4.51 | 4.83 | 4.89 | 3.98 |
| Combined model, as it stands | 4.12 | 3.56 | 3.61 | 4.08 | 3.35 |
| Long-range model, as it stands | 4.40 | 4.13 | 3.70 | 4.39 | 4.13 |
| Approval model, centred | 4.73 | 4.16 | 4.32 | 4.84 | 4.29 |
| Combined model, centred | 4.03 | 3.36 | 3.60 | 4.01 | 3.41 |
| Long-range model, centred | 3.88 | 3.06 | 3.22 | 3.63 | 2.82 |
| Half lean, half approval model centred | 4.15 | 3.57 | 3.80 | 4.18 | 3.57 |
| Half lean, half combined model centred | 3.96 | 3.33 | 3.58 | 3.88 | 3.25 |
| Half lean, half approval model as it stands | 4.24 | 3.73 | 4.20 | 4.23 | 3.39 |
| Half lean, half combined model as it stands (the published setting) | 3.90 | 3.32 | 3.56 | 3.81 | 3.18 |

By election, all 51 states, and with each election left out in turn:

| All 51 states, oracle | 2008 | 2012 | 2016 | 2020 | 2024 | Mean | Without 2008 | Without 2012 | Without 2016 | Without 2020 | Without 2024 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| The lean alone (this forecast's own rule) | 5.77 | 3.28 | 6.10 | 2.69 | 3.01 | 4.17 | 3.77 | 4.39 | 3.69 | 4.54 | 4.46 |
| Approval model, as it stands | 5.83 | 4.79 | 5.77 | 6.77 | 2.74 | 5.18 | 5.02 | 5.28 | 5.03 | 4.78 | 5.79 |
| Combined model, as it stands | 5.15 | 3.45 | 5.27 | 4.71 | 2.04 | 4.12 | 3.87 | 4.29 | 3.84 | 3.98 | 4.64 |
| Long-range model, as it stands | 5.48 | 5.11 | 5.09 | 4.18 | 2.14 | 4.40 | 4.13 | 4.22 | 4.23 | 4.45 | 4.96 |
| Approval model, centred | 5.41 | 3.65 | 5.66 | 5.96 | 2.99 | 4.73 | 4.56 | 5.00 | 4.50 | 4.43 | 5.17 |
| Combined model, centred | 5.17 | 3.45 | 5.48 | 3.60 | 2.46 | 4.03 | 3.75 | 4.17 | 3.67 | 4.14 | 4.42 |
| Long-range model, centred | 5.11 | 3.63 | 5.51 | 2.69 | 2.46 | 3.88 | 3.57 | 3.94 | 3.47 | 4.18 | 4.23 |
| Half lean, half approval model centred | 5.42 | 3.22 | 5.69 | 3.64 | 2.76 | 4.15 | 3.83 | 4.38 | 3.76 | 4.27 | 4.49 |
| Half lean, half combined model centred | 5.37 | 3.25 | 5.73 | 2.76 | 2.67 | 3.96 | 3.60 | 4.13 | 3.51 | 4.26 | 4.28 |
| Half lean, half approval model as it stands | 5.47 | 3.56 | 5.75 | 3.81 | 2.61 | 4.24 | 3.93 | 4.41 | 3.86 | 4.35 | 4.65 |
| Half lean, half combined model as it stands (the published setting) | 5.35 | 3.25 | 5.63 | 2.89 | 2.35 | 3.90 | 3.53 | 4.06 | 3.46 | 4.15 | 4.28 |

The same for states decided by under 10 points:

| Decided by under 10 points, oracle | 2008 | 2012 | 2016 | 2020 | 2024 | Mean | Without 2008 | Without 2012 | Without 2016 | Without 2020 | Without 2024 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| The lean alone (this forecast's own rule) | 4.73 | 1.73 | 4.90 | 2.86 | 2.89 | 3.42 | 3.09 | 3.85 | 3.05 | 3.56 | 3.55 |
| Approval model, as it stands | 4.13 | 4.63 | 5.81 | 5.75 | 2.21 | 4.51 | 4.60 | 4.48 | 4.18 | 4.20 | 5.08 |
| Combined model, as it stands | 4.24 | 2.22 | 5.34 | 4.45 | 1.57 | 3.56 | 3.40 | 3.90 | 3.12 | 3.34 | 4.06 |
| Long-range model, as it stands | 4.77 | 4.53 | 4.88 | 4.68 | 1.79 | 4.13 | 3.97 | 4.03 | 3.94 | 3.99 | 4.71 |
| Approval model, centred | 4.68 | 2.85 | 5.81 | 4.80 | 2.65 | 4.16 | 4.03 | 4.49 | 3.75 | 4.00 | 4.54 |
| Combined model, centred | 4.39 | 2.22 | 5.34 | 2.48 | 2.39 | 3.36 | 3.11 | 3.65 | 2.87 | 3.58 | 3.61 |
| Long-range model, centred | 4.10 | 2.01 | 4.93 | 2.10 | 2.18 | 3.06 | 2.81 | 3.33 | 2.60 | 3.31 | 3.29 |
| Half lean, half approval model centred | 4.71 | 2.04 | 5.34 | 3.02 | 2.76 | 3.57 | 3.29 | 3.96 | 3.13 | 3.71 | 3.78 |
| Half lean, half combined model centred | 4.56 | 1.90 | 5.11 | 2.44 | 2.63 | 3.33 | 3.02 | 3.68 | 2.88 | 3.55 | 3.50 |
| Half lean, half approval model as it stands | 4.38 | 2.70 | 5.34 | 3.71 | 2.54 | 3.73 | 3.57 | 3.99 | 3.33 | 3.74 | 4.03 |
| Half lean, half combined model as it stands (the published setting) | 4.48 | 1.90 | 5.11 | 2.97 | 2.15 | 3.32 | 3.03 | 3.68 | 2.88 | 3.41 | 3.62 |

**As a real forecast.** Here each rule is given the national number this forecast itself held on the day, from polls
and fundamentals available then. A model taken as it stands keeps its own national level.

| The national number this forecast held on the day (a real forecast) | All 51, 120 days | All 51, 60 days | All 51, 30 days | All 51, 1 days | Under 10 points, 120 days | Under 10 points, 60 days | Under 10 points, 30 days | Under 10 points, 1 days |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| The lean alone (this forecast's own rule) | 4.67 | 4.32 | 4.63 | 4.28 | 3.90 | 3.49 | 3.88 | 3.43 |
| Approval model, as it stands | 5.18 | 5.18 | 5.18 | 5.18 | 4.51 | 4.51 | 4.51 | 4.51 |
| Combined model, as it stands | 4.12 | 4.12 | 4.12 | 4.12 | 3.56 | 3.56 | 3.56 | 3.56 |
| Long-range model, as it stands | 4.40 | 4.40 | 4.40 | 4.40 | 4.13 | 4.13 | 4.13 | 4.13 |
| Approval model, centred | 5.14 | 4.95 | 5.21 | 4.91 | 4.17 | 3.96 | 4.25 | 3.92 |
| Combined model, centred | 4.49 | 4.25 | 4.55 | 4.19 | 3.62 | 3.37 | 3.82 | 3.30 |
| Long-range model, centred | 4.41 | 4.12 | 4.39 | 4.00 | 3.63 | 3.34 | 3.79 | 3.21 |
| Half lean, half approval model centred | 4.60 | 4.30 | 4.62 | 4.25 | 3.78 | 3.45 | 3.91 | 3.46 |
| Half lean, half combined model centred | 4.41 | 4.08 | 4.38 | 4.04 | 3.69 | 3.34 | 3.76 | 3.29 |
| Half lean, half approval model as it stands | 4.26 | 4.20 | 4.26 | 4.34 | 3.51 | 3.46 | 3.49 | 3.66 |
| Half lean, half combined model as it stands (the published setting) | 4.00 | 3.92 | 4.07 | 4.01 | 3.32 | 3.25 | 3.40 | 3.31 |

Each rule against the lean alone, election by election:

| Against the lean alone: mean difference (standard error), elections better in | All 51, oracle | Under 10 points, oracle | All 51, 120 days out | All 51, last day |
|---|---:|---:|---:|---:|
| Approval model, as it stands | +1.01 (0.84), 2 of 5 | +1.09 (0.79), 2 of 5 | +0.51 (0.93), 3 of 5 | +0.90 (0.85), 1 of 5 |
| Combined model, as it stands | -0.05 (0.55), 3 of 5 | +0.14 (0.49), 2 of 5 | -0.55 (0.68), 4 of 5 | -0.15 (0.58), 3 of 5 |
| Long-range model, as it stands | +0.23 (0.60), 3 of 5 | +0.71 (0.70), 2 of 5 | -0.27 (0.58), 3 of 5 | +0.12 (0.66), 3 of 5 |
| Approval model, centred | +0.56 (0.69), 3 of 5 | +0.74 (0.40), 2 of 5 | +0.48 (0.71), 3 of 5 | +0.63 (0.64), 2 of 5 |
| Combined model, centred | -0.14 (0.30), 3 of 5 | -0.06 (0.22), 3 of 5 | -0.18 (0.28), 4 of 5 | -0.09 (0.23), 2 of 5 |
| Long-range model, centred | -0.29 (0.20), 4 of 5 | -0.36 (0.22), 3 of 5 | -0.26 (0.16), 4 of 5 | -0.28 (0.19), 4 of 5 |
| Half lean, half approval model centred | -0.03 (0.25), 4 of 5 | +0.15 (0.11), 2 of 5 | -0.07 (0.26), 4 of 5 | -0.02 (0.24), 3 of 5 |
| Half lean, half combined model centred | -0.22 (0.10), 4 of 5 | -0.09 (0.12), 3 of 5 | -0.26 (0.09), 4 of 5 | -0.24 (0.09), 5 of 5 |
| Half lean, half approval model as it stands | +0.07 (0.29), 3 of 5 | +0.31 (0.28), 2 of 5 | -0.41 (0.47), 4 of 5 | +0.06 (0.36), 3 of 5 |
| Half lean, half combined model as it stands (the published setting) | -0.28 (0.16), 4 of 5 | -0.10 (0.18), 2 of 5 | -0.67 (0.29), 4 of 5 | -0.26 (0.28), 4 of 5 |

Where each model's miss comes from:

| National miss of each model, and its miss on the states once that is taken out | 2008 | 2012 | 2016 | 2020 | 2024 |
|---|---:|---:|---:|---:|---:|
| Approval model: national | +3.60 | -3.63 | +0.38 | +4.46 | +0.52 |
| Long-range model: national | -2.06 | +3.61 | -1.86 | +5.10 | +2.42 |
| Combined: national | +0.76 | -0.01 | -0.74 | +4.82 | +1.46 |
| Approval model: states, centred | 5.41 | 3.65 | 5.66 | 5.96 | 2.99 |
| Long-range model: states, centred | 5.11 | 3.63 | 5.51 | 2.69 | 2.46 |
| Combined: states, centred | 5.17 | 3.45 | 5.48 | 3.60 | 2.46 |
| The lean alone: states | 5.77 | 3.28 | 6.10 | 2.69 | 3.01 |

**What this shows.**

- Centring helps the approval model: 5.18 as it stands, 4.73 centred. So part of its error was the country, as suspected. But centred it is still no better
  than the lean alone (4.17), and in states decided by under 10 points it is worse (4.16 against 3.42). Its placing of the states does not
  carry information the lean lacks on this record.
- The combined model's placing is about as good as the lean's (4.03 against 4.17; a difference of -0.14 with a standard error of 0.30).
  Its clear lead as a real forecast far from the election (4.12 against 4.67 at 120 days) is mostly national: the two models' national figures, averaged, were closer than this
  forecast's own national number at that distance. Give both the same national number and most of the lead goes
  (4.49 against 4.67).
- The long-range model places the states best (3.88; better than the lean in 4 of 5). It is also nearly the lean itself: its placing is
  the last result with a home-state term, and the two correlate at 0.996.
- All three placings are close to one thing measured three ways. Against the lean they correlate at 0.982 (approval model), 0.993 (combined) and 0.996 (long-range), and their
  errors at 0.72, 0.87 and 0.92. Averaging them with the lean cannot be expected to gain much, and it does not: the best mix beats the lean by
  0.22 to 0.28 points.
- **2020 decides the approval model's result.** Without 2020 its centred miss is 4.43 against 4.54 for the lean; with it, 4.73 against 4.17. Its 2020 entry
  is the forecast its authors published that year, made with an earlier version of the model and read from a chart in
  their article. The current model's own forecast of 2020 is not on record here: rebuilding it needs the authors'
  replication files, which are not in the repositories. 2020 is kept in every figure above; the columns "Without" are
  there to show its weight, not to drop it.
- The published setting (half lean, half combined model as it stands) against the centred alternative: -0.06 (0.07), 3 of 5 on
  the oracle test, -0.41 (0.25), 4 of 5 at 120 days and -0.02 (0.22), 3 of 5 on the last day (mean difference, standard error, elections in which
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

| Forecast of the national margin less the result (+ = too Democratic) | 2008 | 2012 | 2016 | 2020 | 2024 | Typical size |
|---|---:|---:|---:|---:|---:|---:|
| Approval equation (published fundamentals, half) | +5.45 | +2.72 | -1.81 | -5.08 | +0.69 | 3.65 |
| Fifty-Two Keys line | +4.78 | +7.76 | +4.41 | +0.83 | +3.82 | 4.85 |
| Published fundamentals (the two averaged) | +5.11 | +5.24 | +1.30 | -2.13 | +2.26 | 3.60 |
| Nowcast: approval and economy model | +3.60 | -3.63 | +0.38 | +4.46 | +0.52 | 3.05 |
| Nowcast: long-range model | -2.06 | +3.61 | -1.86 | +5.10 | +2.42 | 3.24 |
| Nowcast combined | +0.77 | -0.01 | -0.74 | +4.78 | +1.47 | 2.29 |
| Candidate prior (the two Nowcast models and the Keys line, a third each) | +2.10 | +2.58 | +0.97 | +3.46 | +2.25 | 2.41 |
| The same with the approval equation as a fourth | +2.94 | +2.61 | +0.28 | +1.33 | +1.86 | 2.04 |
| National polling average, 120 days out | -1.45 | +0.07 | +3.91 | +4.87 | -1.38 | 2.93 |
| National polling average, last day | -0.03 | -2.18 | +2.38 | +4.14 | +2.88 | 2.68 |

Two things stand out. The Nowcast's two models missed on opposite sides in 3 elections of 5, which is why their
average (2.29) does better than either. And the Fifty-Two Keys line missed toward the Democrats in 5 of 5, by 4.3
points on average. Adding it to the Nowcast's figure makes the prior a little worse on these five elections (2.41
against 2.29). That is the cost, on this record, of having the Keys in the foundation.

Over the longer record, each fitted only on the elections before, the approval equation alone has missed by 8.4 points in a
typical year (13 elections since 1976) and the Fifty-Two Keys line by 5.3 (13 elections).

**The candidate** (`model.CANDIDATE`):

1. *Structural forecast.* The Nowcast's two national models and the Fifty-Two Keys line, a third each. The Nowcast's
   combined figure is the average of its two models, so this is two parts Nowcast and one part Keys. No weights are
   fitted: two of the three have five elections on record.
2. *The Keys as a distribution.* The line is read at the middle of that site's run ahead (its mean index, 0.394 today)
   and the spread of the run ahead goes into the range. The published forecast reads the line at the single likeliest
   count.
3. *National polls, phased in.* Their weight comes from what the polling average has been worth at each distance from
   the election (section 3), not from treating polls and prior as unrelated.
4. *Approval* comes only through the Nowcast's approval model and the keys that use it. The separate approval equation
   is left out.

**The Nowcast already holds national polls, and the candidate counts them once.** The Nowcast's combined figure is the
average of two models, and one of them, the long-range model, is built on national head-to-head polls: it moves 0.522
points for every point in their average. At a third of the structural forecast that is 17% of the national number moving
with the polls before this forecast looks at a poll, at any distance from the election. The record gives polls 3% today.
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
against polls on the day the model reads them: 65% at 500 days in 2016, all of it by the day its polls are
fixed). In both, the polls are counted once by the rule above and the excess over the record's weight is added to the
range.

**Is a separate approval equation redundant?** By its inputs, yes: June approval is in the Nowcast's approval model and
in six of the 52 keys. By its errors, no: over 2008 to 2024 it missed on the same side as the Nowcast's approval model in
2 elections of 5 and as the long-range model in 3, and over 13 elections on the same side as the Keys line in 6. Adding
it as a fourth model lowered the candidate's national miss at every distance in test A below. Most of that gain is one
election: in 2020 it missed toward the Republicans while both Nowcast models missed toward the Democrats. Over the
longer record it is the less accurate of the two equations that have one. It is left out of the candidate and shown as
a variant.

**The two forecasts today.**

| 2028, as of 2026-11-25 | Published forecast | Candidate (long-range model left out for now) | Candidate, long-range model in part | Candidate, long-range model in full |
|---|---:|---:|---:|---:|
| Democrats win the Electoral College | 62% | 69% | 67% | 63% |
| National margin | D+3.1 | D+4.2 | D+3.6 | D+2.8 |
| Democratic electoral votes, middle run | 284 | 300 | 294 | 287 |
| How much of the national number moves with today's national polls | 11% (and see below) | 3% | 9% | 17% |

The published forecast's national number gives today's polls 11%. Its map moves with them by more than that: half of
each state's starting point is the Nowcast's forecast of the state, which holds the long-range model, so a point in the
national polls moves a typical state by about 0.18 points. The candidate's map moves by 0.03.

## 3. Phasing polls in

**What is known.** Erikson and Wlezien's work on the timeline of presidential elections finds that polls at the start
of the election year bear almost no relation to the result and that the relation tightens through the campaign as
voters come into line with the fundamentals; Wlezien and Erikson (2002) put the typical gap between poll leads and the
result at about 6.5 points 200 days out and 2.2 at the end, and Jennings, Lewis-Beck and Wlezien put the useful lead
time of a forecast at two to three months. `timeline.py` measures the same thing on the record in hand:
FiveThirtyEight's published polling averages for 1972 to 2016 and this model's own for 2020 and 2024.

| Days before the election | 1 | 7 | 14 | 30 | 60 | 90 | 120 | 150 | 200 | 250 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Elections on record | 13 | 13 | 13 | 13 | 13 | 13 | 12 | 12 | 13 | 13 |
| Typical miss of the national polling average | 3.7 | 4.4 | 5.0 | 4.2 | 4.7 | 11.8 | 5.3 | 7.0 | 8.5 | 15.6 |
| Best weight on the polls against the fundamentals, in hindsight | 68% | 58% | 50% | 61% | 56% | 18% | 50% | 30% | 24% | 6% |
| Weight given by the curve | 61% | 60% | 58% | 51% | 40% | 31% | 24% | 19% | 14% | 11% |

The weights are noisy from one distance to the next (twelve or thirteen elections each), so a smooth curve is fitted
through all of them, using only elections before the one being forecast: a weight on the last day, the distance at
which it has halved, and how fast it falls beyond.

| Forecast year | Elections behind the national curve | National: weight on the last day, days to half of it, power | State: the same |
|---|---:|---|---|
| 2008 | 8 | 69%, 60, 1.5 | 74%, 40, 1.0 |
| 2012 | 9 | 70%, 70, 1.5 | 72%, 60, 1.0 |
| 2016 | 10 | 68%, 80, 1.5 | 69%, 70, 1.0 |
| 2020 | 11 | 66%, 80, 1.5 | 70%, 80, 1.0 |
| 2024 | 12 | 62%, 90, 1.5 | 67%, 90, 1.0 |
| 2028 | 13 | 61%, 90, 1.5 | 67%, 90, 1.0 |

For 2028:

| Days before the election | 1 | 30 | 60 | 120 | 200 | 250 | 365 | 500 | 715 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| National polls: weight the record gives them | 61% | 51% | 40% | 24% | 14% | 11% | 7% | 4% | 3% |
| State polls: ceiling on their share of a state | 100% | 76% | 61% | 43% | 31% | 27% | 20% | 15% | 11% |

Beyond 250 days there is no long record. The curve is carried on by its own shape, and tested below on the three
elections that have early polls on file.

**The state record,** each state's polling average and its lean set against the national result:

| Days before the election | 1 | 7 | 14 | 30 | 60 | 90 | 120 | 150 | 200 | 250 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| State averages on record | 576 | 573 | 562 | 522 | 452 | 415 | 368 | 324 | 300 | 228 |
| Typical miss of a state polling average, against the nation | 5.5 | 5.9 | 6.7 | 6.4 | 8.1 | 11.4 | 7.3 | 7.6 | 7.9 | 8.4 |
| Typical miss of the lean | 7.5 | 7.5 | 7.0 | 6.9 | 6.3 | 6.2 | 6.0 | 5.9 | 6.0 | 6.0 |
| Best weight on the state polls against the lean, in hindsight | 71% | 65% | 53% | 55% | 36% | 20% | 37% | 33% | 35% | 33% |
| Ceiling given by the curve | 100% | 94% | 88% | 76% | 61% | 51% | 43% | 38% | 31% | 27% |

Far from the election only the closely fought states have polls, which is why the lean looks better there: it is being
scored on fewer and closer states.

**Six things that are kept apart.**

| | Where it enters |
|---|---|
| Recency | A poll's weight halves every (days to the election / 5) days, between 7 and 30. Unchanged. |
| Volume | A state's polls against a starting point worth 1.5 polls. Unchanged, and kept: it is how polls build up in a state. |
| Horizon | New. The national weight follows the curve above. A state's polls are held under a ceiling that follows the state curve, whatever their number. |
| Candidate certainty | New. Until both nominees are known, polls are of pairings that may never happen. The spread between pairings (1.8 points of share today, never taken as less than 1.5) is added to the polls' error, which cuts their weight. Polls of somebody's home state are left out until the nominees are known. |
| Pollster quality | Not modelled, here or in the published forecast. The feed's pollster grades are empty, and house effects need a cycle's polls to estimate. Sample size, the kind of voter asked and a pollster's repeat polls are counted. |
| Historical usefulness | New. The curves are the record itself, refitted before each election from the ones before it. |

**Test A: the distances with a record, 2008 to 2024.** The published forecast, the candidate, and the candidate with
one piece put back at a time.

| National miss, by days before the election | 250 | 200 | 150 | 120 | 90 | 60 | 30 | 14 | 7 | 1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Published forecast | 2.66 | 2.46 | 2.12 | 2.04 | 2.14 | 1.83 | 2.47 | 2.17 | 1.90 | 1.72 |
| Candidate | 2.09 | 2.10 | 2.00 | 2.07 | 2.15 | 1.86 | 2.62 | 2.57 | 2.12 | 1.97 |
| Candidate, but polls weighed by the published rules | 1.87 | 1.89 | 1.80 | 1.97 | 2.08 | 1.83 | 2.63 | 2.54 | 2.12 | 2.00 |
| Candidate, but the published fundamentals as the prior | 2.97 | 2.85 | 2.54 | 2.37 | 2.28 | 1.95 | 2.48 | 2.21 | 1.83 | 1.66 |
| Candidate, but the state models as they stand (the published setting) | 2.09 | 2.10 | 2.00 | 2.07 | 2.15 | 1.86 | 2.62 | 2.57 | 2.12 | 1.97 |
| Candidate, with the approval equation as a fourth model | 1.68 | 1.70 | 1.62 | 1.72 | 1.83 | 1.59 | 2.24 | 2.38 | 1.94 | 1.80 |

| State miss, by days before the election | 250 | 200 | 150 | 120 | 90 | 60 | 30 | 14 | 7 | 1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Published forecast | 4.04 | 3.89 | 3.92 | 3.86 | 3.95 | 3.82 | 4.15 | 4.22 | 3.81 | 3.66 |
| Candidate | 4.14 | 4.07 | 4.04 | 4.10 | 4.11 | 3.95 | 4.46 | 4.40 | 3.92 | 3.76 |
| Candidate, but polls weighed by the published rules | 4.18 | 4.17 | 4.15 | 4.07 | 4.19 | 4.02 | 4.49 | 4.45 | 3.93 | 3.76 |
| Candidate, but the published fundamentals as the prior | 4.75 | 4.51 | 4.27 | 4.21 | 4.11 | 3.79 | 4.27 | 4.24 | 3.82 | 3.67 |
| Candidate, but the state models as they stand (the published setting) | 4.03 | 3.95 | 4.00 | 4.00 | 3.99 | 3.86 | 4.18 | 4.19 | 3.83 | 3.70 |
| Candidate, with the approval equation as a fourth model | 4.01 | 3.89 | 3.84 | 3.91 | 3.89 | 3.75 | 4.28 | 4.31 | 3.86 | 3.71 |

| States and districts called, of 280, by days before the election | 250 | 200 | 150 | 120 | 90 | 60 | 30 | 14 | 7 | 1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Published forecast | 262 | 263 | 264 | 262 | 261 | 260 | 262 | 264 | 265 | 264 |
| Candidate | 267 | 267 | 267 | 265 | 265 | 263 | 262 | 262 | 264 | 264 |
| Candidate, but polls weighed by the published rules | 263 | 264 | 265 | 263 | 261 | 261 | 261 | 262 | 264 | 264 |
| Candidate, but the published fundamentals as the prior | 260 | 259 | 263 | 261 | 262 | 262 | 261 | 263 | 263 | 264 |
| Candidate, but the state models as they stand (the published setting) | 266 | 268 | 267 | 266 | 266 | 265 | 265 | 263 | 266 | 264 |
| Candidate, with the approval equation as a fourth model | 265 | 264 | 268 | 265 | 267 | 263 | 262 | 262 | 264 | 264 |

| Elections in which the winner was favored, of 5, by days before the election | 250 | 200 | 150 | 120 | 90 | 60 | 30 | 14 | 7 | 1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Published forecast | 4 | 4 | 4 | 4 | 4 | 3 | 3 | 4 | 4 | 4 |
| Candidate | 4 | 4 | 4 | 4 | 4 | 3 | 4 | 4 | 4 | 4 |
| Candidate, but polls weighed by the published rules | 4 | 4 | 4 | 4 | 4 | 3 | 3 | 4 | 4 | 4 |
| Candidate, but the published fundamentals as the prior | 4 | 4 | 4 | 4 | 4 | 3 | 4 | 4 | 4 | 4 |
| Candidate, but the state models as they stand (the published setting) | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 |
| Candidate, with the approval equation as a fourth model | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 |

| State results inside the 80% range, by days before the election | 250 | 200 | 150 | 120 | 90 | 60 | 30 | 14 | 7 | 1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Published forecast | 94% | 94% | 94% | 95% | 93% | 95% | 91% | 89% | 90% | 91% |
| Candidate | 94% | 94% | 94% | 93% | 93% | 94% | 91% | 87% | 91% | 91% |
| Candidate, but polls weighed by the published rules | 94% | 94% | 94% | 95% | 94% | 95% | 91% | 85% | 90% | 91% |
| Candidate, but the published fundamentals as the prior | 93% | 93% | 93% | 93% | 93% | 94% | 91% | 87% | 91% | 91% |
| Candidate, but the state models as they stand (the published setting) | 95% | 96% | 95% | 95% | 94% | 94% | 92% | 89% | 91% | 91% |
| Candidate, with the approval equation as a fourth model | 94% | 93% | 94% | 93% | 92% | 94% | 91% | 88% | 92% | 91% |

**Test B: far from the election.** Early polls are on file for 2016, 2020 and 2024 only. In each cell: the national
miss (+ is too Democratic) and, in brackets, how much of the national number moved with the polls of the day. Before the
long-range model's own polls existed it is rebuilt as it would have been run that day (an approximation, explained in
`validate_phase_in.py`). Rows marked * are after its polls were fixed.

| Election, days out | Early polls alone | Published | Candidate (long-range model left out) | Long-range model in part | Long-range model in full | With hindsight |
|---|---:|---:|---:|---:|---:|---:|
| 2016, 500 | +15.8 | +3.1 (12%) | +2.9 (4%) | +3.5 (13%) | +3.9 (17%) | +1.6 (4%) |
| 2016, 450 | +8.9 | +2.3 (13%) | +2.7 (5%) | +3.0 (14%) | +3.1 (17%) | +1.4 (5%) |
| 2016, 400 | +0.4 | +1.2 (14%) | +2.3 (6%) | +1.9 (16%) | +1.9 (17%) | +0.9 (6%) |
| 2016, 350 * | +0.5 | +1.2 (16%) | +1.0 (7%) | +1.0 (7%) | +1.0 (7%) | +0.9 (7%) |
| 2016, 300 * | +1.4 | +1.3 (19%) | +1.0 (8%) | +1.0 (8%) | +1.0 (8%) | +1.0 (8%) |
| 2020, 650 | +8.2 | -1.1 (9%) | +2.8 (3%) | +3.5 (9%) | +4.1 (17%) | +3.6 (3%) |
| 2020, 600 | +3.1 | -1.6 (10%) | +2.7 (3%) | +3.1 (10%) | +3.4 (17%) | +3.5 (3%) |
| 2020, 550 | +3.7 | -1.5 (11%) | +2.7 (4%) | +3.2 (11%) | +3.5 (17%) | +3.5 (4%) |
| 2020, 500 | +6.2 | -1.1 (12%) | +2.8 (4%) | +3.4 (13%) | +3.6 (17%) | +3.6 (4%) |
| 2020, 450 | +3.8 | -1.4 (13%) | +2.7 (5%) | +3.3 (14%) | +3.5 (17%) | +3.5 (5%) |
| 2020, 400 | +3.5 | -1.3 (14%) | +2.7 (5%) | +3.4 (16%) | +3.5 (17%) | +3.5 (5%) |
| 2020, 350 * | +4.1 | -1.1 (16%) | +3.5 (12%) | +3.5 (12%) | +3.5 (12%) | +3.5 (6%) |
| 2020, 300 * | +2.5 | -1.3 (18%) | +3.4 (8%) | +3.4 (8%) | +3.4 (8%) | +3.4 (8%) |
| 2024, 650 | +2.0 | +2.2 (9%) | +2.2 (3%) | +2.5 (10%) | +2.8 (17%) | +2.2 (3%) |
| 2024, 600 | +2.5 | +2.3 (10%) | +2.2 (3%) | +2.5 (10%) | +2.7 (17%) | +2.3 (3%) |
| 2024, 550 | +2.2 | +2.2 (10%) | +2.2 (4%) | +2.5 (12%) | +2.6 (17%) | +2.2 (4%) |
| 2024, 500 | +1.5 | +2.2 (11%) | +2.1 (4%) | +2.5 (13%) | +2.6 (17%) | +2.2 (4%) |
| 2024, 450 | +1.7 | +2.2 (12%) | +2.1 (5%) | +2.5 (14%) | +2.5 (17%) | +2.2 (5%) |
| 2024, 400 | +0.4 | +2.0 (13%) | +2.1 (6%) | +2.4 (16%) | +2.5 (17%) | +2.1 (6%) |
| 2024, 350 * | -0.0 | +1.9 (15%) | +2.2 (7%) | +2.2 (7%) | +2.2 (7%) | +2.1 (7%) |
| 2024, 300 * | -0.8 | +1.7 (17%) | +2.0 (9%) | +2.0 (9%) | +2.0 (9%) | +2.0 (9%) |

| Mean size of the national miss before the long-range model's own polls existed | Published | Candidate (left out) | In part | In full | With hindsight |
|---|---:|---:|---:|---:|---:|
| All 15 dates | 1.85 | 2.47 | 2.87 | 3.08 | 2.55 |
| 2016 (3 dates) | 2.19 | 2.64 | 2.82 | 2.98 | 1.29 |
| 2020 (6 dates) | 1.35 | 2.72 | 3.30 | 3.60 | 3.50 |
| 2024 (6 dates) | 2.19 | 2.14 | 2.47 | 2.61 | 2.22 |

The states that had early polls, each against the nation:

| Election, days out | States with polls | Starting point alone | Early state polls alone | Published rule: miss (average share to polls, largest) | Candidate rule: miss (average share, largest) |
|---|---:|---:|---:|---:|---:|
| 2016, 450 | 11 | 8.0 | 7.7 | 6.6 (37%, 53%) | 7.8 (5%, 7%) |
| 2016, 400 | 17 | 7.5 | 5.5 | 5.7 (38%, 71%) | 7.2 (6%, 11%) |
| 2016, 350 | 22 | 6.4 | 7.2 | 6.0 (33%, 67%) | 6.3 (6%, 11%) |
| 2016, 300 | 22 | 6.4 | 7.3 | 5.8 (21%, 67%) | 6.3 (4%, 13%) |
| 2020, 600 | 7 | 2.6 | 5.1 | 2.9 (32%, 46%) | 2.6 (4%, 5%) |
| 2020, 550 | 13 | 2.3 | 4.9 | 3.9 (32%, 54%) | 2.2 (4%, 7%) |
| 2020, 500 | 15 | 2.4 | 9.0 | 4.7 (30%, 68%) | 2.4 (4%, 10%) |
| 2020, 450 | 22 | 2.7 | 8.6 | 4.6 (30%, 68%) | 2.6 (4%, 10%) |
| 2020, 400 | 23 | 2.8 | 7.6 | 3.8 (27%, 65%) | 2.7 (4%, 11%) |
| 2020, 350 | 25 | 2.8 | 6.2 | 3.2 (34%, 72%) | 2.6 (6%, 14%) |
| 2020, 300 | 25 | 2.7 | 5.6 | 2.8 (30%, 61%) | 2.7 (6%, 13%) |
| 2024, 600 | 7 | 2.2 | 5.5 | 2.8 (35%, 61%) | 2.3 (5%, 8%) |
| 2024, 550 | 9 | 2.3 | 5.3 | 2.7 (24%, 43%) | 2.3 (3%, 6%) |
| 2024, 500 | 17 | 2.4 | 4.5 | 2.4 (29%, 51%) | 2.4 (4%, 8%) |
| 2024, 450 | 20 | 2.7 | 4.1 | 2.6 (26%, 63%) | 2.6 (4%, 11%) |
| 2024, 400 | 24 | 2.5 | 3.7 | 2.7 (26%, 69%) | 2.5 (5%, 13%) |
| 2024, 350 | 39 | 2.8 | 4.5 | 3.1 (35%, 80%) | 2.8 (7%, 16%) |
| 2024, 300 | 39 | 2.8 | 4.6 | 3.0 (28%, 81%) | 2.7 (7%, 19%) |

**Test C: a state flooded with early polls.** Ten made-up polls of Pennsylvania, all 10 points too Democratic.

| Days before the election | Published rule: share to the ten polls, state moves by | Candidate rule | Candidate rule, nominees not known |
|---|---:|---:|---:|
| 700 | 87%, +9.6 | 10%, +1.1 | 9%, +1.0 |
| 500 | 87%, +9.5 | 13%, +1.4 | 12%, +1.3 |
| 365 | 87%, +9.4 | 17%, +1.8 | 16%, +1.6 |
| 250 | 87%, +10.1 | 23%, +2.6 | 20%, +2.3 |
| 120 | 86%, +9.6 | 38%, +4.2 | 30%, +3.4 |
| 30 | 81%, +8.1 | 61%, +5.5 | 43%, +3.5 |
| 7 | 81%, +8.5 | 76%, +7.5 | 49%, +4.8 |

**What this shows.**

- With a record behind it (250 days and nearer) neither forecast is ahead throughout. The candidate's national number
  is closer far out (2.09 against 2.66 at 250 days), level in the middle (2.07 against 2.04 at 120) and further off at
  the end (1.97 against 1.72 on the last day). Its state miss is higher at every distance (4.10 against 3.86 at 120 days,
  3.76 against 3.66 on the last day). It calls more states far out (267 against 262 at 250 days) and the same number
  at the end. Part of the gap in the state miss is the state models: taken as they stand, as in the published
  forecast, the candidate's state miss is 4.00 at 120 days and 3.70 on the last day. Five elections cannot
  separate differences of this size.
- Far out, the published rule let early state polls take 30% of a polled state on average and up to 81%; the candidate
  held them to 5% and at most 19%. On the states that had early polls the candidate's miss averaged 3.50 and the
  published rule's 3.84. In the flood test the published rule follows ten bad polls almost all the way at any distance;
  the candidate follows them 10% of the way at 700 days and 76% at 7.
- **Far out, the candidate's national number did worse than the published one** on these three elections: 2.47 against
  1.85. It is 2020: the Nowcast's approval model was +4.5 points off that year and the published fundamentals happened
  to miss the other way (2.72 against 1.35). In 2016 and 2024 the two are within half a point of each other.
- **The long-range model's early run made the far-out number worse the more it counted:** left out 2.47, in part 2.87, in
  full 3.08. It carries the early polls into the number. Three elections cannot settle this, but they agree with the
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

Found today: 108 general-election questions in the feed, 35 national polls and **5 polls of single states** (AK, NC, NV, PA),
8 questions in all. 1 meets the rules. The rest: 3 no named candidates (a generic ballot); 1 paid for by a party or a campaign; 1 Barack Obama cannot be elected again; 1 Donald Trump cannot be elected again; 1 Josh Shapiro's own state, while the nominees are not known.

So there were state polls, and the forecast was not retrieving them: it read only the Nowcast's national list. They are
now read, placed, counted once and listed on each state's page with the reason each is or is not usable
(`polls.py`, README "State polls"). The published forecast still counts none, because its rule for them is the one
test C shows failing; the candidate counts them under its ceiling (11% of a state today).

## 5. The main back-test

`backtest.py` now runs what the live forecast runs: the polls as they stood, the national prior, the state-level models
and the error sizes, through the same code. Before this it ran on the national number and each state's lean alone.

| Election | Favored on the last day | National margin: forecast, result | Democratic electoral votes: middle run, range, result | States and districts called |
|---|---|---|---|---|
| 2008 | Democrats, 97 in 100 | D+9.1, D+7.5 | 354, 298 to 405, 365 | 53 of 56 |
| 2012 | Democrats, 79 in 100 | D+3.9, D+3.8 | 302, 250 to 354, 332 | 55 of 56 |
| 2016 | Democrats, 75 in 100 (missed) | D+4.4, D+2.3 | 300, 243 to 356, 232 (outside) | 50 of 56 |
| 2020 | Democrats, 93 in 100 | D+6.8, D+4.5 | 336, 275 to 394, 306 | 53 of 56 |
| 2024 | Republicans, 52 in 100 | D+1.2, R+1.5 | 267, 225 to 322, 226 | 53 of 56 |

On the last day the published forecast favored the winner in 4 of 5, missed a state by 3.66 points in a typical case and
called 264 of 280 states and districts; 91% of state results fell inside ranges meant to hold 80%. Without the state
models the last-day state miss was 3.75 and the count of calls 264. `python backtest.py candidate` runs the candidate
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
   part, or in full (the Nowcast as it stands, which lets early polls move 17% of the national number). The brief asks
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
