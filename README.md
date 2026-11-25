# The Margin

A forecast of the 2028 presidential election built the traditional way: polling averages, a fundamentals prior, state
leans and betting markets, run through a simulation of the Electoral College. It is
back-tested on 2008 to 2024. The logo is a plus-or-minus sign: `docs/logo.svg`.

The Senate and the House are planned next, on the same design.

## Where it stands (November 23, 2026)

| | |
|---|---|
| Democrats win the Electoral College | 60% (model alone 58%; betting markets 67%) |
| Electoral votes, average | 283 to 255; four runs in five give Democrats 211 to 360 |
| National vote | Democrats 51.4% of the two-party vote, give or take 2.9 |
| Democrats win the most votes | 71% |
| Tipping-point state | Pennsylvania |

The election is 715 days away and neither party has a nominee. Read it as a lean. The page carries the current
numbers; this table is the first day's.

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

1. reads the Tipping Point Nowcast's file (national head-to-head polls, state forecasts, presidential approval among
   adults), the Fifty-Two Keys feed, the party odds from electionbettingodds.com and the state polls (below);
2. compares what it read with what the last forecast was made from (`data/fingerprint.json`: one short hash for the
   national polls, the Nowcast's forecasts, approval, the keys, the odds, the state polls and the day). The time a
   source was read, and the time another site made its file, are not in the fingerprint;
3. stops if nothing differs. Nothing is recalculated and nothing is saved;
4. otherwise reruns the forecast, keeps it in the archive if it differs from the last one kept, replaces the day's row in
   `data/history.csv`, rebuilds the page and commits, which republishes the site.

What counts as new: a poll added, changed or dropped; a move in the Nowcast's forecasts or its approval average; a move
in the Fifty-Two Keys count or its spread; betting odds a point or more away from the price in use (smaller hourly
wobbles are not news); and the day itself. The first run of every day always goes through, so the day-by-day record
has every day and the poll weights, which depend on the date, keep up.

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
a run started by hand, end as failed if an input has gone stale: the Nowcast not read since the day before, the keys,
the odds or the state polls not read for two days. So a source that is down for an hour sends nothing, and one that
stays down is reported once a day. A run that fails for any other reason is tried again the next hour and marked as
failed at 7 a.m., 1 p.m. and 7 p.m. Eastern only.

**"Every hour" is what is asked of GitHub, not what GitHub promises.** GitHub starts scheduled runs when it has room.
In November 2026 it was starting this account's scheduled runs hours late (the Tipping Point runs asked for at 6:17 and
11:17 UTC began 6 to 12 hours later). A late run loses nothing but time, since every run is complete in itself, but how
often the checks really happen is GitHub's doing. A run started from outside (the "Run workflow" button, the event the
other two sites can send, or a call to GitHub's API by a clock somewhere else) starts at once. "Run workflow" has a box
to make the run as the hourly check does.

On a new day the previous day's inputs are kept as `data/prev_inputs.json` and `data/prev_nowcast.js`. The page's "What
moved since yesterday" box comes from them: yesterday's inputs are swapped for today's one at a time (polls, approval,
markets, the keys, then the state models and the date) and the chance is recomputed at each step.

Units: the scripts work in points of the two-party vote share. The page shows every miss in points of margin, which is
twice that (a typical state miss of 1.8 points of share is 3.7 points of margin).

The Fifty-Two Keys count (`keys`, `keys_mean`, `keys_sd` in `data/inputs.json`) is read from that site's own feed,
`https://ka82205.github.io/fifty-two-keys/keys.json`: the share of keys in the Republicans' favor if every open key
lands the way it leans, the middle of its run ahead, and the spread of that run.

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

Every number is the Democratic share of the two-party vote. All settings are at the top of `model.py`. They were written
down before the back-test was scored and none is fitted to the five elections it is tested on.

1. **National polling average.** A poll's weight halves every (days to the election / 5) days, held between 7 and 30;
   grows with the square root of its sample; is halved for each newer poll from the same pollster; and is 1.0, 0.9 or 0.7
   for likely voters, registered voters or adults.
2. **Fundamentals** (`fundamentals.py`). The average of two equations, each fitted only on earlier elections: the
   president's June net approval with a first-term term (after Abramowitz; second-quarter growth is left out because of
   2020), and the Fifty-Two Keys count turned into a vote share.
3. **National number.** Polls and fundamentals are averaged by how reliable each has been: the polling average's error at
   that many days out against the fundamentals' error. On the last day polls carry about 70%.
4. **States.** A state starts at the national number plus its lean (three quarters of how it voted relative to the nation
   last time, one quarter the time before). Its own polls, each moved by the change in the national average since it was
   taken, pull it away from that start as if the start were 1.5 fresh polls.
5. **Uncertainty.** A national error with fat tails, a regional error and a state error. Their sizes come from how far
   FiveThirtyEight's published polling averages of 1972-2016 stood from the result at each distance from the election,
   and from how far states have landed from their leans, using only elections before the one being forecast.
6. **Simulation.** 40,000 elections; Maine and Nebraska split by district; a 269-269 tie counts as half a win. The
   errors are drawn on an open scale, so a simulated share past 90 (or under 10) is folded smoothly into the last ten
   points and none passes 100 or 0 (`model.bound`). Nothing between 10 and 90 is touched and no share is moved across
   50, so no chance or electoral count changes; in practice only the District of Columbia is affected. The range shown
   for a place is the 10th to the 90th of every hundred simulated results, not a normal curve drawn around its middle.
7. **Betting markets.** The market's chance is pooled with the model's at 25%, on the log-odds scale. The markets are one
   of four sources (polls, fundamentals, state models, markets), so they get one share in four; not more, because prices
   already lean on the same polls, the 2028 markets are thinly traded, and this weight is not back-tested yet. At 0% the
   Democrats are at 55%, at 70% they are at 64%.
8. **Expert ratings are left out.** They were tested (see below) and did not help.

Half of each state's starting point is the Tipping Point Nowcast's forecast for that state (two published state-level
models), in the 2028 forecast and in the back-test. For 2028 the fundamentals also carry extra error for two years of
drift: ten points of net approval and the spread of the Fifty-Two Keys run ahead. That allowance does not shrink as
the election nears; only the chart of the narrowing range assumes it does. State polls are collected and listed but not
counted (see "State polls").

### The candidate

A second forecast is run beside the published one every time it runs. It is the design under review, described and
tested in `REVIEW.md`. It is not on the page; it is in `data/forecast_2028.json` under `candidate` and in two columns of
`data/history.csv`. Every setting that differs is in `model.CANDIDATE`:

- **National prior:** the Tipping Point Nowcast's two national models and the Fifty-Two Keys line, a third each, with
  the Keys read at the middle of that site's run ahead. The approval equation is left out. The Nowcast's long-range
  model is built on national polls taken in October 2027; until those exist it is left out, and the prior is the other
  two (`model.long_range_weight`).
- **National polls** are weighed by what the polling average has been worth at each distance from the election
  (`timeline.py`: about 3% two years out, 11% at 250 days, 24% at 120, 61% on the last day), less whatever the prior
  already carries of the same polls, and less again while the nominees are not known.
- **State polls** count as in the published rule, under a ceiling that falls with distance (11% of a state two years
  out, 43% at 120 days, all of it on the last day).
- **State models** give only where they place a state against their own national figure, since their national level
  is already in the national number.

### The hybrid

A third forecast is run the same way: `model.HYBRID`, in `data/forecast_2028.json` under `candidate.hybrid` and in two more
columns of `data/history.csv`. It is the candidate with the approval equation kept, as the published forecast keeps it. Its
national prior is the Nowcast's approval-and-economy model, the Fifty-Two Keys line and the approval equation, a third
each; the long-range model joins as a fourth equal part once the polls it is built on exist. Nothing else differs from the
candidate, and no weight in it was fitted. `STATUS.md` sets it against the published forecast at ten distances from the
election and gives a recommendation. Neither it nor the candidate is the published forecast.

`STATUS.md` (written by `status.py`) is the standing report: what is official and what is under review, the evidence, how
the ranges have held up, and the decisions that are open. `RUNBOOK.md` says how the three sites are kept running: what
starts each run, the two secrets, what a failed run means, and what is still done by hand.

## Back-test, 2008-2024

Run as of 120, 90, 60, 30, 14, 7 and 1 days before each election, with only the polls that had finished, through the
same code as the live forecast and with every part the live forecast has: the polls, the fundamentals prior, the
state-level models and the error sizes, each from before the day.

| Election | Favored on the last day | Won | National margin: forecast, result, off by | Democratic electoral votes: forecast, range, result |
|---|---|---|---|---|
| 2008 | Democrats, 97 in 100 | Democrats | D+9.1, D+7.5, 1.6 | 354, 298 to 405, 365 |
| 2012 | Democrats, 79 in 100 | Democrats | D+3.9, D+3.8, 0.0 | 302, 250 to 354, 332 |
| 2016 | Democrats, 75 in 100 | Republicans (missed) | D+4.4, D+2.3, 2.1 | 300, 243 to 356, 232 (outside) |
| 2020 | Democrats, 93 in 100 | Democrats | D+6.8, D+4.5, 2.2 | 336, 275 to 394, 306 |
| 2024 | Republicans, 52 in 100 | Republicans | D+1.2, R+1.5, 2.7 | 267, 225 to 322, 226 |

- Last day: favored the winner in 4 of 5; typical state miss 1.8 points of share (3.7 of margin); 264 of 280 states and
  districts called; 91% of state results inside ranges meant to hold 80%, so the ranges are a little wide.
- The national margin was off by 1.7 points on average, every time in the Democrats' favor, as the polls were.
- The electoral-vote forecast is the middle simulation and the range holds four in five. The result was inside the range
  in every year but 2016.
- 2024 was a coin flip: the middle simulation had the Democrats on 267, three short, so the Republicans won 52 in 100.
  The close states fell together and the Democrats finished on 226, at the bottom of the range.
- Until November 25, 2026 the back-test ran without the state-level models (last-day state miss 3.75 points of margin;
  now 3.66; the same 264 calls). `python backtest.py candidate` runs the candidate the same way.

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
- **The Fifty-Two Keys count** for a past year uses that year's final figures and today's revised economic data. Most
  of it is known by late summer, so the early snapshots see slightly more than they could have.
- **Betting odds.** They are in the 2028 forecast and not in the back-test. Election-eve odds for 2008-2024 still have
  to be collected from sources that can be checked, so the 25% given to markets is not validated.
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
| Fifty-Two Keys count | That site's feed, `keys.json`, read every hour |
| Polling averages for the timeline, 1972-2016 | FiveThirtyEight `data/polls/pres_pollaverages_1968-2016.csv` (`data/timeline.csv`) |
| State-level models, 2008-2024 | Tipping Point's record of the two models (`data/state_models.csv`) |
| Betting odds | electionbettingodds.com, party to win the presidency, read every hour; a move of under a point is not taken |
| Map | us-atlas 3.0.1 (ISC), Census cartographic boundaries |

The Margin is not affiliated with or endorsed by VoteHub, PollResults.org or The New York Times.

Polls sponsored by a party are left out of 2020 and 2024. For 2024, Biden-Trump polls are used until July 20 and
Harris-Trump polls from July 21. The source's 2020 figure for Maine's 2nd district is on the wrong side and is corrected.
