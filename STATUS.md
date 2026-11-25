# The three sites: the method as frozen, the evidence, and what runs by itself

Written by `status.py` on the forecast of 2026-11-25. Every figure in a table is read from a data file; misses are in
points of margin. `RUNBOOK.md` says how the sites are kept running. `REVIEW.md` holds the earlier research.

## 1. The official method

The Margin's forecast is made in this order. Nothing in it reads Fifty-Two Keys or betting markets.

1. **A national starting point, before polls.** The average of two things, and of a third once it exists:
   the approval equation (net approval in June of the election year, growth, and time in office, fitted on 1948 to the
   election before), today D+4.1; Tipping Point's approval-and-economy model, today D+4.1; and Tipping
   Point's long-range model, which is built on polls and so is left out until November 7, 2027 and then phased in, today
   not in. Together: D+4.1.
2. **An allowance for approval still moving.** Net approval is -30.8 now and the equation wants its June 2028 value. The
   allowance is 10 points of net approval at the midterm, shrinks with the square root of the time left, and closes only when
   The Margin itself finds at least ten June 2028 days in the Nowcast's approval series (from July 8, 2028). If June is late,
   a month's worth stays open. Today 100% of it is open.
3. **National polls, by the calendar.** Polls count for what the record says polls at this distance have been worth:
   about 3% two years out, 11% at 250 days, 24% at 120, 61% on the last day. Today 3%, on 28 polls (R+2.4).
   The national number is D+4.0.
4. **The states.** Each state starts from the national number plus where the state sits against the nation: half from its
   lean in the last two elections (three parts 2024, one part 2020), half from where Tipping Point's two models place it
   against their own national figure. State polls move it by a share that grows with their number and with the calendar.
5. **40,000 simulated elections.** One national error for all states, a regional error shared by neighbours, and each
   state's own. Every figure on the page is counted from these same simulated elections: who wins, the electoral votes, each
   state's range, the national vote (each election's states added up by the votes they cast in 2024), and the chance of
   winning the vote and losing the Electoral College.

| 2028, as of 2026-11-25 | |
|---|---|
| Democrats win the Electoral College | 70 in 100 |
| Republicans win | 30 in 100 |
| A 269 to 269 tie, counted for neither | 7 in 1,000 |
| National vote, from the simulated elections | D+3.9; four in five between D+11.1 and R+3.3 |
| Democrats win the most votes | 77 in 100 |
| Democratic electoral votes | 298; four in five between 227 and 379 |
| Win the vote, lose the Electoral College | Democrats 9 in 100, Republicans 2 in 100 |
| The national number less the states added up | -0.03 points |

The method was adopted on November 25, 2026 and is frozen from that day (section 9). On the day of the change the Democratic
chance moved from 60 to 70 in 100. Almost none of that comes from dropping Fifty-Two Keys' line: with the line left in,
the same method gives 70 in 100 today. It comes from the rest of the approved change: early polls counted for 3% and not
24%, the approval-and-economy model added, and state models used for placing only. Every forecast kept before the change is untouched in `docs/archive/`; the change is recorded in
`data/methods.json` and marked on the page's history chart. The method before it stays in the code as `model.PREVIOUS`, and
four other versions are still run on every forecast and written to the data file, so that in 2028 they can be scored beside
the official one. They are not shown as the forecast.

## 2. The evidence for it

The official method against the one before it, on 2008 to 2024 (`backtest.py`):

|  | 120 days | 90 days | 60 days | 30 days | 14 days | 7 days | last day |
|---|---|---|---|---|---|---|---|
| National miss, official method | 1.06 | 1.24 | 1.14 | 1.98 | 2.32 | 1.88 | 1.74 |
| National miss, method before | 2.04 | 2.14 | 1.83 | 2.47 | 2.17 | 1.90 | 1.72 |
| State miss, official | 3.80 | 3.76 | 3.68 | 4.17 | 4.29 | 3.84 | 3.69 |
| State miss, before | 3.86 | 3.95 | 3.82 | 4.15 | 4.22 | 3.81 | 3.66 |
| Favored the winner, official | 4 of 5 | 4 of 5 | 4 of 5 | 4 of 5 | 4 of 5 | 4 of 5 | 4 of 5 |
| Favored the winner, before | 4 of 5 | 4 of 5 | 3 of 5 | 3 of 5 | 4 of 5 | 4 of 5 | 4 of 5 |
| Log loss for the winner, official | 0.38 | 0.50 | 0.50 | 0.58 | 0.65 | 0.51 | 0.48 |
| Log loss for the winner, before | 0.43 | 0.63 | 0.58 | 0.61 | 0.65 | 0.51 | 0.48 |

Why Fifty-Two Keys is out (`keys_study.py`, ten distances from 250 days to the last day):

| Mean over ten distances, 250 days to the last day | National miss | Of which toward the Democrats | State miss | Chance given to the winner | Brier score, winner | Log loss, winner | Favored the winner (of 5), fewest |
|---|---|---|---|---|---|---|---|
| Published | 2.15 | +2.01 | 3.93 | 67% | 0.182 | 0.538 | 3 |
| Hybrid: Keys as an equal part | 1.85 | +1.74 | 3.95 | 68% | 0.169 | 0.503 | 4 |
| Keys at half weight | 1.66 | +1.52 | 3.89 | 69% | 0.164 | 0.493 | 4 |
| Keys line fitted on the last ten elections | 1.71 | +1.59 | 3.91 | 69% | 0.164 | 0.492 | 4 |
| **No Keys (recommended)** | 1.45 | +1.22 | 3.85 | 69% | 0.159 | 0.480 | 4 |
| No Keys in the vote; the count used as a sign of the winner | 1.45 | +1.22 | 3.85 | 68% | 0.205 | 0.598 | 3 |

The more of the Keys line there is, the worse every measure gets. Taken alone the line missed the national margin by 4.3
points on average, each time toward the Democrats. Used only as a sign of the winner it made every winner score worse.

What this does not show. Five elections; ten distances from one election are not ten elections. The approval-and-economy
model's forecast is the one its authors' method gives about 100 days out, used at every distance, which flatters the
early distances. The real test is 2028, which is why the method is frozen now.

## 3. The states: Texas, Florida, and whether trends or midterms would help

**Why Texas is projected more Republican than Florida.** They voted alike in 2024. Nothing was adjusted by hand; this is
what each part says.

|  | Texas | Florida |
|---|---|---|
| 2020 result | R+5.7 | R+3.4 |
| 2024 result | R+13.9 | R+13.2 |
| 2020 against the nation | R+10.2 | R+7.9 |
| 2024 against the nation | R+12.4 | R+11.7 |
| Lean used (three parts 2024, one part 2020) | R+11.8 | R+10.8 |
| Approval-and-economy model, against its own national figure | R+11.6 | R+7.5 |
| Long-range model, against its own national figure | R+12.3 | R+9.6 |
| The two models together | R+11.9 | R+8.6 |
| Presidential approval in the state | 34.8% | 36.0% |
| State economy index | -0.21 | -0.26 |
| Starting point against the nation: half lean, half the models | R+11.9 | R+9.7 |
| National number | D+4.0 | D+4.0 |
| State polls for 2028 | none | none |
| Forecast | R+7.9 | R+5.7 |
| Democrats win it | 18 in 100 | 26 in 100 |
| If the last election alone set the lean | R+12.4 | R+11.7 |
| If a quarter of the 2020 to 2024 move were carried forward | R+12.9 | R+12.7 |

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

| Rule for a state's lean | Elections scored | Typical miss | The rule in use, same elections | Closer in | Difference (standard error) |
|---|---|---|---|---|---|
| As used: 0.75 and 0.25 | 11 (from 1984) | 5.01 | 5.01 | 0 of 11 | +0.00 (0.0) |
| The last election alone | 11 (from 1984) | 4.89 | 5.01 | 6 of 11 | -0.12 (0.15) |
| The last two evenly | 11 (from 1984) | 5.44 | 5.01 | 2 of 11 | +0.42 (0.14) |
| The last three: 0.6, 0.3, 0.1 | 11 (from 1984) | 5.08 | 5.01 | 3 of 11 | +0.07 (0.16) |
| Trend, a quarter carried forward | 11 (from 1984) | 5.11 | 5.01 | 6 of 11 | +0.09 (0.3) |
| Trend, a half carried forward | 11 (from 1984) | 5.63 | 5.01 | 4 of 11 | +0.62 (0.43) |
| Trend, share fitted on earlier elections | 11 (from 1984) | 5.05 | 5.01 | 6 of 11 | +0.04 (0.09) |
| Midterm House lean, a fifth of the way to it | 7 (from 2000) | 4.49 | 4.29 | 2 of 7 | +0.20 (0.15) |
| Midterm House lean, share fitted | 6 (from 2004) | 4.14 | 4.09 | 0 of 6 | +0.05 (0.01) |
| Move between the last two midterms, a quarter of it | 6 (from 2004) | 4.53 | 4.09 | 1 of 6 | +0.44 (0.16) |
| Move between midterms, share fitted | 5 (from 2008) | 4.23 | 4.17 | 3 of 5 | +0.06 (0.09) |

| With the state models in, 2008 to 2024 | Typical miss |
|---|---|
| As used: 0.75 and 0.25 | 3.96 |
| The last election alone | 3.89 |
| Trend, a quarter carried forward | 3.93 |
| Trend, share fitted on earlier elections | 3.90 |
| Midterm House lean, a fifth of the way to it | 3.89 |
| Move between the last two midterms, a quarter of it | 3.91 |

- **Trends do not persist.** A state's move against the nation in one election says almost nothing about its move in the
  next: the correlation is -0.06 over 561 cases and -0.01 since 2008. The share of a trend that would have been best to
  carry forward is slightly negative in every election (-0.11 to +0.00). Carrying a quarter forward was no better; a half was worse.
- **Midterms do not help.** Moving a fifth of the way to the midterm House lean was worse in 5 of 7 elections, and the best
  share to use was about zero (-0.01).
- **The last election alone** was closer than the rule in use in 6 of 11 elections, by 0.12 points with a standard error of
  0.15: not distinguishable from no difference. With the state models in, every rule lands between 3.89 and 3.96.

**Conclusion: the framework is kept as it is.** No rule beat the one in use by more than chance would, and the two that
would move Texas and Florida closer (trends, the last election alone) have no reliable record. The 2026 House vote is not in
the source file yet and was not used. Tipping Point's models are untouched.

## 4. The allowance for approval still moving

It stays at 10 points, as instructed. What the record says (`data/approval_moves.json`):

| Net approval, midterm reading to June of the election year | Terms | Mean change | Mean size of the change | Median size | Standard deviation | Root mean square | Within 10 | Within 15 | Within 20 |
|---|---|---|---|---|---|---|---|---|---|
| Every term since 1950 (19) | 19 | -5.7 | 16.8 | 16.4 | 20.1 | 20.4 | 6 of 19 | 9 of 19 | 13 of 19 |
| Since 1980 (12) | 12 | -8.5 | 19.3 | 17.4 | 22.7 | 23.4 | 4 of 12 | 4 of 12 | 7 of 12 |
| Since 2000 (7) | 7 | -5.6 | 12.3 | 8.8 | 16.6 | 16.3 | 4 of 7 | 4 of 7 | 6 of 7 |
| The five most recent | 5 | +0.7 | 8.7 | 3.2 | 12.5 | 11.2 | 3 of 5 | 3 of 5 | 5 of 5 |

The "20" and "11" quoted before were root-mean-square changes: the spread about no change at all, for every term and for
the five most recent. That is the right measure here, because the forecast assumes no trend and the allowance is used as one
standard deviation. If the allowance is right, about two terms in three should fall within it. At 10, a third of all terms
do and three of the last five; at 20, two thirds of all terms and all of the last five.

**Recommendation: 15.** Ten is below every estimate in the table, including the one from the five most polarised terms
(11.2), and five terms cannot pin a spread down: the range that five observations with that spread are consistent with
runs from about 7 to about 27. Twenty fits the whole record but includes the swings of 1980 and 1992, larger than anything
since approval hardened along party lines. Fifteen sits between the five-term figure and the seven-term figure (16.3), and
at 15 the count of recent terms inside it is the same as at 10. This was written before measuring what it does to the
forecast. For the record, measured afterwards: Democrats 70 in 100 at 10, 68 at 15, 66 at 20; the range of the national
margin 14.4, 16.3 and 18.6 points wide. The closing rule is the same at any size. The change is one number in
`data/inputs.json` (`approval_drift`) and a line in `data/methods.json`; it is yours to make.

## 5. How wide the ranges are

On the last day the ranges held more results than four in five on average, but in 2016 they needed nearly all their width.
They are left as they are.

| Last day, 2008 to 2024 | Forecasts | Result inside the range | More Republican than the range | More Democratic | Width of the range, points | Typical miss |
|---|---|---|---|---|---|---|
| All states and the District | 255 | 91% | 8% | 1% | 15.9 | 3.7 |
| Projected within 10 points | 84 | 94% | 6% | 0% | 15.4 | 3.3 |
| Projected 10 to 30 points apart | 136 | 91% | 8% | 1% | 16.0 | 3.9 |
| Projected 30 points or more apart | 35 | 86% | 11% | 3% | 16.3 | 3.6 |
| Leaning Democratic | 131 | 96% | 2% | 2% | 15.5 | 3.1 |
| Leaning Republican | 124 | 86% | 14% | 0% | 16.3 | 4.3 |

| Election | Result inside the range | More Republican than the range | More Democratic | Share of the range's width that would have held four results in five |
|---|---|---|---|---|
| 2008 | 90% | 8% | 2% | 68% |
| 2012 | 96% | 2% | 2% | 59% |
| 2016 | 82% | 18% | 0% | 97% |
| 2020 | 90% | 10% | 0% | 83% |
| 2024 | 98% | 2% | 0% | 40% |

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
| A check asked for from outside, the way an outside clock would ask (`workflow_dispatch`, check only) | Tipping Point 23:12 and Fifty-Two Keys 23:12: both found nothing new and saved nothing. The Margin: see RUNBOOK |
| A `heartbeat` check | all three, 22:28 to 22:47 |
| The official method published and kept | 23:14, `docs/archive/2026-11-25T2314Z.json` |
| The forecasters' survey read from the Philadelphia Fed | gave the figures that had been typed |
| The Bureau of Labor Statistics read as a second source | 23:28: "gives the same 11 figures" for the unemployment rate |
| Polls naming a third candidate read from PollResults.org | every Fifty-Two Keys run |
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
