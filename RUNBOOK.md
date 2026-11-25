# Keeping the three sites running

This covers The Margin, Fifty-Two Keys and Tipping Point. Nothing here needs a computer of yours to be on, and nothing in
the normal course needs anyone to run a script.

## What runs, and what starts it

| Site | Workflow | What it reads | What starts it |
|---|---|---|---|
| Tipping Point | `Update data and deploy site` | approval polls, national polls, the economy (FRED), state approval | the schedule (minute 17 of each hour), a `heartbeat`, a push, a run started by hand |
| Fifty-Two Keys | `Update` | approval polls and polls naming a third candidate on every run; the economy (FRED), the forecasters' survey and, in the January after an election, the list of members of Congress, when a release could be out and on the day's first run | the schedule (minute 7), a `heartbeat`, a run started by hand |
| The Margin | `Forecast` | the Tipping Point Nowcast, the Fifty-Two Keys feed, betting odds (shown, not used), state polls | the schedule (minute 37), a notification from either of the other two, a `heartbeat`, a run started by hand |

Each run reads its sources, compares them with what the last result was made from, and stops there if nothing differs. Only
a run that found something new recalculates, saves, archives and deploys. The first run of each day always goes through.

The order is one-way: Tipping Point and Fifty-Two Keys never read The Margin, and The Margin never notifies anyone. Two kinds
of message go to The Margin: `upstream-updated`, when one of the other two has published something new, and `heartbeat`,
which only means "check now". Every run of the other two sends The Margin a heartbeat if it has not started a run for 50
minutes. A message that arrives when nothing has changed ends as a run with nothing new.

[ops.html](https://ka82205.github.io/the-margin/ops.html) reads GitHub's record live: for each site the last run of any kind, how many runs GitHub started by itself in the
last day and week, and the last twelve runs with who started each.

**GitHub decides when a scheduled run starts.** A schedule is a request, not a promise. Before November 25, 2026 Tipping
Point asked for runs at 06:17 and 11:17 UTC and GitHub started them seven to ten hours late, every day. In the first five
hours after the hourly schedules went in, none of the three repositories had a scheduled run start. Whether hourly runs
then arrive late but regularly, or are dropped, is what ops.html shows.

### An outside clock, if GitHub's schedule is not dependable

Nothing inside GitHub can wake a repository whose schedule does not fire. An outside clock can, for free. It takes one
account and one change to your token, and only you can make either:

1. Widen the token you already made. GitHub, Settings, Developer settings, Fine-grained tokens, `the-margin dispatch`,
   Repository access: add `tipping-point` and `fifty-two-keys` beside `the-margin`. Keep Contents: Read and write, nothing
   else. This is needed because a "check now" message is accepted only from a token that covers the repository it is sent
   to, and the token today covers The Margin alone. The two secrets already saved keep working; nothing in the repositories
   changes.
2. At cron-job.org (free, no card), make three jobs, one for each repository, each every hour at its own minute (5, 15, 35):
   - URL: `https://api.github.com/repos/KA82205/tipping-point/dispatches` (then `fifty-two-keys`, then `the-margin`)
   - Method: POST. Body: `{"event_type":"heartbeat"}`
   - Headers: `Authorization: Bearer` followed by the token, `Accept: application/vnd.github+json`, `Content-Type: application/json`
   A good answer is `204`. The service keeps a record of each call and can e-mail you when one fails.

The token then sits in that service's settings as well as in GitHub's. It can write to the three repositories' files and
nothing else of yours; if the service were ever compromised, delete the token on GitHub and make a new one. Each site treats
a heartbeat exactly as a scheduled run, so an hourly heartbeat on top of GitHub's own schedule only means more checks that
find nothing new.

## Secrets

Two secrets, both optional, both set under each repository's Settings, Secrets and variables, Actions. Never put either in
a file, a commit, a message or a chat.

**`FRED_API_KEY`** (Fifty-Two Keys; Tipping Point if it has one). A free key from fred.stlouisfed.org, My Account, API
Keys. Without it FRED's download links do not answer GitHub's servers and the economic figures are not refreshed; the run
says so and ends as failed.

**`DISPATCH_TOKEN`** (Fifty-Two Keys and Tipping Point). Lets a site tell The Margin the moment it has published something
new, and wake it when it has gone quiet. It is saved in both repositories and both have used it: Fifty-Two Keys at 19:01 UTC
and Tipping Point at 21:48 UTC on November 25, 2026. It is a fine-grained token with no expiry, limited to `the-margin`,
Contents: Read and write.

If it is ever revoked the two sites carry on, their logs say "No DISPATCH_TOKEN secret" or warn that The Margin could not be
told, and The Margin finds their changes at its own next run. To replace it: GitHub, Settings, Developer settings,
Fine-grained tokens, Generate new token; Only select repositories, `the-margin` (and the other two if the outside clock above
is in use); Repository permissions, Contents: Read and write; then save it as `DISPATCH_TOKEN` under Settings, Secrets and
variables, Actions in `tipping-point` and in `fifty-two-keys`, and delete the old token.

Without the token nothing breaks. The Margin's own scheduled run is the fallback.

## When a run ends as failed

A failed run means "somebody should look", not "the site is down". The page always shows the last good figures.

| The log says | What it means | What to do |
|---|---|---|
| A figure was held back | A new figure was outside its believable range or jumped too far. It was not used | Look at the series at its source. If it is real (a shock like spring 2020), start the workflow by hand with the series name in the `trust` box. If it is wrong, do nothing: the next good figure replaces it |
| Held: a key's evidence is late or in dispute | A key should have been callable by now and its evidence is missing, or an entry and the rule disagree | `KEYS.md` says what each key needs. The key keeps its chance and is never counted as no |
| Not read for N days | A source has not answered | Usually passes. If it lasts, check whether the source moved |
| A newer survey should be out and has not been read | The forecasters' survey was not reached, or its table changed shape | Find the line starting `The outlook:` in the log. If the table changed, `outlook.py` needs to learn the new layout; until then the older outlook is used and labelled with its date |
| Stale input (The Margin) | The Nowcast, the Keys feed, the odds or the state polls have not been read for a day or two | Check that the other site's page is up; the last copy is used meanwhile |
| The repository changed while this run was working | Two runs overlapped. The later one's result was dropped | Nothing: the next run starts from the new state |

To run any site again by hand: its repository, Actions, the workflow, Run workflow. Ticking `check` makes the run behave as
the hourly one does (stop if nothing is new); leaving it unticked runs everything.

## What is still done by hand, and when

| What | When | Where |
|---|---|---|
| The nominee's share of pledged delegates (key E04) | Once, when the primaries end in June 2028 | `fifty-two-keys/data/outlook.json`, the `settled` block, with its source |
| The New Hampshire primary line (keys E05 to E07) | Once, when both parties have a candidate with a majority of pledged delegates | `fifty-two-keys/data/nh_primaries.csv`, from the Secretary of State's certified results |
| The parts of the outlook the forecasters' survey does not give (income, pay, spending, industrial production, factory jobs, oil, sentiment, population), the 30% share of runs with a recession, and the odds for the nomination keys | When you judge they have changed. Each carries the date it was entered | `fifty-two-keys/data/outlook.json` |
| Who the nominees are | Once, when both are known | Tipping Point's candidate file; The Margin reads it from the Nowcast |
| State approval from Civiqs (Tipping Point) | When a new copy is taken. Civiqs offers no feed | as now |
| A forecast published by the authors of Tipping Point's models | If and when one appears | as Tipping Point's own notes say |
| A real economic move too large for the checks | If it happens: the run fails once a day and names the series | start the workflow by hand with the series in the `trust` box, after looking at it |
| A decision on any change to a published method | When you choose | see below |

No longer by hand: seats in Congress (counted from the public list of members each January after an election), the
third-candidate key (scored from the June 2028 polls), growth, jobs, unemployment and inflation in the outlook (read from
the forecasters' survey), and the allowance for approval still moving (it closes when the June polls are in).

Everything else is read by the workflows.

## Changing a published method

The published forecast is `model.SET` in `the-margin/model.py`. The versions under review are `CANDIDATE` and `HYBRID`
beside it; they are run on every forecast and written to the data file and the archive, not to the page.

To adopt the recommended version (the hybrid without the Fifty-Two Keys line): copy `RECOMMENDED`'s settings into `SET`,
add a line to `data/methods.json` saying what changed, run `python backtest.py` (this rewrites `data/backtest.csv`, which is
what `tests/test_model.py` guards), then `python checks.py`, `python status.py` and `python update.py --force`. The archive
keeps every forecast made before the change exactly as it was, and the page marks the day on its history chart.

Fifty-Two Keys' rules are locked (`locked_keys.csv`, `tests/test_model.py`) and are not changed by any of this.

## Checking that everything still works

    the-margin        python -m pytest tests && node tests/test_page.js && node tests/browser_hover.js && node tests/browser_page.js
    fifty-two-keys    python -m pytest tests
    tipping-point     python pipeline/tests/test_runs.py

Each workflow runs its repository's tests before it reads anything, and stops if one fails.

Every forecast The Margin has kept is in `docs/archive/` with the versions of the other two sites it was made from; the
Nowcast file itself is in `docs/archive/upstream/`. Fifty-Two Keys keeps its runs in `archive/` and its calls in
`data/key_calls.csv`; Tipping Point keeps its runs in `docs/record/`. None of these is ever rewritten.
