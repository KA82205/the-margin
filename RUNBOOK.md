# Keeping the three sites running

This covers The Margin, Fifty-Two Keys and Tipping Point. Nothing here needs a computer of yours to be on, and nothing in
the normal course needs anyone to run a script.

## What runs, and what starts it

| Site | Workflow | What it reads | What starts it |
|---|---|---|---|
| Tipping Point | `Update data and deploy site` | approval polls, national polls, the economy (FRED), state approval | the schedule (minute 17 of each hour), a `heartbeat`, a push, a run started by hand |
| Fifty-Two Keys | `Update` | approval polls and polls naming a third candidate on every run; the economy (FRED), the forecasters' survey and, in the January after an election, the list of members of Congress, when a release could be out and on the day's first run | the schedule (minute 7), a `heartbeat`, a run started by hand |
| The Margin | `Forecast` | the Tipping Point Nowcast (its models, national polls, approval) and state polls. Prediction markets and the Fifty-Two Keys count are read for comparison only | the schedule (minute 37), a notification from either of the other two, a `heartbeat`, an outside clock, a run started by hand |

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
schedules went in on November 25, 2026, the first scheduled run started eight hours later. How late and how regular
they are is what ops.html shows; the outside clock below is for the hours they miss.

### An outside clock, if GitHub's schedule is not dependable

Nothing inside GitHub can wake a repository whose schedule does not fire. An outside clock can, for free. It asks each site
for its ordinary hourly check: read the sources, stop if nothing is new. It cannot force a forecast.

The token you already made (`DISPATCH_TOKEN`) is not touched and not widened. The clock gets a token of its own that can do
one thing: start and stop workflow runs in these three repositories. It cannot read or change a file, a setting or a secret,
and it is no use anywhere else in your account. Never paste it into a chat, an e-mail, a file or a commit: it goes from
GitHub's page straight into the scheduler's form.

**1. Make the token** (about three minutes)

1. GitHub, your picture at the top right, Settings, Developer settings (bottom of the left column), Personal access
   tokens, Fine-grained tokens, Generate new token.
2. Token name: `forecast clock`. Expiration: one year is GitHub's longest fixed choice; "No expiration" is offered too.
   With an expiry, GitHub e-mails you a week before and the three jobs below start failing on that day until the token is
   replaced.
3. Repository access: Only select repositories, and pick `the-margin`, `fifty-two-keys` and `tipping-point`.
4. Permissions, Repository permissions: set **Actions** to **Read and write**. Leave everything else at "No access".
   (GitHub adds Metadata: Read-only by itself.)
5. Generate token, and leave the page open: the token is shown once.

**2. Make the three jobs** (about five minutes)

At [cron-job.org](https://cron-job.org) (free, no card), sign up, then Create cronjob, three times:

| | Tipping Point | Fifty-Two Keys | The Margin |
|---|---|---|---|
| Title | `tipping-point check` | `fifty-two-keys check` | `the-margin check` |
| URL | `https://api.github.com/repos/KA82205/tipping-point/actions/workflows/update.yml/dispatches` | `https://api.github.com/repos/KA82205/fifty-two-keys/actions/workflows/update.yml/dispatches` | `https://api.github.com/repos/KA82205/the-margin/actions/workflows/update.yml/dispatches` |
| Schedule: every hour, at minute | 12 | 22 | 42 |

The same for all three, on the job's Advanced tab:

- Request method: `POST`
- Request body: `{"ref":"main","inputs":{"check":"true","source":"clock"}}`
- Headers, one a line:
  - `Authorization` : `Bearer ` followed by the token (the word Bearer, a space, the token)
  - `Accept` : `application/vnd.github+json`
  - `Content-Type` : `application/json`

Switch on "Notify me when the cronjob fails" on each. Use the form's test run before saving: the answer should be `200` or
`204`. `401` means the token was mistyped; `403` or `404` means the token does not cover that repository or lacks Actions:
Read and write; `422` means the body was not pasted exactly.

**3. Check it.** Within a minute of a test run, [ops.html](https://ka82205.github.io/the-margin/ops.html) shows a run named "Check: outside clock" for that
site, and "Last run started by an outside clock" turns to the time. The service switches a job off after 25 failures in a
row and tells you.

**What it costs to leave in place.** Each site treats the clock's run exactly as a scheduled one, so on top of GitHub's own
schedule it only means more checks that find nothing new. If the service were ever compromised, the most the token allows is
starting or cancelling runs of these three workflows; delete it on GitHub's token page and make another.

**To stop it:** delete the three jobs, then delete the token on GitHub.

## Secrets

Three secrets, all optional, set under each repository's Settings, Secrets and variables, Actions. Never put one in a file,
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

**`BLS_API_KEY`** (Fifty-Two Keys). Not needed. The second-source check asks the Bureau of Labor Statistics without a key,
which allows a few requests a day from each address; GitHub's servers share addresses, so on some days the Bureau may
answer that the allowance is used up. Then a held figure simply stays held until the next run. A free key from
bls.gov/developers, saved under this name, removes that limit.

## When a run ends as failed

A failed run means "somebody should look", not "the site is down". The page always shows the last good figures.

| The log says | What it means | What to do |
|---|---|---|
| A figure was held back | A new figure was outside its believable range or jumped too far, and its own agency did not confirm it. It was not used | For unemployment, payrolls, factory jobs, consumer prices and hourly pay the run has already asked the Bureau of Labor Statistics, and the line says what the Bureau answered; a real figure passes by itself once the Bureau gives it. For any other series, look at it at its source. If it is real, start the workflow by hand with the series name in the `trust` box. If it is wrong, do nothing: the next good figure replaces it |
| Held: a key's evidence is late or in dispute | A key should have been callable by now and its evidence is missing, or an entry and the rule disagree | `KEYS.md` says what each key needs. The key keeps its chance and is never counted as no |
| Not read for N days | A source has not answered | Usually passes. If it lasts, check whether the source moved |
| A newer survey should be out and has not been read | The forecasters' survey was not reached, or its table changed shape | Find the line starting `The outlook:` in the log. If the table changed, `outlook.py` needs to learn the new layout; until then the older outlook is used and labelled with its date |
| Stale input (The Margin) | The Nowcast has not been read for a day, or the state polls for two | Check that Tipping Point's page is up; the last copy is used meanwhile |
| Prediction markets: a provider was not read | One of Polymarket, Kalshi or Manifold did not answer | Nothing: the others are used, the last reading stays, and the forecast does not depend on any of them |
| The repository changed while this run was working | Two runs overlapped. The later one's result was dropped | Nothing: the next run starts from the new state |

To run any site again by hand: its repository, Actions, the workflow, Run workflow. Ticking `check` makes the run behave as
the hourly one does (stop if nothing is new); leaving it unticked runs everything.

## What is done by hand

Nothing, in the ordinary course. No figure, name, address or odds is typed in on any of the three sites.

What is left to a person is the exception, and each one announces itself:

| What | How you will know | What to do |
|---|---|---|
| The two sources for a nomination key (E04 to E07) disagree, or one cannot be read | The Fifty-Two Keys page shows the key as held with the reason; from 2028 the run fails once a day while it lasts | Usually nothing: the next run looks again. If it does not clear, put the figure in by hand with its source (`data/outlook.json` for E04, `data/nh_primaries.csv` for New Hampshire); the entry is compared with the sources |
| A large, real move in industrial production or housing starts | The Fifty-Two Keys run fails once a day and names the series | Look at it at its source, then start the workflow by hand with the series in the `trust` box. Every other series is confirmed against its publisher automatically |
| The authors of Tipping Point's models publish a 2028 forecast | Tipping Point's run carries a warning naming the article; `docs/watch.json` lists it | `python pipeline/put_in.py`, as Tipping Point's readme says |
| Civiqs state approval grows old | Tipping Point's page shows the date of the figures | Nothing is required. To refresh: `python pipeline/civiqs.py "saved page.html"` |
| A token lapses | GitHub e-mails you; the scheduling service e-mails when its jobs fail | Make a new one as above |

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
                      (the studies: python interval_study.py, market_study.py, method_change.py, keys_study.py, state_trend_study.py)
    fifty-two-keys    python -m pytest tests
    tipping-point     python pipeline/tests/test_runs.py

Each workflow runs its repository's tests before it reads anything, and stops if one fails.

Every forecast The Margin has kept is in `docs/archive/` with the versions of the other two sites it was made from; the
Nowcast file itself is in `docs/archive/upstream/`. Fifty-Two Keys keeps its runs in `archive/` and its calls in
`data/key_calls.csv`; Tipping Point keeps its runs in `docs/record/`. None of these is ever rewritten.
