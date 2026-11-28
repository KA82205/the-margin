# Keeping the three sites running

This covers The Margin, Fifty-Two Keys and Tipping Point. Nothing here needs a computer of yours to be on, and nothing in
the normal course needs anyone to run a script. One thing is done by hand, every few weeks, in a browser: saving a page
from Civiqs and uploading it (see "What is done by hand").

## What runs, and what starts it

| Site | Workflow | What it reads | What starts it |
|---|---|---|---|
| Tipping Point | `Update data and deploy site` | approval polls, national polls, the economy (FRED), state approval | the outside clock (minute 12 of each hour), GitHub's schedule (minute 17, often late), a `heartbeat`, a push (which is how a Civiqs page uploaded by hand is taken in), a run started by hand |
| Fifty-Two Keys | `Update` | approval polls and polls naming a third candidate on every run; the economy (FRED), the forecasters' survey and, in the January after an election, the list of members of Congress, when a release could be out and on the day's first run | the outside clock (minute 22), GitHub's schedule (minute 7, often late), a `heartbeat`, a run started by hand |
| The Margin | `Forecast` | the Tipping Point Nowcast (its models, national polls, approval) and state polls. Prediction markets and the Fifty-Two Keys count are read for comparison only | a notification from either of the other two, the outside clock (minute 42), GitHub's schedule (minute 37, often late), a `heartbeat`, a run started by hand |

Each run reads its sources, compares them with what the last result was made from, and stops there if nothing differs. Only
a run that found something new recalculates, saves, archives and deploys. The first run of each day always goes through.
For The Margin, "new" means something its forecast reads: a new Fifty-Two Keys count does not start one; a move in prediction
markets refreshes the comparison and the price record without a new official forecast; and if either cannot be read the
run does not fail.

The order is one-way: Tipping Point and Fifty-Two Keys never read The Margin, and The Margin never notifies anyone. Two kinds
of message go to The Margin: `upstream-updated`, when one of the other two has published something new, and `heartbeat`,
which only means "check now". Every run of the other two sends The Margin a heartbeat if it has not started a run for 50
minutes. A message that arrives when nothing has changed ends as a run with nothing new.

[ops.html](https://ka82205.github.io/the-margin/ops.html) reads GitHub's record live. For each site: the last good check, the last saved update, the last run
GitHub's own schedule started, the last run an outside clock or a heartbeat started, failures in the last day, whether a
check is overdue (none for three hours), and the last twelve runs with what started each. For The Margin it also shows what
was last read from each source and when.

**GitHub decides when a scheduled run starts.** A schedule is a request, not a promise. Before November 25, 2026 Tipping
Point asked for runs at 06:17 and 11:17 UTC and GitHub started them seven to ten hours late, every day. After the hourly
schedules went in on November 25, 2026, the first scheduled run started eight hours later. That is why the hourly check
does not rest on GitHub's schedule: an outside clock asks for it.

### The outside clock

Set up on November 25, 2026 at [cron-job.org](https://cron-job.org) (free). Three jobs, one a site, each asking GitHub once
an hour for that site's ordinary check: read the sources, stop if nothing is new. It cannot force a forecast.

| | Tipping Point | Fifty-Two Keys | The Margin |
|---|---|---|---|
| Every hour, at minute | 12 | 22 | 42 |
| URL | `https://api.github.com/repos/KA82205/tipping-point/actions/workflows/update.yml/dispatches` | `https://api.github.com/repos/KA82205/fifty-two-keys/actions/workflows/update.yml/dispatches` | `https://api.github.com/repos/KA82205/the-margin/actions/workflows/update.yml/dispatches` |

The same for all three:

- Request method: `POST`
- Request body: `{"ref":"main","inputs":{"check":"true","source":"clock"}}`
- Headers:
  - `Authorization` : `Bearer ` followed by the clock's token (the word Bearer, a space, the token)
  - `Accept` : `application/vnd.github+json`
  - `Content-Type` : `application/json`
  - `X-GitHub-Api-Version` : `2026-03-10`

A good answer is `200`. (Under the older API version the same request answered `204`.)

**What the record shows.** From the first hour after it was set up, November 26, 2026, the record was read twelve hours on: 12 runs of 12 at each site (04:12 to 15:12 UTC at Tipping Point, 04:22 to 15:22 at Fifty-Two Keys, 04:42 to 15:42 at The Margin), every one started four seconds after its minute and every one ended well. In the same twelve hours GitHub's own schedule, which asks for a run every hour, started one run at each site.
A run the clock starts is listed as "Check: outside clock", and [ops.html](https://ka82205.github.io/the-margin/ops.html)
shows the last one for each site. An accepted request is not an update: ops.html reads runs, saved updates and deployments
each on its own.

**The order of the minutes matters a little.** Tipping Point (12) and Fifty-Two Keys (22) check before The Margin (42), so
whatever they publish in an hour is there for The Margin to read in the same hour. They also tell The Margin directly when
they publish, so nothing waits for minute 42.

**GitHub's API version.** GitHub's REST API is versioned by date. The version these sites first used, `2022-11-28`, is
supported "for at least 24 months" after its successor `2026-03-10` came out in March 2026, so it can be withdrawn from
about March 2028, in the middle of the primaries. The three jobs name `2026-03-10`, and so do the messages Tipping Point
and Fifty-Two Keys send The Margin (`.github/workflows/update.yml` in each). When GitHub announces a version after
`2026-03-10`, the same two-year clock starts for it: change the header in the three jobs and in those two files.
ops.html reads GitHub without naming a version, which GitHub answers with its oldest supported one; it uses only fields
that have not changed.

**The token.** The clock has a token of its own, `forecast clock`, that can do one thing: start and stop workflow runs in
these three repositories (fine-grained, Actions: Read and write, nothing else). It cannot read or change a file, a setting
or a secret. It lives only in the three jobs. `DISPATCH_TOKEN`, the secret the sites use to tell The Margin, is a different
token and was not touched. Never paste either into a chat, an e-mail, a file or a commit.

**If a job starts failing.** cron-job.org e-mails when a job fails and switches a job off after 25 failures in a row.
`401`: the token has lapsed or was mistyped. `403` or `404`: the token does not cover that repository or lacks Actions:
Read and write. `422`: the body is not exactly as above. `400` mentioning the API version: GitHub has withdrawn the
version named in the header. While the clock is down nothing is lost: GitHub's own schedules still fire, late, and the
other two sites still wake The Margin whenever they run.

**To replace the token** (it lapses if it was given an expiry; GitHub e-mails a week before): GitHub, your picture at the
top right, Settings, Developer settings, Personal access tokens, Fine-grained tokens, Generate new token. Name
`forecast clock`; Repository access: Only select repositories, the three sites; Repository permissions: **Actions**, Read
and write, everything else "No access". Copy the token from GitHub's page straight into the `Authorization` header of each
job, after the word `Bearer` and a space. Use each job's test run: the answer should be `200`.

**To stop it:** delete the three jobs, then delete the token on GitHub.

## The Senate jobs (The Margin)

| Job | Workflow | What it does | What starts it |
|---|---|---|---|
| The Senate forecast | `Senate forecast` (`senate.yml`) | reads Wikipedia and reruns the Senate forecast (`senate/live.py`) | the end of each run of `Forecast` (so every hour, through the outside clock), GitHub's schedule (minute 55), a run started by hand |
| Money raised | `Senate money` (`senate-money.yml`) | the FEC totals shown on the Senate tab, not used in the forecast (`senate/fec_live.py`, with the `FEC_API_KEY` secret) | the Senate forecast job, once its last run is a day old; GitHub's schedule (10:23 UTC); by hand |
| After each election | `Senate after the election` (`senate-after.yml`) | adds the election's races to the training data and refits the model (`senate/after_election.py`); does nothing between elections | the Senate forecast job, once its last run is a week old; GitHub's schedule (Mondays, 15:47 UTC); by hand |

The Senate forecast hangs on the presidential run, not on GitHub's schedule: on November 27, 2026, its first day, GitHub's
schedule did not start it once in four hours, and started one presidential run in fifteen.

**Each job's health** is a small file on the site that anyone, or any program, can read without signing in:
[senate-forecast.json](https://ka82205.github.io/the-margin/api/health/senate-forecast.json),
[senate-money.json](https://ka82205.github.io/the-margin/api/health/senate-money.json),
[senate-after.json](https://ka82205.github.io/the-margin/api/health/senate-after.json) (`senate/health.py`). Each gives
`ok`, `last_run`, `last_success`, `overdue_after`, `failing_since` and `error`. Something needs a look when `ok` is false,
or when today is later than `overdue_after` (the job has stopped running). A failed Senate run is listed on GitHub with a
green check and a warning, not as failed, so the health file is the place to look. The site keeps the last good figures
meanwhile.

| `error` says | What it means | What to do |
|---|---|---|
| What was read does not look right | A Wikipedia page the forecast reads changed shape or was vandalized, and the run's checks stopped it | Usually passes when the page is put right. If it lasts, the reader in `senate/` needs to learn the new layout |
| Wikipedia could not be read; a page could not be read | Wikipedia did not answer, or a page moved | Nothing if it passes. If it lasts, check that the page named still exists |
| The FEC could not be reached; stopped answering; failed N of M calls | The FEC's API was down, or refused the key | Nothing if it passes. If it lasts, check the key at api.data.gov and save a new one as `FEC_API_KEY` |
| FEC_API_KEY is not set | The secret is missing | Save it under Settings, Secrets and variables, Actions |
| not added yet | Seven weeks after an election some of its results could not be read | The message says what is missing; each week's run tries again |
| The run was stopped before it finished | It ran past its time limit | If it lasts, the run's log on GitHub says where it stopped |

## The House jobs (The Margin)

| Job | Workflow | What it does | What starts it |
|---|---|---|---|
| The House forecast | `House forecast` (`house.yml`) | reads Wikipedia's overview of the election, takes the national mood from the Senate forecast and reruns the House forecast (`house/live.py`) | the end of each run of `Senate forecast` (so every hour, after the presidential and Senate runs), GitHub's schedule (minute 25), a run started by hand |
| After each election | `House after the election` (`house-after.yml`) | once an election's results have settled (seven weeks) and Wikipedia has every district's result, adds its districts to the training data, refits the model and remakes the back-tests (`house/after_election.py`, `house/fit.py`); does nothing between elections | the House forecast job, once its last run is a week old; GitHub's schedule (Mondays, 16:17 UTC); by hand |

**Each job's health**, read as the Senate's:
[house-forecast.json](https://ka82205.github.io/the-margin/api/health/house-forecast.json),
[house-after.json](https://ka82205.github.io/the-margin/api/health/house-after.json).

| `error` says | What it means | What to do |
|---|---|---|
| What was read does not look right | The overview page changed shape, lost districts or was vandalized, and the run's checks stopped it | Usually passes when the page is put right. If it lasts, the reader in `house/wiki_house.py` needs to learn the new layout |
| The Senate forecast's national mood is from ... days old | The Senate forecast has not worked for more than three days | Fix the Senate job first (its health file says why); the House recovers with it |
| not added yet | Seven weeks after an election, Wikipedia still lacks some results (shares, a runoff, the final seat count) | The message lists what is missing; each week's run tries again. Wikipedia's overview usually fills in within a few weeks |

2026 is not in the House model's fit yet: on November 28, 2026, Wikipedia's overview had vote shares for 227 of the 417
contested districts. The after-election job adds it once the page is complete (no earlier than December 22). Until then the
Back-tests tab shows 2026 forecast from 2018-2024 and scored on the winners (`python house/after_election.py --year 2026
--pages FILE --test --save`, with the pages saved by `tools/fetch_house_pages.py` through the samples workflow).

## The governor jobs (The Margin)

| Job | Workflow | What it does | What starts it |
|---|---|---|---|
| The governor forecast | `Governor forecast` (`governor.yml`) | reads Wikipedia's overviews and race pages of every governor race through the next even-year election (the odd-year races before it included), takes the national mood from the Senate forecast and reruns the forecast (`governor/gov_live.py`) | the end of each run of `Senate forecast`, GitHub's schedule (minute 35), a run started by hand |
| After each year's races | `Governors after the election` (`governor-after.yml`) | once a year's results have settled (seven weeks) and Wikipedia has every race's result, adds the races and their polls to the training data, refits the model and remakes the back-tests (`governor/gov_after.py`, `governor/gov_fit.py`) | the governor forecast job, once its last run is a week old; GitHub's schedule (Mondays, 16:37 UTC); by hand |

**Each job's health**, read as the Senate's:
[governor-forecast.json](https://ka82205.github.io/the-margin/api/health/governor-forecast.json),
[governor-after.json](https://ka82205.github.io/the-margin/api/health/governor-after.json). The errors are the House's
(above): a page that changed shape stops the run and keeps the last forecast; a Senate forecast more than three days old
stops it too; "not added yet" lists what Wikipedia still lacks. The checks also need every one of the 50 states accounted
for: those with a race, and those whose last election (read from the overview of the year it was held) chose their
governor.

2026's 36 races pass every check already; the after-election job adds them, with their polls, once seven weeks have
passed (December 22). Until then the Back-tests tab shows 2026 forecast from 2006-2024 (`python governor/gov_after.py
--year 2026 --pages FILE --test --save`).

## Secrets

Four secrets, all optional, set under each repository's Settings, Secrets and variables, Actions. Never put one in a file,
a commit, a message or a chat. The outside clock's token (above) is not a secret of any repository: it lives only in the
scheduling service.

**`FRED_API_KEY`** (Fifty-Two Keys; Tipping Point if it has one). A free key from fred.stlouisfed.org, My Account, API
Keys. Without it FRED's download links do not answer GitHub's servers and the economic figures are not refreshed; the run
says so and ends as failed.

**`DISPATCH_TOKEN`** (Fifty-Two Keys and Tipping Point). Lets a site tell The Margin the moment it has published something
new, and wake it when it has gone quiet. It is saved in both repositories and both have used it: Fifty-Two Keys at 19:01 UTC
and Tipping Point at 21:48 UTC on November 25, 2026. It is a fine-grained token with no expiry, limited to `the-margin`,
Contents: Read and write.

If it is ever revoked the two sites carry on, their logs say "No DISPATCH_TOKEN secret" or warn that The Margin could not be
told, and The Margin finds their changes at its own next run. To replace it: GitHub, Settings, Developer settings,
Fine-grained tokens, Generate new token; Only select repositories, `the-margin`; Repository permissions, Contents: Read and
write; then save it as `DISPATCH_TOKEN` under Settings, Secrets and
variables, Actions in `tipping-point` and in `fifty-two-keys`, and delete the old token.

Without the token nothing breaks. The Margin's own scheduled run is the fallback.

**`FEC_API_KEY`** (The Margin). A free key from api.data.gov, for the money each Senate candidate has raised, shown on
the Senate tab and not used in the forecast. Without it the money job stops, its health file says `FEC_API_KEY is not
set`, and the Senate tab keeps the last totals.

**`BLS_API_KEY`** (Fifty-Two Keys). Not needed. The second-source check asks the Bureau of Labor Statistics without a key,
which allows a few requests a day from each address; GitHub's servers share addresses, so on some days the Bureau may
answer that the allowance is used up. Then a held figure simply stays held until the next run. A free key from
bls.gov/developers, saved under this name, removes that limit.

## When a run ends as failed

A failed run means "somebody should look", not "the site is down". The page always shows the last good figures.

| The log says | What it means | What to do |
|---|---|---|
| A figure was held back | A new figure was outside its believable range or jumped too far, and its own publisher did not confirm it. It was not used | The run has already asked the publisher (the Bureau of Labor Statistics, the Bureau of Economic Analysis, the Census Bureau, the Federal Reserve Board, the University of Michigan, the Energy Information Administration, the Department of Labor), and the line says what it answered; a real figure passes by itself once the publisher gives it. If the publisher could not be reached and the figure is real, start the workflow by hand with the series name in the `trust` box. If it is wrong, do nothing: the next good figure replaces it |
| Held: a key's evidence is late or in dispute | A key should have been callable by now and its evidence is missing, or an entry and the rule disagree | `KEYS.md` says what each key needs. The key keeps its chance and is never counted as no |
| Not read for N days | A source has not answered | Usually passes. If it lasts, check whether the source moved |
| A newer survey should be out and has not been read | The forecasters' survey was not reached, or its table changed shape | Find the line starting `The outlook:` in the log. If the table changed, `outlook.py` needs to learn the new layout; until then the older outlook is used and labelled with its date |
| Stale input (The Margin) | The Nowcast has not been read for a day, or the state polls for two | Check that Tipping Point's page is up; the last copy is used meanwhile |
| The page left in pipeline/inbox was not used (Tipping Point) | A Civiqs page uploaded by hand failed a check: not the tracker, older than the copy held, or figures too far from it | `pipeline/inbox/LAST.md` in `tipping-point` gives the reason. The copy held is unchanged. Save the page again and upload it again |
| Prediction markets: a provider was not read | One of Polymarket, Kalshi or Manifold did not answer | Nothing: the others are used, the last reading stays, and the forecast does not depend on any of them |
| The repository changed while this run was working | Two runs overlapped. The later one's result was dropped | Nothing: the next run starts from the new state |

To run any site again by hand: its repository, Actions, the workflow, Run workflow. Ticking `check` makes the run behave as
the hourly one does (stop if nothing is new); leaving it unticked runs everything.

## What is done by hand

One thing, every few weeks, and it takes a minute. Nothing else is typed in on any of the three sites.

### Every few weeks: the Civiqs page

Tipping Point takes the gaps in approval between states from Civiqs's tracker. Civiqs's site refuses automatic reads and
offers no data service, and no other free source publishes the same measure for fifty states (Morning Consult's is monthly,
pools three months and keeps its data behind a paid plan; YouGov has no regular state series). So the page is saved by hand:

1. Open <https://civiqs.com/results/approve_president_trump_2025>, press Ctrl+U (Cmd+Option+U on a Mac) to see the
   page's source, and save it (Ctrl+S). The source carries the figures to two decimals; the page saved as shown is read
   too, in whole percentages.
2. Open [pipeline/inbox in tipping-point](https://github.com/KA82205/tipping-point/tree/main/pipeline/inbox), choose
   **Add file**, **Upload files**, drop the saved file in, **Commit changes**.

The commit starts a run. It reads the page, checks it, rewrites the copy and its date, empties the inbox, runs the models
again, publishes Tipping Point and tells The Margin, which makes a new forecast if the Nowcast moved. About three minutes
end to end. `pipeline/inbox/LAST.md` says what happened; a page that fails a check changes nothing and marks the run
failed. Nothing breaks if the copy grows old: the date of the figures is shown on Tipping Point's page and on ops.html,
which marks it once it is more than five weeks old.

### Exceptions, each of which announces itself

| What | How you will know | What to do |
|---|---|---|
| Two sources contradict each other on a nomination key (E04 to E07), or the nominee is replaced after a convention | The Fifty-Two Keys page shows the key as held with the reason; from 2028 the run fails once a day while it lasts | Usually nothing: the next run looks again, and New Hampshire's own count settles a dispute about New Hampshire when its site answers. If it does not clear, put the figure in by hand with its source (`data/outlook.json` for E04, `data/nh_primaries.csv` for New Hampshire); the entry is compared with the sources. A source that has simply not been updated holds nothing |
| A large, real move in an economic series on a day its publisher cannot be reached | The Fifty-Two Keys run fails once a day and names the series | Usually nothing: the next run asks the publisher again. To let it in after a look, start the workflow by hand with the series in the `trust` box |
| The authors of Tipping Point's models publish a 2028 forecast | Tipping Point's run carries a warning naming the article; `docs/watch.json` lists it | `python pipeline/put_in.py`, as Tipping Point's readme says |
| A token lapses, or GitHub withdraws an API version | GitHub e-mails you; the scheduling service e-mails when its jobs fail | See "The outside clock" above |

The "Source samples" workflow in `the-margin` and the "Nomination sources check" workflow in `fifty-two-keys` are started by
hand and change nothing: the first fetches a sample from each outside source onto a side branch, the second prints what the
nomination reader makes of the live pages for 2016, 2020, 2024 and 2028. Use them if a source seems to have changed shape.

## The method is frozen

The published forecast is `model.SET` in `the-margin/model.py` with the approval allowance in `data/inputs.json`
(`approval_drift`, 15): the version approved on November 25 and 26, 2026, with no weight for Fifty-Two Keys or prediction
markets. It is not changed before the election except to fix a fault. `PREVIOUS`, `CANDIDATE`,
`HYBRID` and `STRUCTURAL` beside it are run on every forecast and written to the data file and the archive, never to the
page, so that they can be scored beside the official one afterwards.

If a fault has to be fixed: change the code, add a line to `data/methods.json` saying what changed and why, run
`python backtest.py` (this rewrites `data/backtest.csv`, which `tests/test_model.py` guards), then `python checks.py`,
`python status.py` and `python update.py --force`. The archive keeps every earlier forecast as it was, the page marks the
day on its history chart, and the next check publishes a forecast whose reason reads "the method".

Fifty-Two Keys' rules are locked (`locked_keys.csv`, `tests/test_model.py`). Tipping Point's two models follow their
authors' published methods and are not adjusted.

## Checking that everything still works

    the-margin        python -m pytest tests && node tests/test_page.js && node tests/browser_hover.js && node tests/browser_page.js
                      (the Senate, each on its own: python tests/test_senate_live.py, test_after_election.py,
                      test_fec_live.py, test_senate_health.py; the House: python tests/test_house.py; the governors:
                      python tests/test_governor.py)
                      (the studies: python interval_study.py, market_study.py, method_change.py, keys_study.py, state_trend_study.py)
    fifty-two-keys    python -m pytest tests
    tipping-point     python pipeline/tests/test_runs.py && python pipeline/tests/test_civiqs.py

Each workflow runs its repository's tests before it reads anything, and stops if one fails.

Every forecast The Margin has kept is in `docs/archive/` with the versions of the other two sites it was made from; the
Nowcast file itself is in `docs/archive/upstream/`. Fifty-Two Keys keeps its runs in `archive/` and its calls in
`data/key_calls.csv`; Tipping Point keeps its runs in `docs/record/`. None of these is ever rewritten.
