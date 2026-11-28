"""The governor forecast's readers and checks (governor/): the overview's table of races in its older and newer forms,
what a governor has said about running, the nominees once named, the governors of the states with no race, the same
person told apart, and the checks that stop a run.
    python tests/test_governor.py
"""
import os, sys
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, os.path.join(ROOT, 'governor'))
import wiki_governor as WG, gov_live as GL

OLD = """== Race summary ==
{| class="wikitable sortable"
|- valign=bottom
! State
! Incumbent
! Party
! First<br />elected
! Result
! Candidates
|-
! [[#Alabama|Alabama]]
| {{sortname|Bob|Riley}}
| {{party shading/Republican}} | Republican
| [[2002 Alabama gubernatorial election|2002]]
| Incumbent [[2006 Alabama gubernatorial election|re-elected]].
| nowrap | {{plainlist|
* {{party stripe|Republican Party (US)}}{{aye}} '''{{sortname|Bob|Riley}}''' (Republican) 57.5%
* {{party stripe|Democratic Party (US)}}[[Lucy Baxley]] (Democratic) 41.6%
}}
|-
! [[#Alaska|Alaska]]
| {{sortname|Frank|Murkowski}}
| {{party shading/Republican}} | Republican
| [[2002 Alaska gubernatorial election|2002]]
| {{party shading/Republican/Hold}} | Incumbent lost renomination.<br />New governor [[2006 Alaska gubernatorial election|elected]].<br />'''Republican hold'''.
| nowrap | {{plainlist|
* {{party stripe|Republican Party (US)}}{{aye}} '''{{sortname|Sarah|Palin}}''' (Republican) 48.3%
* {{party stripe|Democratic Party (US)}}[[Tony Knowles (politician)|Tony Knowles]] (Democratic) 41.0%
}}
|}
"""
NEW = """== Race summary ==
=== States ===
{| class="wikitable sortable"
|- valign=bottom
! State
! Governor
! Party
! First<br />elected
! Last race
! Status
! Candidates
|-
! [[#Delaware|Delaware]]
| {{sortname|Matt|Meyer}}
| {{party shading/Text/Democratic}}
| [[2024 Delaware gubernatorial election|2024]]
| {{party shading/Democratic}} data-sort-value=-56.1 | 56.1% D
| Incumbent’s intent unknown
| TBD
|-
! [[#Montana|Montana]]
| {{sortname|Greg|Gianforte}}
| {{party shading/Text/Republican}}
| [[2020 Montana gubernatorial election|2020]]
| {{party shading/Republican}} data-sort-value=58.9 | 58.9% R
| {{party shading/Hold}} | Incumbent term-limited
| TBD
|-
! [[#Indiana|Indiana]]
| {{sortname|Mike|Braun}}
| {{party shading/Text/Republican}}
| [[2024 Indiana gubernatorial election|2024]]
| {{party shading/Republican}} data-sort-value=54.4 | 54.4% R
| Incumbent running
|{{plainlist|
*{{Party stripe|Republican Party (US)}}[[Mike Braun]] (Republican)
*{{Party stripe|Democratic Party (US)}}Jane Roe (Democratic)
}}
|}
"""


def main():
    bad = []; check = lambda ok, msg: ok or bad.append(msg)
    a = WG.races(OLD, 2006)
    check([(r['state'], r['governor'], r['party']) for r in a] == [('AL', 'Bob Riley', 'R'), ('AK', 'Frank Murkowski', 'R')], f'the older table: {a}')
    check(a[0]['candidates'][0]['won'] and a[0]['candidates'][0]['share'] == 57.5 and 'lost renomination' in a[1]['status'], f'winners and statuses: {a}')
    b = WG.races(NEW, 2028)
    check([(r['state'], r['governor'], r['party'], r['last_race']) for r in b] == [('DE', 'Matt Meyer', 'D', '56.1% D'), ('MT', 'Greg Gianforte', 'R', '58.9% R'), ('IN', 'Mike Braun', 'R', '54.4% R')], f'the newer table: {b}')
    check([GL.plan(r['status']) for r in b] == ['unknown', 'term', 'running'], f'what governors said: {[r["status"] for r in b]}')
    check(WG.nominees(b[0]) is None and WG.nominees(b[2]) == ('Jane Roe', 'Mike Braun'), f'nominees: {WG.nominees(b[2])}')
    for s, want in {'Incumbent retiring': 'out', 'Incumbent running for U.S. Senate': 'out', 'Incumbent lost renomination': 'out', 'Incumbent renominated': 'nominee', '': 'unknown'}.items():
        check(GL.plan(s) == want, f'"{s}" reads as {GL.plan(s)}, not {want}')
    check(WG.same_person('Mike Braun', 'Michael Braun') and WG.same_person('Kay Ivey', 'Kay E. Ivey') and not WG.same_person('Mike Braun', 'Mike Pence'), 'the same person, and not')
    # the states with no race: the winner of their last election
    pages = {WG.overview(2026): {'text': OLD.replace('2006', '2026')}, WG.overview(2028): {'text': NEW}}
    hold, up = GL.holdovers(pages, [2028])
    check(hold == {'AL': 'R', 'AK': 'R'} and up == {'DE', 'MT', 'IN'}, f'holdovers: {hold}, {up}')
    # the checks that stop a run
    try:
        GL.validate(pd.DataFrame({'state': ['DE'], 'lean': [8.0]}), hold, up, {'blend': 52.0}); bad.append('five states passed the checks')
    except RuntimeError as e:
        check('states accounted for' in str(e), f'the checks: {e}')
    print('\n'.join(bad) if bad else 'all governor checks pass'); return not bad


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
