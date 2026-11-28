"""The health of each Senate, House and governor job, for anyone watching from outside: docs/api/health/<job>.json, on the site at
https://ka82205.github.io/the-margin/api/health/<job>.json. Each says whether the job's last run worked, the day it last
ran and last worked, the day after which no new success means the job has stopped, and, when the last run failed, why.
A file is saved only when one of these changes, so a healthy job changes its file once a day.

    python senate/health.py <job> <outcome> [log]   records a run: outcome is the run step's (success, failure,
                                                   cancelled or skipped), log what the run printed
    python senate/health.py --due <job>             exits 0 if the hourly job should start this one now

Jobs: senate-forecast (senate.yml), senate-money (senate-money.yml), senate-after (senate-after.yml), house-forecast
(house.yml), house-after (house-after.yml), governor-forecast (governor.yml) and governor-after (governor-after.yml). The
error kept is
the last one the run printed. An FEC key is masked before anything is saved, should one ever appear in what was printed.
"""
import json, os, re, sys
from datetime import date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
OUT = os.environ.get('SENATE_HEALTH_DIR') or os.path.join(ROOT, 'docs', 'api', 'health')
REPO = 'https://github.com/KA82205/the-margin'
# job: (how often it runs, its workflow, what it does, days after the last success before the job counts as stopped)
JOBS = {
    'senate-forecast': ('every hour, after each run of the presidential forecast', 'senate.yml',
                        'The Senate forecast: reads Wikipedia, reruns the forecast and writes data/senate/<year>/ and '
                        'docs/api/senate.json, which the Senate tab reads. A run whose readings look wrong stops and '
                        'leaves the last forecast in place.', 1),
    'senate-money': ('every day', 'senate-money.yml',
                     "Money raised by each Senate candidate, from the FEC, shown on the Senate tab (not used in the "
                     "forecast). A run that cannot reach the FEC leaves the last totals in place.", 2),
    'senate-after': ('every week', 'senate-after.yml',
                     'After each Senate election, once its results have settled: adds its races to the training data, '
                     'refits the model for the next election and remakes the back-tests. Between elections it finds '
                     'nothing to do, which counts as working.', 8),
    'house-forecast': ('every hour, after each run of the Senate forecast', 'house.yml',
                       "The House forecast: reads Wikipedia's overview of the election, takes the national mood from the "
                       'Senate forecast, reruns the forecast and writes data/house/<year>/ and docs/api/house.json, which '
                       'the House tab reads. A run whose readings look wrong stops and leaves the last forecast in place.', 1),
    'house-after': ('every week', 'house-after.yml',
                    "After each House election, once its results have settled and Wikipedia has every district's result: "
                    'adds its districts to the training data, refits the model and remakes the back-tests. Between '
                    'elections it finds nothing to do, which counts as working.', 8),
    'governor-forecast': ('every hour, after each run of the Senate forecast', 'governor.yml',
                          "The governor forecast: reads Wikipedia's overviews and race pages of the coming governor races, "
                          'takes the national mood from the Senate forecast, reruns the forecast and writes '
                          'data/governor/<year>/ and docs/api/governor.json, which the Governors tab reads. A run whose '
                          'readings look wrong stops and leaves the last forecast in place.', 1),
    'governor-after': ('every week', 'governor-after.yml',
                       "After each year's governor races, once their results have settled and Wikipedia has every race's "
                       'result: adds them and their polls to the training data, refits the model and remakes the '
                       'back-tests. Between elections it finds nothing to do, which counts as working.', 8),
}
# the hourly jobs start these when their last run is this many days old (their own schedules are a second way in)
DUE_EVERY = {'senate-money': 1, 'senate-after': 7, 'house-after': 7, 'governor-after': 7}
# a run that ended well but printed one of these did not do its job
PROBLEMS = {'senate-after': r'not added yet', 'house-after': r'not added yet', 'governor-after': r'not added yet'}
READ = ('ok false: the last run failed, error says why, and the site keeps the last good figures. ok true but today later '
        'than overdue_after: the job has stopped running. The workflow link lists every run.')


def today():
    if os.environ.get('SENATE_TODAY'): return date.fromisoformat(os.environ['SENATE_TODAY'][:10])
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo('America/New_York')).date()
    except Exception:                                              # noqa: BLE001 - no time zone data: Eastern standard time
        return (datetime.now(timezone.utc) - timedelta(hours=5)).date()


def path(job):
    return os.path.join(OUT, f'{job}.json')


def mask(text):
    key = os.environ.get('FEC_API_KEY', '')
    if key: text = text.replace(key, '***')
    text = re.sub(r'(api_key=)[^&\s\'"]+', r'\1***', text)
    return re.sub(r'\b[A-Za-z0-9]{32,}\b', '***', text)


def read_log(log):
    if not log or not os.path.exists(log): return []
    with open(log, errors='replace') as f: return [l.rstrip() for l in f if l.strip()]


def error_of(lines, outcome):
    if outcome == 'cancelled': return 'The run was stopped before it finished (it ran past its time limit, or was cancelled).'
    if outcome == 'skipped': return 'The run never started: a step before it failed (getting the code, Python or its packages).'
    if not lines: return 'The run stopped before it printed anything.'
    exc = [l for l in lines if re.match(r'[\w.]*(Error|Exception)\b', l)]
    hit = exc[-1:] or [l for l in lines if re.search(r'could not|does not look right|not added yet|not set|failed', l)][-2:] or lines[-3:]
    return mask(' | '.join(hit))[-600:]


def record(job, outcome, log=None):
    when, wf, what, grace = JOBS[job]
    lines = read_log(log)
    problem = [l for l in lines if PROBLEMS.get(job) and re.search(PROBLEMS[job], l)]
    ok = outcome == 'success' and not problem
    os.makedirs(OUT, exist_ok=True)
    try:
        with open(path(job)) as f: old = json.load(f)
    except (OSError, ValueError):
        old = {}
    now = str(today()); last = now if ok else old.get('last_success')
    new = {'job': job, 'ok': ok, 'last_run': now, 'last_success': last,
           'overdue_after': str(date.fromisoformat(last) + timedelta(days=grace)) if last else None,
           'failing_since': None if ok else (old.get('failing_since') if old.get('ok') is False else now),
           'error': None if ok else (mask(' | '.join(problem[-2:]))[-600:] if problem else error_of(lines, outcome)),
           'runs': when, 'what': what, 'workflow': f'{REPO}/actions/workflows/{wf}', 'how_to_read': READ}
    if new == old:
        print(f'{job}: health unchanged ({"working" if ok else "failing"})')
    else:
        with open(path(job), 'w') as f: json.dump(new, f, indent=1)
        print(f'{job}: health saved ({"working" if ok else "failing: " + new["error"]})')
    return new


def due(job):
    try:
        with open(path(job)) as f: last = json.load(f).get('last_run')
    except (OSError, ValueError):
        return True
    return not last or (today() - date.fromisoformat(last)).days >= DUE_EVERY[job]


if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == '--due':
        sys.exit(0 if due(a[1]) else 1)
    record(a[0], a[1], a[2] if len(a) > 2 else None)
