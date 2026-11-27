"""Money raised by each date: the FEC reports of each Senate nominee's campaign committees (tools/fetch_fec_reports.py),
turned into a table the back-test can read as of any day. Research.

    python senate/fec_money.py <fec_reports.json>     writes data/senate/money_reports.csv

A report counts from the day the FEC received it, not from the end of the period it covers, so a forecast made on a
date sees only the reports filed by then. Only the latest version of each report is kept (amendments replace it).
"""
import json, math, os, sys
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'data', 'senate', 'money_reports.csv')


def build(path):
    J = json.load(open(path)); rows = []
    for k, v in J.items():
        year, state, special, side = k.split('|')
        for r in v['reports']:
            if r.get('most_recent') is False: continue
            rows.append({'year': int(year), 'state': state, 'special': special == 'True', 'side': side, 'candidate_id': v['candidate_id'],
                         'committee_id': r['committee_id'], 'report_type': r['report_type'], 'coverage_end': (r['coverage_end_date'] or '')[:10],
                         'received': (r['receipt_date'] or '')[:10], 'receipts': r['total_receipts_period'] or 0.0,
                         'individual': r['total_individual_contributions_period'] or 0.0, 'cash_on_hand': r['cash_on_hand_end_period']})
    T = pd.DataFrame(rows).drop_duplicates(subset=['year', 'state', 'special', 'side', 'committee_id', 'report_type', 'coverage_end'])
    T.to_csv(OUT, index=False)
    return T


def table():
    return pd.read_csv(OUT, parse_dates=['received']) if os.path.exists(OUT) else None


def raised(T, year, state, special, asof):
    """(Democratic side, Republican side) receipts in reports the FEC had received by the date, this cycle."""
    t = T[(T.year == year) & (T.state == state) & (T.special == special) & (T.received <= asof)]
    return float(t[t.side == 'dem'].receipts.sum()), float(t[t.side == 'rep'].receipts.sum())


def money_feature(md, mr):
    return math.log((md + 1e5) / (mr + 1e5))


if __name__ == '__main__':
    T = build(sys.argv[1]); print(len(T), T.groupby('year').size().to_dict())
