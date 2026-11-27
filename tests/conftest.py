# The Senate tests are scripts, each run on its own (python tests/test_senate_live.py and so on: RUNBOOK.md). Collected
# with the presidential tests in one process, they would load the Senate's backtest.py in place of the presidential one,
# so pytest leaves them out.
collect_ignore = ['test_senate_live.py', 'test_after_election.py', 'test_fec_live.py', 'test_senate_health.py']
