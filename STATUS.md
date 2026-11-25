# Where the three sites stand

Written by `status.py` on the forecast of 2026-11-25. Tables are read from the data files; nothing in them is typed.
Misses are in points of margin (twice the miss in share). `REVIEW.md` holds the research this builds on, `RUNBOOK.md` how the
sites are kept running.

## 1. What is official and what is not

| | What it is | Status |
|---|---|---|
| **Published forecast** (The Margin) | The model as it has stood since November 24: the approval equation and the Fifty-Two Keys line averaged, polls weighted by their precision, half of each state's starting point from Tipping Point's state models | Official. Unchanged in this round: `tests/test_model.py` fails if a last-day back-test figure moves |
| Candidate | The two Nowcast models and the Keys line; polls by the record of what they have been worth; state models for their placing only; state polls under a ceiling | Under review, run beside the published one every time |
| **Hybrid** | The candidate with the approval equation kept: approval-and-economy model, Keys line, approval equation, a third each; the long-range model joins as a fourth once its own polls exist (November 7, 2027) | Under review, run beside the published one. **Recommended** (decision A) |
| Fifty-Two Keys | 52 keys, five groups, call at one half; locked | Official. Unchanged |
| Fifty-Two Keys run-ahead and key calls | Where the open keys are likely to land; which keys are called | Running. The outlook is now read from the forecasters' survey by rule |
| Tipping Point | Two published academic models and their Nowcast | Official. Unchanged apart from a footer link |

## 2. Done in this round, with the evidence

**The Margin's display defects** (deployed, commit `ce173b4`).
The map moved because the readout under it wrapped onto a second line for some places and not others; it is now three lines
of fixed height. Ranges were a normal curve around each state's middle, which gave the District of Columbia D+101.6; they are
now the 10th and 90th of every hundred simulated results, and simulated shares are kept inside 0 to 100 without moving any
across 50, so no chance changed. A margin that rounds to 0.0 is written `0.0` in the neutral color by one routine used
everywhere. The headline says its figure includes the betting markets. `node tests/browser_hover.js` hovers over 13 places
(both parties, safe and close, the District, the districts, nothing) at five window sizes and fails if the map, the
electoral-vote bar or the headline moves by half a pixel; `node tests/test_page.js` checks the margin routine;
`tests/test_model.py` checks that every share, margin and range in every forecast is a possible one.

**Fifty-Two Keys calls its keys by itself** (deployed, commits `908bc40`, `0ff1655`).
`calls.py` scores 2028 with the model's own scoring function on the figures published so far and puts each key in one of
four states: unresolved, provisional, settled, held. `KEYS.md` and `data/key_registry.json` list, for all 52, what the key
reads, when it can first be called and what is still entered by hand. Every call and correction is added to
`data/key_calls.csv` and nothing in it is rewritten. Today: 8 settled, 44 unresolved. `tests/test_calls.py` walks a made-up
future from today to the day the count is closed.

**The run-ahead reads its outlook instead of having it typed** (deployed, commits `9107761`, `0709049`).
`outlook.py` reads the Survey of Professional Forecasters' own table and lays a later survey into the outlook. On GitHub's
servers it read the real file and, by rule, gave the growth, inflation and unemployment figures that had been entered by
hand; the only difference was jobs a month in 2028, 51,000 by rule against 50,000 entered. Only a later survey replaces the
outlook. Income, pay, spending, industrial production, factory jobs, oil, sentiment, population and the 30% recession share
are not in the survey and stay as entered, with their date.

**Every kept forecast says what it was made from** (commit `db01e43`).
The archive now records the version of the Fifty-Two Keys feed and of the Nowcast behind each forecast, the model's settings
and the commit that ran it, and keeps the Nowcast file itself once for each version. `docs/api/manifest.json` and
`docs/api/forecast.json` give the current forecast to other programs, the manifest written last.

**The simulation reports ties and splits.** A 269 to 269 tie comes up in 8 of 1,000 simulations and counts as
half a win for each side; the Democrats win the most votes and lose the Electoral College in 15 of 100, the reverse in
3 of 100.

**The three sites link to each other**, and The Margin's Model tab sets the three figures side by side with what each one
measures.

## 3. The hybrid against the published forecast

The hybrid was not found by searching for weights: it is the candidate with one part of the published forecast put back.
Eight versions have now been scored on the same five elections (all are in `data/phase_in.json`), so a small edge among
them means little; what follows is the size and the consistency of the differences.

National miss, mean over 2008 to 2024:

|  | 250 days | 200 days | 150 days | 120 days | 90 days | 60 days | 30 days | 14 days | 7 days | last day |
|---|---|---|---|---|---|---|---|---|---|---|
| Published | 2.66 | 2.46 | 2.12 | 2.04 | 2.14 | 1.83 | 2.47 | 2.17 | 1.90 | 1.72 |
| Candidate | 2.09 | 2.10 | 2.00 | 2.07 | 2.15 | 1.86 | 2.62 | 2.57 | 2.12 | 1.97 |
| Hybrid | 1.68 | 1.70 | 1.62 | 1.72 | 1.83 | 1.59 | 2.24 | 2.38 | 1.94 | 1.80 |
| Hybrid, no long-range model | 1.79 | 1.81 | 1.74 | 1.83 | 1.93 | 1.68 | 2.28 | 2.47 | 2.02 | 1.87 |
| Published prior, polls by the timeline | 2.97 | 2.85 | 2.54 | 2.37 | 2.28 | 1.95 | 2.48 | 2.21 | 1.83 | 1.66 |

The same without 2020, the election the candidate's edge was thought to rest on:

|  | 250 days | 200 days | 150 days | 120 days | 90 days | 60 days | 30 days | 14 days | 7 days | last day |
|---|---|---|---|---|---|---|---|---|---|---|
| Published | 2.95 | 2.76 | 2.50 | 2.53 | 2.59 | 2.16 | 2.60 | 2.08 | 1.84 | 1.59 |
| Candidate | 1.82 | 1.82 | 1.64 | 1.64 | 1.73 | 1.41 | 2.14 | 2.04 | 1.63 | 1.48 |
| Hybrid | 1.77 | 1.78 | 1.60 | 1.60 | 1.71 | 1.39 | 1.92 | 2.00 | 1.60 | 1.46 |

Typical state miss:

|  | 250 days | 200 days | 150 days | 120 days | 90 days | 60 days | 30 days | 14 days | 7 days | last day |
|---|---|---|---|---|---|---|---|---|---|---|
| Published | 4.04 | 3.89 | 3.92 | 3.86 | 3.95 | 3.82 | 4.15 | 4.22 | 3.81 | 3.66 |
| Candidate | 4.14 | 4.07 | 4.04 | 4.10 | 4.11 | 3.95 | 4.46 | 4.40 | 3.92 | 3.76 |
| Hybrid | 4.01 | 3.89 | 3.84 | 3.91 | 3.89 | 3.75 | 4.28 | 4.31 | 3.86 | 3.71 |
| Hybrid, no long-range model | 4.12 | 3.99 | 3.89 | 3.94 | 3.89 | 3.71 | 4.22 | 4.30 | 3.85 | 3.70 |
| Published prior, polls by the timeline | 4.75 | 4.51 | 4.27 | 4.21 | 4.11 | 3.79 | 4.27 | 4.24 | 3.82 | 3.67 |

Mean chance given to the party that went on to win:

|  | 250 days | 200 days | 150 days | 120 days | 90 days | 60 days | 30 days | 14 days | 7 days | last day |
|---|---|---|---|---|---|---|---|---|---|---|
| Published | 69% | 63% | 69% | 72% | 64% | 63% | 67% | 65% | 68% | 69% |
| Candidate | 71% | 69% | 71% | 73% | 68% | 65% | 68% | 64% | 67% | 68% |
| Hybrid | 71% | 69% | 71% | 73% | 68% | 66% | 68% | 64% | 67% | 68% |
| Hybrid, no long-range model | 69% | 67% | 70% | 72% | 67% | 65% | 68% | 64% | 67% | 68% |
| Published prior, polls by the timeline | 68% | 66% | 69% | 71% | 67% | 65% | 68% | 64% | 67% | 68% |

Brier score of the state forecasts (lower is better):

|  | 250 days | 200 days | 150 days | 120 days | 90 days | 60 days | 30 days | 14 days | 7 days | last day |
|---|---|---|---|---|---|---|---|---|---|---|
| Published | 0.0540 | 0.0529 | 0.0512 | 0.0496 | 0.0534 | 0.0489 | 0.0461 | 0.0476 | 0.0414 | 0.0402 |
| Candidate | 0.0496 | 0.0496 | 0.0483 | 0.0483 | 0.0503 | 0.0482 | 0.0479 | 0.0491 | 0.0425 | 0.0405 |
| Hybrid | 0.0496 | 0.0493 | 0.0478 | 0.0477 | 0.0496 | 0.0476 | 0.0471 | 0.0487 | 0.0422 | 0.0403 |
| Hybrid, no long-range model | 0.0516 | 0.0510 | 0.0490 | 0.0488 | 0.0504 | 0.0481 | 0.0471 | 0.0490 | 0.0423 | 0.0404 |
| Published prior, polls by the timeline | 0.0556 | 0.0544 | 0.0514 | 0.0505 | 0.0517 | 0.0486 | 0.0475 | 0.0487 | 0.0423 | 0.0404 |

Before the long-range model's own polls existed (2016, 2020, 2024; more than a year out), mean size of the national miss:

| Election | Dates | Published | Candidate | Hybrid |
|---|---|---|---|---|
| 2016 | 3 | 2.19 | 2.64 | 1.31 |
| 2020 | 6 | 1.35 | 2.72 | 0.24 |
| 2024 | 6 | 2.19 | 2.14 | 1.67 |
| All | 15 | 1.85 | 2.47 | 1.03 |

What this shows. From 250 days to 30 days the hybrid's national number was closer than the published one at every distance,
by a quarter of a point to a full point, and it favored the eventual winner in four elections of five at all ten distances
(the published forecast in three of five at 60 and 30 days). In the last two weeks the published forecast was slightly
closer: by 0.21 at 14 days, 0.04 at 7 and 0.08 on the last day. State misses are level throughout; the hybrid's
Brier score is lower far out and level at the end. Without 2020 the hybrid is closer at all ten distances, so the difference
does not rest on that year. More than a year out, on the 15 dates there are, the hybrid was closer in all three elections.

What it does not show. Five elections, three of them for the early test. The approval-and-economy model's forecast of each
year is the one made about 100 days out, used here at every distance, and the Keys count for a past year uses that year's
final figures, so the early rows flatter every version that uses them, the hybrid included. The published forecast is
flattered the same way by the Keys count. None of this is a forecast made at the time.

| 2028, as of 2026-11-25 | Published | Candidate | Hybrid |
|---|---|---|---|
| Democrats win the Electoral College | 62 in 100 | 69 in 100 | 69 in 100 |
| The same, simulations only (no betting markets) | 60 in 100 | 69 in 100 | 70 in 100 |
| National vote | D+3.1 | D+4.2 | D+4.1 |
| Democratic electoral votes, middle simulation | 284 | 300 | 299 |
| Four in five simulations | 214 to 364 | 220 to 392 | 223 to 387 |
| Polls in the national number | 11% | 3% | 3% |

The Fifty-Two Keys part, as a spread and not one number: the middle of that site's run ahead, 40% of the count, points
to a Democratic share of 52.3% (D+4.6), with four chances in five between 47.1% and 57.7%. Of that
spread, 2.8 points of share come from where the count may still end up and 3.0 from the line's own misses on
past elections. The second part stays when every key is called.

## 4. The Fifty-Two Keys vote line

The line's misses were all toward the Democrats in the five back-tested elections. That is not a mistake of orientation:
in the party-in-office terms the line is fitted in, the misses go both ways.

| Election | Party in office | Miss toward the party in office | Miss toward the Democrats |
|---|---|---|---|
| 2008 | Republicans | -4.9 | +4.9 |
| 2012 | Democrats | +7.6 | +7.6 |
| 2016 | Democrats | +4.5 | +4.5 |
| 2020 | Republicans | -0.8 | +0.8 |
| 2024 | Democrats | +3.8 | +3.8 |

The share the line is fitted on and the national share in the results file differ by at most 0.14 points, so the two are
the same measure. The line has flattened as elections were added: the vote now moves less for a given count than it did
before the 1990s.

| Line fitted on | Typical miss, 2008 to 2024 | Mean miss toward the Democrats | Mean miss toward the party in office | Points of vote for the whole count, 2024 fit |
|---|---|---|---|---|
| Every election since 1952 (as used) | 4.3 | +4.3 | +2.0 | 24 |
| Last ten elections | 3.4 | +3.4 | +1.8 | 18 |
| Elections since 1980 | 2.8 | +2.8 | +1.2 | 19 |

A line fitted on fewer, later elections would have missed by less, but those windows were looked at after the fact and five
elections cannot tell a real change of slope from chance. No correction by party is proposed. Recommendation: leave the
line as it is and carry its error (3.0 points of share) in full (decision D).

## 5. Are the ranges too wide?

The range shown for a place is the 10th to the 90th of every hundred simulated results: a range for the result, not for the
model's middle estimate. All places use the same rule.

| Last day, 2008 to 2024 | Forecasts | Result inside the range | More Republican than the range | More Democratic | Width of the range, points | Typical miss |
|---|---|---|---|---|---|---|
| All states and the District | 255 | 91% | 9% | 1% | 15.9 | 3.7 |
| Projected within 10 points | 81 | 95% | 5% | 0% | 15.7 | 3.3 |
| Projected 10 to 30 points apart | 137 | 89% | 10% | 1% | 15.9 | 3.8 |
| Projected 30 points or more apart | 37 | 86% | 11% | 3% | 16.3 | 3.9 |
| Leaning Democratic | 131 | 96% | 2% | 2% | 15.5 | 3.0 |
| Leaning Republican | 124 | 85% | 15% | 0% | 16.2 | 4.3 |

| Election | Result inside the range | More Republican than the range | More Democratic | Share of the range's width that would have held four results in five |
|---|---|---|---|---|
| 2008 | 90% | 8% | 2% | 66% |
| 2012 | 94% | 4% | 2% | 61% |
| 2016 | 82% | 18% | 0% | 94% |
| 2020 | 88% | 12% | 0% | 83% |
| 2024 | 98% | 2% | 0% | 38% |

| Days out | State results inside the range | Width, points | National result inside its range, of 5 |
|---|---|---|---|
| 120 | 95% | 21.3 | 5 |
| 90 | 93% | 20.7 | 5 |
| 60 | 95% | 19.4 | 5 |
| 30 | 91% | 17.8 | 5 |
| 14 | 87% | 17.0 | 5 |
| 7 | 89% | 16.4 | 5 |
| 1 | 91% | 15.9 | 5 |

On average the ranges held more than four results in five, which read alone says they are wider than they need to be. Read
by election it says something else: in 2016 and 2020 the results fell outside almost only on one side, and in 2016 the
ranges needed nearly all of their width. A range has to be wide enough for the year in which the polls miss together, and
two of the five years were such years. Narrowing the ranges to fit the average would have left 2016 well short.
**Recommendation: keep the width.** Five elections cannot show that a two-year range is too wide or too narrow; this is a
check on the last day only, where there is a record.

One part of the range does need a decision. The allowance for approval still moving (10 points of net approval, set by hand)
does not shrink as June 2028 approaches, while the chart on the Model tab assumes it does. `drift_rule='calendar'` in
`model.py` makes the forecast do what the chart shows: the allowance as it is today, falling with the square root of the
time left and gone by the end of June 2028, when June approval is a fact. It is written, tested and switched off. Today's
forecast is the same either way (decision B).

## 6. Updates as they actually run

Measured from GitHub's own record of runs, not from the schedule.

- Hourly schedules went into all three repositories at about 18:00 UTC on November 25. In the four hours after that, to
  22:00 UTC, **GitHub started no scheduled run in any of the three**. Every run in that window was started by hand, by a
  push, or by a notification. Before the change, Tipping Point's scheduled runs did start, about twice a day.
- Notifications work from Fifty-Two Keys: two of its runs told The Margin, and The Margin ran within two minutes each time
  (19:01 and 21:48 UTC). Tipping Point has no `DISPATCH_TOKEN` secret and says so in its log, so its changes reach The
  Margin only at The Margin's own next run.
- A run with nothing new ends without saving anything (checked by hand in all three). A run with something new saves,
  archives and deploys.

So the chain works when a run starts; what cannot be promised is when GitHub starts one. `RUNBOOK.md` has the two things
that would make it dependable (decisions F and G).

## 7. Decisions that are yours

A. **Adopt the hybrid as the published national method?** Recommended: yes. It keeps every part of the published forecast
   that has earned its place, adds the approval-and-economy model, stops early polls from counting for more than their
   record supports, and holds early state polls under a ceiling. Effect today: 62 to 69 in 100, national vote D+3.1 to
   D+4.1, 284 to 299 electoral votes. The published forecast stays as it is until you say so. This is the one decision here
   worth a second, slower look.
B. **Let the approval allowance shrink with the calendar?** Recommended: yes. No change today; without it somebody has to
   edit `data/inputs.json` by hand in 2028.
C. **Which number is the headline?** Today the headline (62 in 100) is the simulations (60 in 100) moved a quarter of
   the way toward betting markets, and the page says so. Markets are in no back-test, and the blend makes the headline
   differ from the map and the electoral-vote chart beneath it. Recommended: make the simulations the headline and show the
   market figure beside it.
D. **The Keys vote line.** Recommended: no change (section 4).
E. **Three rules Fifty-Two Keys needs before 2028**: the day the count is closed (proposed: August 1, 2028); which polls
   decide the third-candidate key and how they are averaged; and who counts as "the nominee" before the conventions, for
   the delegate and New Hampshire keys. `KEYS.md` sets out each. Until they are settled those five keys are entered by hand.
F. **Add `DISPATCH_TOKEN` to Tipping Point.** It is already in Fifty-Two Keys. Steps in `RUNBOOK.md`; nothing to paste here.
G. **Scheduled runs.** Wait a day and read the record again, or let each site's run wake the other two (the token would then
   need to cover all three repositories). No paid service is needed for either.
H. **A contact link on The Margin.** Tipping Point's footer links to your LinkedIn page. Say the word and The Margin's
   footer gets the same link, with no name or photo beside it.

## 8. The roadmap, section by section

| Roadmap | Status |
|---|---|
| 3 Audit; 4 Literature | Done in `REVIEW.md`; reconciled here |
| 5 National architecture; 12 Combination and overlap | Built and tested as the hybrid; under review (A). Polls shared with the long-range model are counted once, and the test says so; no claim that this removes every overlap |
| 6 Tipping Point integration | Working: The Margin reads the Nowcast's two models separately and records its version, mode and whether it is fixed. Still read from `nowcast.js`, not a plain JSON file. Token missing (F) |
| 7 Fifty-Two Keys: vote line, spread, key calls, run-ahead | Done and deployed. Still by hand: five nomination and third-candidate keys (E), the seat counts every two years, and the parts of the outlook the survey does not give |
| 8 Approval; 9 National polls | The Margin takes both from Tipping Point. Fifty-Two Keys reads the same approval list itself, for its own windows. No separate file of every poll with every field yet |
| 10 Phasing polls in; 11 State polls | Built; state polls are collected and listed, and counted only in the versions under review (A). 5 found, 1 meets the rules |
| 13 National and state agreement | Not changed: the national number is set first and states are placed around it. Turnout-weighted adding-up is not built |
| 14 Correlated errors; 16 Long-range ranges | Ranges now come from the simulation and cannot leave 0 to 100. Coverage report in section 5; calendar rule waiting (B) |
| 15 Betting markets | Labelled on the page; decision C |
| 17 Validation; 18 Trying parts in and out | Back-test with state models; eight versions scored and kept. Not rebuilt as it stood on the day: the approval-and-economy model before its publication date, and Keys counts on first-published figures |
| 19 Electoral College | Tipping-point chances, ties and splits from the same simulations. Paths to victory not built |
| 20 Automation; 21 Failures; 22 Archives | Built and checked by hand both ways; archives are write-once and now carry upstream versions. Scheduled starts are GitHub's and are not dependable yet (section 6) |
| 23 What moved | As before: parts are swapped in one at a time, so the split depends on the order. Not rebuilt |
| 24 Site; 26 Links between sites | Display defects fixed; three-site table and links added. No polling page, forecast-history page or scenario tool on The Margin yet |
| 25 Scenario lab; 28 Congress and governors | Not started, as instructed |
| 27 Methodology pages; 31 Governance | Model and Research tabs, `README.md`, `REVIEW.md`, this file. Official and under-review versions are separate in code and on record |
| 29 Accessibility | Not audited in this round |
| 30 Tests | The Margin 17 Python tests and two browser tests; Fifty-Two Keys 31; Tipping Point's own. All pass |
| 32 Independent review | Not done in this round |
