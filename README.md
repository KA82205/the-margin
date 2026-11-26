# The Margin

A forecast of the 2028 presidential election: polling averages, structural models of the national vote and state leans,
run through a simulation of the Electoral College. It is back-tested on 2008 to 2024. The method was fixed on November 25,
2026 and is not changed before the election except to fix a fault (`STATUS.md`). The logo is a plus-or-minus sign:
`docs/logo.svg`.

## Where it stands (November 26, 2026, the day the method was fixed)

| | |
|---|---|
| Democrats win the Electoral College | 69% (Republicans 30%; a 269 to 269 tie 0.6%) |
| Democratic electoral votes | 299; 80% prediction interval 222 to 389 |
| National vote | Democrats by 3.9 points; 80% prediction interval -4.0 to +11.7 |
| Democrats win the most votes | 75% |

The election is 713 days away and neither party has a nominee. Read it as a lean. The page carries the current numbers.

## The site

One self-contained page, `docs/index.html`, with five tabs: **Forecast** (the map, the forecast day by day, the national
margin, the closest states), **States** (a profile of every state and district: how it has voted since 1976, its lean
against the nation, how its projection is built, every poll of it that the sources hold with the reason each is or is
not usable, and how often it decides the election; `#states/PA` opens one directly), **Model** (what goes in, why each weight, how the range narrows, sources and limits),
**Back-tests** (2008-2024 against the results, calibration, every distance from the election) and **Research** (a
notebook of questions about elections that stands apart from the forecast: how good expert ratings are, how far off the
polls have been, whether they miss everywhere at once, the Electoral College's tilt, approval and the vote, which states
are moving, and the primaries). Section headings share one device: a dark band across the
whole screen with a blue-to-red stripe under it, each color as wide as its share of the 538 electoral votes on the map. To add a contact link, set `CONTACT` at the top of `make_page.py`.

## Updates

`.github/workflows/update.yml` runs `python update.py` every hour. Most runs read the sources, find nothing new and
end there. A run

1. reads the Tipping Point Nowcast's file (national head-to-head polls, the two models' forecasts for the nation and each
   state, presidential approval among adults) and the state polls (below). The Fifty-Two Keys feed and the party odds from
   electionbettingodds.com are read too, for display only;
2. compares what it read with what the last forecast was made from (`data/fingerprint.json`: one short hash for the
   national polls, the Nowcast's forecasts, approval, the state polls, the method's settings and the day). The time a
   source was read, and the time another site made its file, are not in the fingerprint;
3. stops if nothing differs. Nothing is recalculated and nothing is saved;
4. otherwise reruns the forecast, keeps it in the archive if it differs from the last one kept, replaces the day's row in
   `data/history.csv`, rebuilds the page and commits, which republishes the site.

What counts as new: a poll added, changed or dropped; a move in the Nowcast's forecasts or its approval average; a change
to the method's settings; and the day itself. The first run of every day always goes through, so the day-by-day record has
every day and the poll weights, which depend on the date, keep up. A new Fifty-Two Keys count does not start a forecast. A move in
prediction markets refreshes the comparison beside the forecast and the record of prices; the official forecast is not made
again for it.

**The archive** (`docs/archive/`, on the site at `archive/index.json`). Every forecast that differs from the last one
kept is written to a file of its own, named for the time it was made, and never opened for writing again. "Differs"
means a tenth of a point in the chance, a twentieth of a point in the national share, a different middle count of
electoral votes, or the same in any one state. `data/history.csv` is the day-by-day record: one row a day, the day's
latest. The archive is the record of every version in between.

**When the other sites change.** The Nowcast and the Fifty-Two Keys feed are read every hour, so a change in either
reaches this forecast within the hour. It can be immediate: both of those repositories send a `repository_dispatch`
event (`upstream-updated`) when they publish something new, if they hold a secret named `DISPATCH_TOKEN`. That needs a
personal access token with permission to start workflows in this repository, which only the owner can create; without
it the hourly run does the same job a little later. A run started that way looks again for up to four minutes, since
the other site's page can take a minute or two to show what it has just saved.

**When something cannot be read.** The last value is kept and the run goes on with a warning. The day's first run, and
a run started by hand, end as failed if an input has gone stale: the Nowcast not read since the day before, or the state
polls not read for two days. So a source that is down for an hour sends nothing, and one that stays down is reported once
a day. The Fifty-Two Keys feed and the prediction markets cannot make a run fail: if one is not read the log says so and the page
shows the last copy. A run that fails for any other reason is tried again the next hour and marked as failed at 7 a.m.,
1 p.m. and 7 p.m. Eastern only.

**"Every hour" is what is asked of GitHub, not what GitHub promises.** GitHub starts scheduled runs when it has room.
In November 2026 it was starting this account's scheduled runs hours late (the Tipping Point runs asked for at 6:17 and
11:17 UTC began 6 to 12 hours later). A late run loses nothing but time, since every run is complete in itself, but how
often the checks really happen is GitHub's doing. A run started from outside (the "Run workflow" button, the event the
other two sites can send, or a call to GitHub's API by a clock somewhere else) starts at once. "Run workflow" has a box
to make the run as the hourly check does.

On a new day the previous day's inputs are kept as `data/prev_inputs.json`, `data/prev_nowcast.js` and
`data/prev_state_polls.json`. The page's "Forecast updates" box comes from them. What moved is split between national
polls, state polls, approval, Tipping Point's models and time, each credited with its average effect over every order in
which the parts could be swapped in, so the order does not matter and the parts add up.

Units: the scripts work in points of the two-party vote share. The page shows every miss in points of margin, which is
twice that (a typical state miss of 1.8 points of share is 3.7 points of margin).

The Fifty-Two Keys count (`keys`, `keys_mean`, `keys_sd` in `data/inputs.json`) is read from that site's own feed,
`https://ka82205.github.io/fifty-two-keys/keys.json`, and shown on the page beside the forecast. It is not used in it.

**The June 2028 approval reading.** The approval equation wants net approval in June of the election year. The Margin
finds it for itself in the Nowcast's daily approval series: from July 8, 2028, once at least ten June days are there, their
average is the reading and the allowance for approval still moving closes. No other site has to report anything.

## State polls

`polls.py` keeps `data/state_polls.json`: every head-to-head poll of a single state for the 2028 general election that
the sources hold, each marked usable or not, with the reason.

- **PollResults.org** (`api.pollresults.org/v1.0/politics/results/president`) serves The New York Times's poll data
  under CC BY 4.0, 100 polls a page with a cursor to the next, no key needed. Every poll carries the state it was taken
  in (`US` for the country) and each question says whether it is a primary or the general election. The script follows
  the cursor to the last page and stops if a page brings nothing new or after 40 pages, and says which.
- **VoteHub** (`api.votehub.com`, CC BY 4.0) lists no presidential general-election polls. Its list of poll types is
  read on every run, and the run warns when one for the presidential general election appears.
- **RealClearPolling** listed national pairings only among its 2028 general-election races when it was checked
  (November 25, 2026). It is not read by the script, and its data are not openly licensed.
- If PollResults.org cannot be reached, the copy of its feed that Tipping Point saves is read.

A poll's place is read from the state field and, for Maine and Nebraska, from the fields that can name a district. A
place that cannot be read (a territory, a region, two fields that disagree) is listed and never used: nothing is
guessed, and nothing unreadable is taken for a national poll. One question of one poll is counted once, whether the
feed repeats it on another page or gives one sample under two labels. A poll is not usable if it names no candidates
(a generic ballot), names somebody who cannot be elected again, was paid for by a party or a campaign, or, while the
nominees are not known, was taken in the home state of one of the two people it asks about. Those are the rules the
national polls already follow. The usable pairings of one poll in one state are averaged into one line.

So "no state polls" now means one of three things, and the file says which: the source could not be reached, the
source has none, or it has some and none is usable. As of November 25, 2026 the feed holds five state polls (Alaska,
Nevada, North Carolina twice, Pennsylvania). One meets the rules, an Alaska poll from September 2025, too old to count.
Before this the forecast read only the Nowcast's national list, which is why it had found none.

Each state's page lists its polls and says which meet the rules. **The published forecast does not count state polls
yet.** Its rule (a state's polls against a starting point worth 1.5 polls, whatever the distance from the election)
would hand a state to a handful of polls taken two years out; see `REVIEW.md`. The candidate counts them under a
ceiling that falls with distance.

## Run it

```
python prep.py                  # builds data/ from the downloaded sources in raw/
python backtest.py              # the back-test of the published forecast, 2008-2024; writes data/backtest.csv
python backtest.py candidate    # the same for the candidate; writes data/backtest_candidate.csv
python checks.py                # ratings test, every setting changed in turn, calibration (a few minutes)
python research.py              # polling error by distance from the election, for the Research tab
python state_model_check.py     # the state models' share of a state's starting point
python state_geography_check.py # the state models: their national level and their placing of the states, apart
python timeline.py              # what the polls have been worth at each distance, and the curves that follow
python validate_phase_in.py     # the phase-in of polls tested near the election, far from it, and under a flood
python review.py                # REVIEW.md, from the files the scripts above wrote
python status.py                # STATUS.md: where things stand, the hybrid's evidence, the ranges, the open decisions
python polls.py                 # the state polls; writes data/state_polls.json (--offline to rebuild from the saved feed)
python run_2028.py              # the forecast for the date in data/inputs.json; writes data/forecast_2028.json, data/history.csv
python update.py                # the update: read, compare, and if anything is new run_2028, archive, make_page
python make_page.py             # docs/index.html
python tests/test_model.py; python tests/test_polls.py; python tests/test_update.py
```

The tests run before every update. `tests/test_model.py` reruns the last-day forecasts of 2008 to 2024 and fails if any
differs from `data/backtest.csv`, so a change to the code cannot move the published forecast unnoticed. It also checks
the candidate's rules: polls counted once, the long-range model before and after its polls exist, and early state
polls held under their ceiling.

Needs numpy and pandas. `prep.py` expects the source files listed below in `raw/`; the cleaned copies it writes to
`data/` are included, so everything after `prep.py` runs as is. (`prep.py` also reads the Fifty-Two Keys and Tipping Point folders for results.)

## The model

Every number is the Democratic share of the two-party vote. All settings are at the top of `model.py` (`SET`). None is
fitted to the five elections the method is tested on.

1. **National polling average.** A poll's weight halves every (days to the election / 5) days, held between 7 and 30;
   grows with the square root of its sample; is halved for each newer poll from the same pollster; and is 1.0, 0.9 or 0.7
   for likely voters, registered voters or adults.
2. **A national starting point before polls** (`fundamentals.py`, `run_2028.official`). The plain average of the approval
   equation (the president's June net approval with a first-term term, after Abramowitz, fitted only on earlier
   elections) and Tipping Point's approval-and-economy model. Tipping Point's long-range model joins as a third equal
   part once the polls it is built on exist (November 7, 2027), phased in so that its polls are not counted twice.
   Fifty-Two Keys is not a part.
3. **National number.** Polls and the starting point are mixed by the calendar: polls count for what the polling average
   has been worth at each distance from an election (`timeline.py`: about 3% two years out, 11% at 250 days, 24% at 120,
   61% on the last day), and less again while the nominees are not known.
4. **States.** A state starts at the national number plus where it sits against the nation: half its lean (three quarters
   of how it voted against the nation last time, one quarter the time before), half where Tipping Point's two state models
   place it against their own national figure. Its own polls, each moved by the change in the national average since it was
   taken, pull it away from that start, under a ceiling that rises as the election nears (11% of a state two years out,
   43% at 120 days, all of it on the last day).
5. **Uncertainty.** A national error with fat tails, a regional error and a state error. Their sizes come from how far
   FiveThirtyEight's published polling averages of 1972-2016 stood from the result at each distance from the election,
   and from how far states have landed from their leans, using only elections before the one being forecast. A state's
   own error is sized from its record in the last five elections, pulled toward the common size, so some states' intervals
   are wider than others' (`interval_study.py`). For 2028 the starting point carries an allowance for approval still
   moving: fifteen points of net approval at the midterm, counted by the structural models' share of the national number,
   shrinking with the square root of the time left and closing when the June 2028 reading is in.
6. **Simulation.** 40,000 elections; Maine and Nebraska split by district. The headline is the share each side wins
   outright; a 269-269 tie is counted on its own. Simulated shares past 90 or under 10 are folded smoothly into the last
   ten points (`model.bound`); nothing between 10 and 90 is touched and no share is moved across 50. The 80% prediction interval shown
   for a place is the 10th to the 90th of every hundred simulated results.
7. **One set of simulated elections for everything shown.** The national vote, its range and the chance of winning the
   most votes are counted from each simulated election's own states, added up by the votes each state cast in 2024, so
   they cannot disagree with the states or the electoral count.
8. **Left out, after testing:** Fifty-Two Keys (`keys_study.py`: every measure was best without it), prediction markets
   (`market_study.py`: one election of state markets exists to test on, and on it they did not add), expert ratings
   (`checks.py`), trends in state leans and midterm results (`state_trend_study.py`).

### Prediction markets

`markets.py` finds every open market on 2028 at Polymarket, Kalshi and Manifold by searching and by the pattern of their
names, reads a Democratic and a Republican price for each, scores each market on how much is staked, how recently it traded
and how tight its prices are (play money counts for half), and averages each provider's best market for each place. Prices
are kept in `docs/markets/` whenever they move. None of this enters the forecast. An experimental run
(`markets.informed`) weights the official simulated elections toward the markets and is shown beside the forecast; it never
moves a headline on its own, and its figures stay consistent with one another because whole elections are weighted. A move
in the markets alone refreshes the comparison without making a new official forecast.

### The other versions

`model.PREVIOUS` is the method published until November 25, 2026. `CANDIDATE`, `HYBRID` and `STRUCTURAL` are versions that
were tested against it. All are run beside the official forecast every time and written to `data/forecast_2028.json`
(`candidate`) and `data/history.csv`, never to the page, so that they can be scored against the result in 2028.

`STATUS.md` (written by `status.py`) is the standing report: the method, the evidence, the state-level and approval
studies, what runs by itself and what is still done by hand. `RUNBOOK.md` says how the three sites are kept running.

## Changes of method

Forecasts kept before a change stay in `docs/archive/` exactly as they were made. `data/methods.json` holds the same list
for the page, which marks each change on the history chart.

- **November 25, 2026.** The headline is the share of simulated elections each side wins outright. Before, it was moved a
  quarter of the way toward betting markets (62% for the Democrats against the simulations' 60%) and a 269 to 269
  split counted as half a win for each side. Markets are now shown for comparison only; they are in no back-test. A tie is
  counted on its own.
- **November 25, 2026.** What approval may still move by before June 2028 now shrinks with the square root of the time
  left, and closes only when the June 2028 polls are in.
- **November 25, 2026.** The national number no longer uses Fifty-Two Keys. It starts from the approval equation and
  Tipping Point's approval-and-economy model (and its long-range model from November 2027), early polls count for what the
  record says they are worth, and Tipping Point's state models are used only for where they place each state. Democrats
  moved from 61% to 70% on the day: a change of method, not of the race. Tested in `keys_study.py` and `backtest.py`; the evidence is in `STATUS.md`.
- **November 25, 2026.** The approval allowance is 15 points, up from 10, and counts by the structural models' share of the
  national number. Each state's error is sized from its own record in the last five elections. `method_change.py` splits
  the day's changes into their parts; `STATUS.md` has the table.
- **November 25, 2026.** The chance of winning the most votes, and of the vote and the Electoral College disagreeing, are
  counted from each simulated election's own states, added up by the votes each state cast in 2024.
- **November 26, 2026.** Presentation only. The headline's two chances are each party's outright wins out of the simulated
  elections that do not end 269 to 269, rounded so that they add to 100, with the note "Winning probabilities exclude
  Electoral College ties." The forecast file, the API, the archive, the back-tests and every other figure keep the raw shares
  and the tie. The Model tab now explains the calculation step by step from the run's own figures; the prediction-market
  study moved to the Research tab. Polls, approval and nominees are read from Tipping Point's live feed (`live.js`), which is
  still written after its academic forecast is fixed on August 6, 2028.
- **November 26, 2026.** Presentation only. The Forecast tab's opening paragraph is written from the day's inputs; the
  forecast-updates box and the prediction-market comparison left the Forecast tab (the change attribution, the archive and
  the market record are all still made and kept; the comparison is now in the Research tab's markets study). The history
  chart was redrawn. The Model tab's projection of the national interval now uses the 80% multiplier of the t distribution
  the simulation draws from (1.143 standard deviations, not the normal 1.282), so its first point matches the simulation's
  own interval; the projected Election Day width is about ±3.6 points of margin, not the ±4.1 shown before. The simulation
  itself is unchanged.

## Back-test, 2008-2024

Run as of 120, 90, 60, 30, 14, 7 and 1 days before each election, with only the polls that had finished, through the
same code as the live forecast and with every part the live forecast has: the polls, the fundamentals prior, the
state-level models and the error sizes, each from before the day.

| Election | Favored on the last day | Won | National margin: forecast, result, off by | Democratic electoral votes: forecast, range, result |
|---|---|---|---|---|
| 2008 | Democrats, 96% | Democrats | D+8.2, D+7.5, 0.7 | 352, 293 to 404, 365 |
| 2012 | Democrats, 76% | Democrats | D+2.6, D+3.8, 1.3 | 299, 245 to 348, 332 |
| 2016 | Democrats, 75% | Republicans (missed) | D+3.6, D+2.3, 1.3 | 302, 242 to 357, 232 (outside) |
| 2020 | Democrats, 92% | Democrats | D+7.8, D+4.5, 3.2 | 336, 273 to 395, 306 |
| 2024 | Republicans, 52% | Republicans | D+0.7, R+1.5, 2.2 | 268, 225 to 322, 226 |

- Last day: favored the winner in 4 of 5; typical state miss 1.8 points of share (3.7 of margin); 264 of 280 states and
  districts called; 90% of state results inside 80% prediction intervals, so the intervals are a little wide
  (`STATUS.md`, section 4, says why they are left so).
- The national margin was off by 1.7 points on average, most times in the Democrats' favor, as the polls were.
- The electoral-vote forecast is the middle simulation with its 80% prediction interval. The result was inside the interval
  in 4 of the 5 years.
- This table is the official method. `python backtest.py previous` runs the method published until November 25, 2026 the same
  way (`data/backtest_previous.csv`); `STATUS.md` sets the two side by side at every distance.

### Checks on the choices (`checks.py`)

- **Expert ratings.** Cook Political Report's final ratings (2008-2020) and Sabato's Crystal Ball (2008-2024) were added to
  the last-day forecasts, each rating pointing to a share three points a step from a toss-up. At 15% the model called 263
  of 280 states and districts against 264 without them; the typical miss in close states went from 1.36 to 1.43 points.
  Heavier weights were worse (at 100%: 263 called, 2.26). In the closest states the raters mostly say toss-up. So ratings
  are not used for the presidency. The date of the Sabato ratings is not given in the file they come from.
- **Every other setting, changed one at a time** (the weight of a state's starting point, the half-life, the cut for repeat
  polls, the lean, the regional share, the tails): the typical state miss on the last day stayed between 1.81 and 1.89
  points and the count of calls between 264 and 267 of 280. Nothing here was tuned.
- **Are the chances honest?** Last-day state forecasts grouped by the chance given to the favorite: said 55%, won 40% (15
  forecasts); said 67%, won 86% (21); said 83%, won 89% (35); said 96%, won 100% (62); said 99.8%, won 100% (147). The
  model is a little less sure than it needs to be, except in the closest group, which is small.

- **The state-level models' share of a state's starting point** (`state_model_check.py`). For 2028 half of each
  state's starting point is the Tipping Point Nowcast's forecast of that state, which averages two state-level models
  (state approval and economy, after Enns and colleagues; long-range polls, after DeSart). Tipping Point's record of
  those models for 2008 to 2024 is in `data/state_models.csv`: the forecasts the authors published for 2020 and 2024,
  and for 2008 to 2016 each model refitted on the elections before. With every state poll taken away, the starting
  point missed the final margin by 4.67 points with no state model, 4.00 at half, 3.98 at 60%, 4.00 at 80% and 4.12
  with the state models alone (close states: 3.90, 3.32, 3.33, 3.40, 3.56). Half to four fifths is flat, so half stays.
  The approval model alone was best near 40% (4.20) and worse past half (5.18 alone; its 2020 forecast was too
  Democratic), so the average of the two is used. Using only where the models place a state against the nation, not
  their national level, was worse (4.41 at best). With polls in, the gain shrinks (last day: 3.75 to 3.66), because
  polls make up 55% of a close state's projection at 120 days and 80% on the last day. At 60% today's 2028 chance
  would be 62.1% and not 62.3%. `state_geography_check.py` takes this further and separates the models' national level
  from their placing of the states; `REVIEW.md` has the tables. In short: the approval model's placing is no better
  than the lean's, the combined model's is about equal, and most of the combined model's lead far from the election is
  its national level.
- **A primary equation.** Helmut Norpoth's Primary Model reads November from the early primaries. A third fundamentals
  equation was tried in that spirit: the party in office's candidate's share in New Hampshire less the challenger's, with
  first term, fitted on earlier elections and averaged with the other two (`fundamentals.PRIMARY`). In the back-test the
  national miss fell at every distance (last day: 1.72 to 1.47 points of margin; 120 days: 2.04 to 1.68), with no change
  in state calls or in the calibration score. But that rests on five elections, was better in three of them and worse in
  two (2012, 2024), and the gain is mostly 2008. Over the 13 elections since 1976 the fundamentals alone were worse with
  the primary equation than without it (a typical miss of 2.7 points of share against 2.0, better in 3 of 13; in 2020 it
  put Trump four points too high). So it is not used. The Research tab has the study.

### What the back-test cannot show

These are limits of the validation. Where something could not be rebuilt as it stood on the day, it is either used as
it finally stood or left out, and the results above should be read with that in mind.

- **The state-level models have one forecast a year on record, not one a day.** The approval model's forecast is made
  about 100 days out, so the test at 120 days sees it three weeks early. For 2008, 2012 and 2016 the models are refits on
  the elections before, with that year's final inputs; for 2020 and 2024 they are the forecasts the authors published.
  The approval model's 2020 entry was made with an earlier version of the model and read from a chart in the article.
- **Final figures, not first releases.** The approval equation's growth figure and the state models' inputs are as
  finally revised, not as first published. Old vintages of every series, and poll lists as they stood on each day, are not
  available free in one place, so the back-test is not a real-time one.
- **Betting odds and Fifty-Two Keys** are in no back-test of the official method and in no part of the forecast.
- **Two years out.** The back-test starts 120 days before each election (250 in `validate_phase_in.py`). Beyond that
  there are early polls for three elections only, of pairings picked in hindsight. Neither forecast's range at this
  distance is validated: the allowance for drift is a stated size, not a measured one.
- **Pollster quality and house effects** are not modelled. Every pollster counts the same apart from sample and recency.

## Sources

| Input | Source |
|---|---|
| Polls, 2008, 2012, 2016 | The Economist, `us-potus-model` (`data/all_polls_2008.csv`, `all_polls_2012.csv`, `all_polls.csv`) |
| Polls, 2020, 2024 | FiveThirtyEight `president_polls_historical.csv`, from the archive copy in `jcervas/Data` |
| Polling averages, 1972-2016 | FiveThirtyEight `data/polls/pres_pollaverages_1968-2016.csv` |
| Results and electoral votes | The Fifty-Two Keys data (state results 1952-2020) and official 2024 counts |
| June approval, 1948-2016 | The Economist, `abramowitz_data.csv`; 2020 and 2024 from Gallup |
| Regions | The Economist, `state_region_crosswalk.csv` |
| Expert ratings | Cook Political Report ratings 1988-2020 and Sabato's Crystal Ball ratings 2004-2024, from public course data (`cpr_ratings.csv`, `sabato_crystal_ball_ratings.csv`) |
| 2028 national head-to-head polls, state forecasts and approval | Tipping Point Nowcast, read every hour (approval is its pooled average among adults over the last 30 days). It reads its polls from VoteHub and PollResults.org, both CC BY 4.0 |
| 2028 state polls | PollResults.org (The New York Times's poll data, CC BY 4.0), read every hour; VoteHub's list of poll types is watched (`polls.py`) |
| Fifty-Two Keys count (shown, not used) | That site's feed, `keys.json`, read every hour |
| Polling averages for the timeline, 1972-2016 | FiveThirtyEight `data/polls/pres_pollaverages_1968-2016.csv` (`data/timeline.csv`) |
| State-level models, 2008-2024 | Tipping Point's record of the two models (`data/state_models.csv`) |
| Prediction markets (shown, not used) | Polymarket, Kalshi and Manifold, through their public services, and electionbettingodds.com; read every hour, kept in `docs/markets/` |
| What markets said of each state in 2024 (the market study only) | Polymarket's and Manifold's public price histories (`data/market_history_2024.csv`, read by `tools/market_history.py`) |
| House vote by state, 1998-2024 (the trend study only) | FiveThirtyEight `election_results_house.csv` (`data/house_by_state.csv`: districts both parties contested) |
| Map | us-atlas 3.0.1 (ISC), Census cartographic boundaries |

The Margin is not affiliated with or endorsed by VoteHub, PollResults.org or The New York Times.

Polls sponsored by a party are left out of 2020 and 2024. For 2024, Biden-Trump polls are used until July 20 and
Harris-Trump polls from July 21. The source's 2020 figure for Maine's 2nd district is on the wrong side and is corrected.
