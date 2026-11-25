# Where the three sites stand

Written by `status.py` on the forecast of 2026-11-25. Every figure in a table is read from a data file. Misses are in
points of margin. `RUNBOOK.md` says how the sites are kept running; `REVIEW.md` holds the earlier research.

Each line below is marked: **live** (deployed and seen working on the public site or in GitHub's record), **tested** (passes
its tests here; not yet seen in production because the event has not happened), **under review** (built, run beside the
published forecast, waiting for your word), or **open**.

## 1. What changed in this round

| | Status |
|---|---|
| The headline is the simulations' own number: Democrats 60 in 100, Republicans 39, a 269 to 269 tie 8 in 1,000, counted for neither. Betting markets are shown beside it. Forecasts kept before the change are untouched; the change is in `data/methods.json` and marked on the history chart | live |
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

| Mean over ten distances, 250 days to the last day | National miss | Of which toward the Democrats | State miss | Chance given to the winner | Brier score, winner | Log loss, winner | Favored the winner (of 5), fewest |
|---|---|---|---|---|---|---|---|
| Published | 2.15 | +2.01 | 3.93 | 67% | 0.182 | 0.538 | 3 |
| Hybrid: Keys as an equal part | 1.85 | +1.74 | 3.95 | 68% | 0.169 | 0.503 | 4 |
| Keys at half weight | 1.66 | +1.52 | 3.89 | 69% | 0.164 | 0.493 | 4 |
| Keys line fitted on the last ten elections | 1.71 | +1.59 | 3.91 | 69% | 0.164 | 0.492 | 4 |
| **No Keys (recommended)** | 1.45 | +1.22 | 3.85 | 69% | 0.159 | 0.480 | 4 |
| No Keys in the vote; the count used as a sign of the winner | 1.45 | +1.22 | 3.85 | 68% | 0.205 | 0.598 | 3 |

| National miss | 250 days | 200 days | 150 days | 120 days | 90 days | 60 days | 30 days | 14 days | 7 days | last day |
|---|---|---|---|---|---|---|---|---|---|---|
| Published | 2.66 | 2.46 | 2.12 | 2.04 | 2.14 | 1.83 | 2.47 | 2.17 | 1.90 | 1.72 |
| Hybrid: Keys as an equal part | 1.68 | 1.70 | 1.62 | 1.72 | 1.83 | 1.59 | 2.24 | 2.38 | 1.94 | 1.80 |
| Keys at half weight | 1.34 | 1.38 | 1.33 | 1.44 | 1.58 | 1.37 | 2.13 | 2.36 | 1.92 | 1.77 |
| Keys line fitted on the last ten elections | 1.46 | 1.49 | 1.43 | 1.54 | 1.67 | 1.44 | 2.20 | 2.30 | 1.87 | 1.73 |
| **No Keys (recommended)** | 1.14 | 0.96 | 1.07 | 1.06 | 1.24 | 1.14 | 1.98 | 2.32 | 1.88 | 1.74 |

| Log loss for the winner | 250 days | 200 days | 150 days | 120 days | 90 days | 60 days | 30 days | 14 days | 7 days | last day |
|---|---|---|---|---|---|---|---|---|---|---|
| Published | 0.46 | 0.61 | 0.44 | 0.43 | 0.63 | 0.58 | 0.61 | 0.65 | 0.51 | 0.48 |
| Hybrid: Keys as an equal part | 0.41 | 0.47 | 0.41 | 0.41 | 0.53 | 0.52 | 0.60 | 0.66 | 0.52 | 0.49 |
| Keys at half weight | 0.40 | 0.46 | 0.40 | 0.40 | 0.52 | 0.51 | 0.59 | 0.66 | 0.52 | 0.49 |
| Keys line fitted on the last ten elections | 0.40 | 0.46 | 0.40 | 0.39 | 0.51 | 0.51 | 0.60 | 0.66 | 0.51 | 0.48 |
| **No Keys (recommended)** | 0.38 | 0.43 | 0.38 | 0.38 | 0.50 | 0.50 | 0.58 | 0.65 | 0.51 | 0.48 |
| No Keys in the vote; the count used as a sign of the winner | 0.46 | 0.53 | 0.47 | 0.47 | 0.62 | 0.62 | 0.75 | 0.79 | 0.65 | 0.63 |

Among the versions of the hybrid every average is best with the Keys left out, and the order is the same on every measure:
the more of the Keys line there is, the worse the forecast. That holds for the vote (national and state misses, and the lean
toward the Democrats) and for the winner (Brier score and log loss). On the national miss it holds at eight of the ten
distances and is within 0.02 at the other two. Against the published forecast the version without the Keys is closer from
250 days to 30 days and level in the last fortnight (2.32 against 2.17 at 14 days, 1.74 against 1.72 on the last day).

Why. The Keys line, taken alone, missed the national margin by more than any other part and always the same way:

| Each part alone, miss on the national margin | 2008 | 2012 | 2016 | 2020 | 2024 | Typical size | Mean, toward the Democrats |
|---|---|---|---|---|---|---|---|
| Keys line | +4.8 | +7.8 | +4.4 | +0.8 | +3.8 | 4.3 | +4.3 |
| Keys line, last ten elections | +3.4 | +7.6 | +2.4 | +0.5 | +3.0 | 3.4 | +3.4 |
| Approval equation | +5.5 | +2.7 | -1.8 | -5.1 | +0.7 | 3.1 | +0.4 |
| Approval-and-economy model | +3.6 | -3.6 | +0.4 | +4.5 | +0.5 | 2.5 | +1.1 |
| Long-range model | -2.1 | +3.6 | -1.9 | +5.1 | +2.4 | 3.0 | +1.4 |

As a sign of the winner the count did no better. Laid over the simulations with its own past record (shrunk halfway to a coin
toss, because the keys were chosen with the results in view), it made every winner score worse:

| Election | Count | The count called | Right? | Its record before, as used |
|---|---|---|---|---|
| 2008 | 26% | Democrats | yes | 66% |
| 2012 | 70% | Democrats | yes | 66% |
| 2016 | 62% | Democrats | no | 67% |
| 2020 | 38% | Democrats | yes | 64% |
| 2024 | 53% | Democrats | no | 65% |

In all five elections the count pointed to the Democrats; three of the five went that way. Its record of 15 Electoral College
winners in 19 (17 for the national vote) is a record of rules written after the results were known.

What this does not show. Five elections; ten distances from the same election are not ten elections. Six versions were
scored on them, so a small gap between two versions means little: the case rests on the gap being large, in one direction,
and on every measure. The approval-and-economy model's forecast is the one made about 100 days out, used at every distance,
and the Keys counts use final figures: both flatter early forecasts, and the second flatters the Keys.

**Recommendation: give Fifty-Two Keys no weight in The Margin.** The version without it is `model.RECOMMENDED`. It is run on
every forecast and is not published until you say so.

| 2028, as of 2026-11-25 | Published | Hybrid | Recommended (no Keys) |
|---|---|---|---|
| Democrats win | 60 in 100 | 68 in 100 | 70 in 100 |
| National vote | D+3.1 | D+4.0 | D+4.0 |
| Democratic electoral votes, middle simulation | 284 | 298 | 298 |
| Four in five simulations | 214 to 364 | 222 to 386 | 227 to 379 |
| National number less the states added up | -0.32 | -0.03 | -0.03 |

For 2028 the choice moves little: today the Keys line (D+4.1) stands beside the other two parts (D+4.1 and D+4.1).
The difference from the published forecast comes from the rest of the hybrid: early polls counted for 3% and not 11%, and the
approval-and-economy model added. The recommendation is not made for the number it gives.

Fifty-Two Keys goes on as its own site. It calls a winner; it no longer gives an estimate of the vote.

## 3. The national number and the states

In the published forecast the states, added up by the votes each cast in 2024, come to 51.21% against a national number of
51.54%: 0.32 points apart. Half of each state's starting point is Tipping Point's forecast of that state as it stands,
which carries that site's lower national level into the states a second time. In the versions under review the state models
are used only for where they place each state against their own national figure, and the two agree to 0.03. The chance of
winning the most votes shown on the page is counted from the states added up (68 in 100), not from the national number alone.
Adopting the recommended version closes the gap; nothing else was needed.

## 4. How wide the ranges are

Unchanged, and the evidence is as before: on the last day the ranges held more results than four in five on average, but in
2016 they needed nearly all of their width.

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

1. **Make the version without Fifty-Two Keys the published forecast?** Recommended. Today: 60 in 100 to 70 in 100, national vote D+3.1 to D+4.0,
   284 to 298 electoral votes. It also brings the national number and the states into agreement. `RUNBOOK.md` has the steps; every
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
