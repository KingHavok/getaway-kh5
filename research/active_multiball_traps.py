"""Port of authored historical controller active_multiball_traps. See research/provenance.json.
Run through tools/lab.py; inputs and raw outputs stay in the private workspace.
"""
import hashlib,itertools,json,pathlib,time,traceback

import fault_campaign_v3 as regular

import remaining_multiball_matrix_v4 as modes

from fault_lab_candidate import session,setup,ensure_playable,qualify_locks,collect_lock,installed

from readiness_multiplayer import wait_saver

from pilot_donut_trap import edge

from donut_ramp_tests import down

def searches(api):return [t for t in api.call('debugger/tracepoints')['log'] if (t['pc'],t['bank'])==(0x481A,0x30)]

def trap(api,label):
    api.wait('qualified ramp down before slow right passage',lambda s:s['switches'][54]==1,limit=2400,activity=True)
    edge(api,18);edge(api,17);up=api.marker(label+'-entry-lift');assert down(up['io'])==0
    api.frames(180);stuck=api.marker(label+'-dropped-without-exit');assert down(stuck['io'])==1
    return up,stuck

def run(folder,port,mode,game):
    with session(folder,port,__file__,game=game) as (api,r):
        locks=2 if mode=='redline' else 0
        r['specification']=dict(scenario='active-multiball-'+mode,trap_mode=mode,locks=locks,extended=True)
        r['reused_contract_sources']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [pathlib.Path(regular.__file__),pathlib.Path(modes.__file__)]}
        setup(api,extended=True);ensure_playable(api)
        api.call('debugger/tracepoints',cmd='add',addr='6AD4',bank='2A')
        if mode=='regular':regular.start_mb(api)
        else:
            qualify_locks(api)
            for credit in [1,2]:collect_lock(api,credit);ensure_playable(api)
            modes.redline(api,1,True)
        wait_saver(api)
        # Ordinary MB begins with the jackpot ramp up. Earn the lit jackpot
        # through actual Supercharger shots before creating a dropped-ramp trap.
        # The retained successful regular-MB pilot confirms this precondition;
        # Redline already lights the down-ramp award on entry.
        shots=0
        if mode=='regular':
            for _ in range(12):
                if api.state()['switches'][54]==1:break
                api.pulse(4,'5',after=300);shots+=1
            api.wait('jackpot qualified through Supercharger loops',lambda s:s['switches'][54]==1,limit=2400,activity=True)
        r['supercharger_qualification_shots']=shots
        api.wait('three actual free simulator balls',lambda s:sum(b['state']==258 for b in installed(api.io()))==3,limit=2400,activity=True)
        api.wait('ramp ready for right passage',lambda s:s['switches'][54]==1,limit=2400,activity=True)
        before=api.marker('before-active-MB-right-passage');assert before['state']['live']==3
        first,first_trap=trap(api,'first')
        for _ in range(3):edge(api,31);api.frames(174)
        assert not any(t['time']>=first['io']['time'] for t in searches(api)),'Search ran despite ongoing playfield activity'
        # Another ball using the right passage should provide an earlier lift,
        # without requiring the idle search timer. Ball identity is aggregate.
        edge(api,18);edge(api,17);other=api.marker('another-right-passage-lifts-trapped-ball');assert down(other['io'])==0
        edge(api,16);edge(api,15);api.frames(180)
        second,stuck=trap(api,'second')
        for _ in range(10):edge(api,31);api.frames(174)
        active=api.marker('other-balls-active-for-thirty-seconds')
        assert active['state']['live']==3 and down(active['io'])==1
        assert not any(first['io']['time']<=t['time']<=active['io']['time'] for t in searches(api))
        for live in [2,1]:
            api.pulse(5,'2000',after=300);api.wait('drained other ball',lambda s:s['live']==live,limit=1800)
        survivor=api.marker('only-unswitched-trapped-ball-remains')
        assert (survivor['state']['player'],survivor['state']['ball'],survivor['state']['phase'])==(1,1,[0,0,0])
        for _ in range(1200):
            if down(api.io())==0 and any(t['time']>active['io']['time'] for t in searches(api)):break
            api.frames(6)
        else:raise TimeoutError('No search-driven lift after other multiball balls drain')
        lifted=api.marker('quiet-search-lift-releases-survivor');edge(api,16);edge(api,15);api.frames(180)
        after_search=len(searches(api))
        for _ in range(6):edge(api,31);api.frames(174)
        found=api.marker('survivor-returned-to-active-play')
        assert len(searches(api))==after_search
        assert (found['state']['player'],found['state']['ball'],found['state']['live'],found['state']['phase'])==(1,1,1,[0,0,0])
        assert found['state']['lock_credits'][0]==locks
        qualify_locks(api);collect_lock(api,locks+1);api.frames(600)
        final=api.marker('same-ball-legitimate-lock-after-trap-recovery')
        assert final['state']['lock_credits'][0]==locks+1 or final['state']['live']==3
        log=api.call('debugger/tracepoints')['log'];assert len(log)<512
        normal=[t for t in log if (t['pc'],t['bank'])==(0x6253,0x2A)]
        red=[t for t in log if (t['pc'],t['bank'])==(0x6A88,0x2A)]
        assert len(normal)==1 and len(red)==(mode=='redline')
        assert (normal[0]['time']>found['io']['time'])==(mode=='redline')
        assert not any((t['pc'],t['bank'])==(0x56CB,0x2A) for t in log)
        (folder/'traces.json').write_text(json.dumps({'log':log},indent=2)+'\n')
        r.update(result='PASS',before=before,first_passage_lift=first,trapped=stuck,release_lift=lifted,
                 first_trap=first_trap,another_passage_lift=other,second_passage_lift=second,
                 other_balls_active=active,survivor=survivor,found=found,final=final,
                 limits=['G-5 is the matched baseline with the same gameplay fixes; not an official-L-5 control',
                         'Aggregate switch/ball-count model, not per-ball collision, travel-time or release-force physics',
                         'Playfield activity suppresses idle search; another right-passage arrival can lift the ramp earlier'])
from lab.config import REPO as ROOT
