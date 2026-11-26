# The three sites: the method as frozen, the evidence, and what runs by itself

Written by `status.py` on the forecast of 2026-11-25. Every figure in a table is read from a data file; misses are in
points of margin. `RUNBOOK.md` says how the sites are kept running. `REVIEW.md` holds the earlier research.

## 1. The official method

The Margin's forecast is made in this order. It gives no weight to Fifty-Two Keys or to prediction markets.

1. **A national starting point, before polls.** The average of the approval equation (net approval in June of the election
   year, growth, and time in office, fitted on 1948 to the election before), today D+4.1, and Tipping Point's
   approval-and-economy model, today D+4.1. Tipping Point's long-range model joins from November 7, 2027, when the
   polls it is built on exist. Together today: D+4.1.
2. **An allowance for approval still moving: 15 points of net approval** at the midterm, shrinking with the square root of
   the time left, closing only when The Margin itself finds ten June 2028 days in the Nowcast's approval series. It counts
   by the structural models' share of the national number, so it is not added to the part polls already carry. Today 100%
   of it is open.
3. **National polls, by the calendar:** what the record says polls at this distance have been worth. Today 3%, on 28
   polls (R+2.4). The national number is D+4.0.
4. **The states.** The national number plus where each state sits against the nation: half its lean in the last two elections,
   half where Tipping Point's two models place it. State polls move it by a share that grows with their number and the calendar.
5. **Each state's own error,** sized from how far that state has landed from its starting point in the last five elections,
   pulled toward the common size as if by four more elections. Small and lopsided states get wider intervals than large,
   close ones.
6. **40,000 simulated elections,** with one national error, a regional one and each state's own. Everything shown is
   counted from the same simulated elections: who wins, the electoral votes, each state's 80% prediction interval, the
   national vote, and the chance of winning the vote and losing the Electoral College.

| 2028, as of 2026-11-25 | |
|---|---|
| Democrats win the Electoral College | 69.0% |
| Republicans win | 30.4% |
| A 269 to 269 tie, counted for neither | 0.6% |
| National vote, from the simulated elections | D+3.9; 80% prediction interval D+11.7 to R+4.0 |
| Democrats win the most votes | 75% |
| Democratic electoral votes | 299; 80% prediction interval 222 to 389 |
| The national number less the states added up | -0.03 points |

**Where the change of November 25 came from** (`method_change.py`). The Democratic chance went from 60.9% to 69.7% that day.
Nothing had happened in the race. Run on the day's inputs with each change of method switched on and off in every combination,
on the same random draws, and each credited with its average effect over every order:

| Change | Points of Democratic chance |
|---|---|
| State models used for where they place each state, not for their forecast as it stands | +5.9 |
| Early polls counted for 3%, not 24% | +2.2 |
| Fifty-Two Keys taken out | +0.6 |
| The approval-and-economy model added | +0.2 |
| **Together** | **+8.8** |
| Later the same day: the approval allowance from 10 to 15, counted by the structural share | -1.7 |
| Later the same day: each state's error sized on its own recent record | +1.0 |

The two ends of the first block are the forecasts kept that day (60.8%, 69.7%). The largest part is not the one the
change was known for: Tipping Point's models carry their own, lower, national level, and using them only for where they
place each state removed that pull on every state at once. The headline had also been taken off betting markets earlier
that day (62% to 60%); that was a change to what was shown and is not split here. Every kept forecast is untouched in
`docs/archive/`; the first one under the new method is labelled "a new day" where it should read "the method", and
`docs/archive/notes.json` carries that correction without touching the forecast.

## 2. The evidence for the method

The official method against the one before it, on 2008 to 2024 (`backtest.py`):

|  | 120 days | 90 days | 60 days | 30 days | 14 days | 7 days | last day |
|---|---|---|---|---|---|---|---|
| National miss, official method | 1.06 | 1.24 | 1.14 | 1.98 | 2.32 | 1.88 | 1.74 |
| National miss, method before | 2.04 | 2.14 | 1.83 | 2.47 | 2.17 | 1.90 | 1.72 |
| State miss, official | 3.80 | 3.76 | 3.68 | 4.17 | 4.29 | 3.84 | 3.69 |
| State miss, before | 3.86 | 3.95 | 3.82 | 4.15 | 4.22 | 3.81 | 3.66 |
| Favored the winner, official | 4 of 5 | 4 of 5 | 4 of 5 | 4 of 5 | 4 of 5 | 4 of 5 | 4 of 5 |
| Favored the winner, before | 4 of 5 | 4 of 5 | 3 of 5 | 3 of 5 | 4 of 5 | 4 of 5 | 4 of 5 |
| Log loss for the winner, official | 0.38 | 0.51 | 0.51 | 0.60 | 0.66 | 0.51 | 0.49 |
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

Read 2026-11-26T03:18Z: Polymarket 51, Kalshi 62, Manifold 61 markets; 56 of the 56 states and districts priced.

| Democrats win, 2026-11-26T03:18Z |  |  |
|---|---|---|
| Official forecast | 69.0% | no markets |
| Polymarket | 66.8% | $3,011,901 traded |
| Kalshi | 66.5% | $932,547 traded |
| Manifold | 67.5% | 118 traders, play money |
| Markets together, by quality | 66.8% |  |
| Market-informed run (experimental) | 68.4% | 49 prices; 87% of the simulated elections effectively kept |
| Market-informed, national markets only | 68.1% | 2 prices |
| Market-informed, state markets only | 69.2% | 47 prices |
| Market-informed, national and state markets, at half strength | 68.7% | 49 prices |

**The experimental run** (`markets.informed`). It never moves a headline. It weights the official simulated elections so
that each priced event's chance moves toward the market's by half the market's quality on the log-odds scale; a thin market
moves next to nothing. Whole elections are weighted, so the chance of winning, ties, each state, the electoral votes, the
national vote and its interval stay consistent. If fewer than a quarter of the elections would effectively remain, every
pull is halved. A winning chance does not fix a margin: nothing is said about any margin except through which simulated
elections count for more.

**What history can say** (`market_study.py`). State markets with a readable price history exist for one election, 2024.
On the states Polymarket priced, at nine distances from 200 days to the last day:

| 2024, mean over nine distances | Log loss | Brier score | States called | Chance given to the winner | Better than the forecast at |
|---|---|---|---|---|---|
| The forecast alone | 0.101 | 0.027 | 46.6 | 64% |  |
| Polymarket alone | 0.128 | 0.032 | 46.1 | 56% | 2 of 9 |
| Manifold alone | 0.178 | 0.050 | 44.3 |  | 0 of 9 |
| Half and half with Polymarket, state by state | 0.107 | 0.028 | 47.0 |  | 2 of 9 |
| Weighted elections: national price only | 0.103 | 0.028 | 46.7 | 60% | 3 of 9 |
| Weighted elections: state prices only | 0.105 | 0.028 | 47.0 | 60% | 3 of 9 |
| Weighted elections: national and state prices | 0.105 | 0.028 | 47.0 | 60% | 3 of 9 |
| Weighted elections: both, at half strength | 0.102 | 0.027 | 46.9 | 62% | 3 of 9 |

The forecast scored better than the markets on the whole and the markets better in the last two weeks; every way of mixing
them in landed between and was better than the forecast at 3 of 9 distances. That is one election, in which the states
shared one national miss, and the forecast's early figures are flattered by final data. Not checkable at all: any earlier
election at state level, any distance beyond about 250 days, and the quality rule itself (the record gives each market's
final volume, not its volume on the day).

**Recommendation: no weight.** The evidence does not show markets adding to the forecast, and could not show it either
way. The official forecast stays statistical. The market-informed run is made beside it on every forecast and kept, so by
November 2028 there is a record to judge on. The largest disagreement today is Texas: markets 40%, forecast 15%.

## 4. Prediction intervals

**What was found** (`interval_study.py`; states, 2008 to 2024, as the method now stands):

| Days out | 50% interval held | 80% held | 90% held | 95% held | Width of the 80% interval | Interval score | Missed on the Republican side | On the Democratic side |
|---|---|---|---|---|---|---|---|---|
| 250 | 78% | 93% | 97% | 99% | 20.6 | 2.23 | 5% | 2% |
| 200 | 77% | 93% | 97% | 98% | 20.1 | 2.17 | 6% | 1% |
| 150 | 76% | 92% | 97% | 99% | 19.9 | 2.14 | 6% | 2% |
| 120 | 72% | 92% | 97% | 99% | 19.1 | 2.12 | 6% | 2% |
| 90 | 70% | 92% | 96% | 98% | 19.1 | 2.14 | 6% | 1% |
| 60 | 74% | 92% | 96% | 99% | 18.5 | 2.07 | 6% | 2% |
| 30 | 62% | 88% | 94% | 97% | 16.6 | 2.14 | 10% | 2% |
| 14 | 62% | 84% | 95% | 98% | 16.7 | 2.17 | 15% | 1% |
| 7 | 62% | 89% | 96% | 98% | 16.1 | 1.99 | 10% | 0% |
| last day | 62% | 90% | 96% | 98% | 15.4 | 1.92 | 9% | 1% |

The intervals hold more than they claim: the 80% interval held 90% of state results on the last day and more further out.
The national vote fell inside its 80% interval every time and the electoral votes in 88% of cases. Misses fall on the
Republican side far more often than the Democratic: the polls' miss of 2016, 2020 and 2024.

**The parts, and whether any is counted twice.**

| Part | Size, and what was checked |
|---|---|
| National error | The error a mix of polls and structural models has made at each distance since 1976. On the last day about 3.4 points of margin against a realized 2.0 over five elections; five values cannot tell 2.0 from 3.4 |
| Approval still moving | 15 points of net approval, which is 4.5 points of margin today. Counted by the structural share, so it does not sit on top of the drift the polls' own error already holds. The record's structural error is measured with June approval known, so the allowance is not in it twice |
| Two years out, checked independently | The approval equation run with the midterm's approval in place of June's missed by 11.07 points over 13 elections and 6.48 since 2000; approval moving accounts for 5.81 and 4.68. The forecast allows about 6.4 in all and 4.5 for approval: in line with the record since 2000, well under the longer one |
| Economic and candidate uncertainty | Not separate terms. They are inside the record's error for the structural models; candidates enter through the spread between poll pairings, which lowers the polls' weight and adds no width |
| State polls | Each state's poll error is measured against the national average, so the national miss is not in it twice |
| Regional error | 40% of each state's own error is shared with its region; it changes how states move together, not how wide one state's interval is |
| State's own error | Was one size for all, measured since 1980. Now each state's own, from the last five elections (below) |
| Model disagreement | The two structural models are averaged; their gap is not added as width |
| Prediction markets | Not in the forecast |

**The one thing that was too wide, and is changed.** A state's error was sized on every election since 1980 with one figure
for all states. States moved about more then than since 2000, and some states are steadily harder to place than others
(small and lopsided ones miss by about 7.4 points, large and close ones by about 5.4; a state's size of miss in one half
of the record predicts its size in the other, correlation 0.26). Eight ways of sizing it were written down and run
through the whole simulation, each using only earlier elections:

| Way of sizing a state's error | Interval score | Better than the earlier sizing in | 50% held | 80% held | 95% held | Width of the 80% | 80% held, by election, last day | Narrowest and widest state |
|---|---|---|---|---|---|---|---|---|
| Until November 25, 2026: every election since 1980, one size for all states | 2.19 | 0 of 5 | 73% | 93% | 98% | 19.6 | 90%, 96%, 82%, 90%, 96% | 13.8 to 18.0 |
| Last 5 elections, one size | 2.129 | 5 of 5 | 70% | 91% | 98% | 18.2 | 90%, 94%, 80%, 88%, 94% | 12.4 to 16.6 |
| As published: last 5 elections, each state its own, pulled as if by 4 | 2.109 | 5 of 5 | 70% | 91% | 98% | 18.2 | 90%, 96%, 80%, 90%, 94% | 12.1 to 20.2 |
| Last 5, pulled as if by 2 | 2.105 | 5 of 5 | 69% | 90% | 98% | 18.2 | 90%, 96%, 76%, 90%, 94% | 12.0 to 21.3 |
| Last 5, pulled as if by 8 | 2.114 | 5 of 5 | 70% | 91% | 98% | 18.2 | 90%, 94%, 80%, 90%, 94% | 12.2 to 19.0 |
| Last 3 elections, pulled as if by 4 | 2.104 | 5 of 5 | 69% | 90% | 98% | 17.8 | 90%, 94%, 78%, 88%, 94% | 11.6 to 19.2 |
| Last 7 elections, pulled as if by 4 | 2.133 | 5 of 5 | 71% | 91% | 99% | 18.9 | 90%, 94%, 80%, 90%, 94% | 13.5 to 20.4 |
| Every election since 1980, each state its own, pulled as if by 4 | 2.166 | 4 of 5 | 73% | 92% | 99% | 19.6 | 90%, 96%, 82%, 92%, 94% | 13.5 to 22.9 |

Sizing each state on its own recent record, pulled toward the common size, scored better in all five elections and is
adopted. Intervals are about 7% narrower on average, and no longer the same for every state.

**Why not narrower still.** Scaling the national and state errors down, choosing the scales on four elections and scoring
on the fifth, brings average coverage to the nominal 80% and improves the score in four elections:

| Left out | National error scaled by | State error scaled by | Interval score | As published | 80% held | As published | 95% held | As published |
|---|---|---|---|---|---|---|---|---|
| 2008 | 0.6 | 0.7 | 2.485 | 2.509 | 76% | 89% | 89% | 98% |
| 2012 | 0.6 | 0.8 | 1.681 | 1.931 | 92% | 98% | 98% | 100% |
| 2016 | 0.6 | 0.6 | 3.02 | 2.681 | 55% | 75% | 72% | 94% |
| 2020 | 0.6 | 0.8 | 1.677 | 1.848 | 82% | 94% | 98% | 100% |
| 2024 | 0.6 | 0.8 | 1.301 | 1.576 | 94% | 98% | 99% | 100% |

and in the fifth, 2016, the 80% intervals would have held 55% and the 95% intervals 72%. Every held-out choice
also put the national scale at the lowest value on offer, which says the five national misses were small, not that the
next one will be. Fifty states share an election's national miss, so this is five tests, and one of the five says the
width was needed. The remaining over-coverage is left in. That is a judgment between two risks and is stated as one.

**Cannot be validated yet:** anything about intervals more than 250 days out for states (the back-test has no polls that
early and runs the structural models on final figures), and the shape of the allowance's shrinking between now and June 2028.

## 5. The states: Texas, Florida, and whether trends or midterms would help

Closed, and not reopened. The framework is kept: no rule for a state's lean beat the one in use by more than chance would,
trends do not persist (correlation -0.06 between a state's move in one election and the next), and midterm House results
did not help. `state_trend_study.py` and `data/state_trend_study.json` hold the study.

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
| Democrats win it | 15 in 100 | 22 in 100 |
| If the last election alone set the lean | R+12.4 | R+11.7 |
| If a quarter of the 2020 to 2024 move were carried forward | R+12.9 | R+12.7 |

## 6. Running by itself

Each site checks its sources every hour, stops if nothing is new, and otherwise recalculates, archives and publishes. A new
official forecast is made only for what the forecast reads; a move in prediction markets alone refreshes the comparison.

| Seen in production, November 25 and 26, 2026 (UTC) | |
|---|---|
| A run started by GitHub's own schedule | The Margin, November 26, 01:56. The first since the hourly schedules went in eight hours earlier: the schedule works, late |
| Tipping Point and Fifty-Two Keys notify The Margin; it runs within a minute | 19:01, 21:48, 22:29, 23:06 |
| A check asked for the way the outside clock will ask | all three sites, 23:12 to 23:40: each found nothing new and saved nothing |
| Prediction markets read at three providers, kept, and shown | November 26, 03:18: Polymarket 51, Kalshi 62 and Manifold 61 markets; all 56 states and districts priced; the national race at all three |
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
- **No nominees.** Every 2028 poll pairs people who may never face each other. Polls count for 3% of the national number.
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
