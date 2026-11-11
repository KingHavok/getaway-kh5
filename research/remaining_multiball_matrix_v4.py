"""Port of authored historical controller remaining_multiball_matrix_v4. See research/provenance.json.
Run through tools/lab.py; inputs and raw outputs stay in the private workspace.
"""
import argparse

import concurrent.futures

import itertools

import json

import pathlib

import traceback

from fault_lab_candidate import session,setup,configure,ensure_playable,qualify_locks,collect_lock,installed

from readiness_multiplayer import wait_saver,drain_turn,lights

from readiness_shared_matrix import advance_to

from pilot_burn_rubber import tunnel

def mode_idle(api,extended):
    for _ in range((99 if extended else 20)*3+60):
        if 0xB7 not in api.state(tasks=True)['task_ids']:return
        api.call('input',sw=31,val=1);api.frames(6)
        api.call('input',sw=31,val=0);api.frames(54)
    raise TimeoutError('Fourth-gear mode did not finish')

def advance_with_burn(api,target,players,recipient,mode):
    for _ in range(players+1):
        s=api.state()
        if s['player']==target and s['phase']==[0,0,0]:return s
        ensure_playable(api)
        if mode=='burn' and s['player']==recipient:
            counter=0x937+(recipient-1)*54
            if api.memory(counter,1)[0]==0:
                for _ in range(3):
                    tunnel(api)
                    if api.memory(counter,1)[0]>0:break
                assert api.memory(counter,1)[0]==1,'Could not collect initial Burn Rubber before skipping turn'
                api.marker('initial-Burn-Rubber-collected-before-recipient-turn-skipped')
        s=api.state();drain_turn(api,s['player'],s['ball'])
    raise TimeoutError('Player turn not reached')

def redline(api,player,extended):
    for _ in range(45):
        s=api.state(tasks=True)
        if s['gears'][player-1]==5:break
        mode_idle(api,extended)
        api.pulse(4,'12',after=180)
        api.pulse(4,'400',on=12,after=180)
    assert api.state()['gears'][player-1]==5,'Could not qualify Redline through RPM/shifter'
    # Entering fifth gear is not completing its RPM requirement.
    for _ in range(6):api.pulse(4,'12',after=180)
    api.pulse(4,'5',after=600)
    state=api.wait('Redline three live balls',lambda s:s['live']==3,limit=2400)
    traces=api.call('debugger/tracepoints')['log']
    assert any(t['pc']==0x6AD4 and bytes.fromhex(t['ram'])[0x40F]==player for t in traces),'Redline initializer did not execute'
    return state

def burn_rubber(api,player,extended):
    for cycle in range(12):
        mode_idle(api,extended)
        for shot in range(3):
            s=tunnel(api)
            if s['live']>1:
                return api.wait('Burn Rubber three live balls',lambda s:s['live']==3,limit=2400)
        for _ in range(4):api.pulse(4,'12',after=180)
        api.pulse(4,'400',on=12,after=180)
    raise TimeoutError('Did not reach tournament Burn Rubber multiball')

def tilt(api):
    for _ in range(4):
        if api.state()['phase'][0]==1:return
        api.button('400',on=12,after=60)
    raise AssertionError('Tilt switch stimulus not accepted')

def restart_and_recover(api,players,slow):
    assert api.state()['ball']>=2,'Restart on ball 1 would add players'
    configure(api,{0x1B5F:1 if slow else 2})
    api.button('200',on=240 if slow else 12,after=300)
    api.wait('new game starts on player 1 ball 1',lambda s:(s['player'],s['ball'],s['phase'])==(1,1,[0,0,0]),limit=2400)
    # Preserve the test roster: player records can initialize lazily when added.
    for _ in range(players-1):api.button('200',after=120)
    assert api.memory(0x17A5,1)==bytes([players])
    # Drain only genuinely free old balls; never teleport or reset inventory.
    for _ in range(60):
        io=api.io();s=api.state(tasks=True)
        returned=sum(s['switches'][n] for n in [56,57,58])
        if returned==2 and not any(s['switches'][n] for n in [74,75,76]):
            # Search may automatically launch the newly served P1 ball. Two in
            # the trough plus one live ball is settled inventory in either the
            # shooter or playfield; do not drain that new ball to force a lane.
            if (s['player'],s['ball'],s['live'],s['phase'])==(1,1,1,[0,0,0]):break
            api.frames(30)
            continue
        if any(b['state']==258 for b in installed(io)):api.pulse(5,'2000',after=300)
        else:api.frames(60)
    else:raise TimeoutError('Old multiball balls did not settle after restart')
    s=api.state(tasks=True)
    assert (s['player'],s['ball'],s['live'],s['phase'])==(1,1,1,[0,0,0])
    assert s['lock_credits'][:players]==[0]*players
    assert not ({0x138,0x139} & set(s['task_ids']))
    clean=api.marker('restart-physical-inventory-settled')
    assert sum(s['switches'][n] for n in [56,57,58])==2
    ensure_playable(api);qualify_locks(api);collect_lock(api,1)
    accepted=api.marker('restart-new-game-legitimate-lock')
    assert accepted['state']['lock_credits'][0]==1
    return clean,accepted

def run_case(folder,port,spec):
    players,owner,recipient,locks=[spec[k] for k in ['players','owner','recipient','locks']]
    extended=spec['extended'];mode=spec['mode'];ending=spec['ending']
    with session(folder,port,__file__,game='gw_g6') as (api,r):
        setup(api,players=players,extended=extended)
        api.call('debugger/tracepoints',cmd='clear')
        for addr,bank in [('6253','2A'),('6A88','2A'),('6AD4','2A'),('56CB','2A'),('45A4','38')]:
            api.call('debugger/tracepoints',cmd='add',addr=addr,bank=bank)
        advance_with_burn(api,owner,players,recipient,mode);ensure_playable(api);qualify_locks(api)
        for credit in range(1,locks+1):
            collect_lock(api,credit,player=owner);ensure_playable(api)
        s=wait_saver(api);saved=dict(credits=s['lock_credits'][owner-1],gear=s['gears'][owner-1],
                                    qualified=s['qualified'],lights=lights(api),ball=s['ball'])
        assert saved['credits']==locks
        before=api.marker('owner-saved-before-recipient')
        drain_turn(api,owner,s['ball']);advance_with_burn(api,recipient,players,recipient,mode)
        if ending=='restart' and api.state()['ball']==1:
            ensure_playable(api)
            if mode=='burn' and api.memory(0x937+(recipient-1)*54,1)[0]==0:
                tunnel(api)
                assert api.memory(0x937+(recipient-1)*54,1)[0]==1
                api.marker('initial-Burn-Rubber-collected-before-restart-eligibility-turn')
            drain_turn(api,recipient,1);advance_with_burn(api,recipient,players,recipient,mode)
        assert ending!='restart' or api.state()['ball']>=2
        ensure_playable(api)
        if mode=='burn':
            # Spend any lit Burn Rubber before a replacement-launch shifter pull
            # can advance a completed gear and waste that gear's mystery relight.
            before_awards=api.memory(0x937+(recipient-1)*54,1)[0]
            for _ in range(3):
                state=tunnel(api)
                assert state['live']==1,'Burn MB occurred before the intended own-lock setup'
            assert api.memory(0x937+(recipient-1)*54,1)[0]>=before_awards
            api.marker('Burn-Rubber-collected-before-own-lock-and-replacement-launch')
        qualify_locks(api)
        own=3 if mode=='regular' else 1 if mode=='burn' else 2
        for credit in range(1,own+1):
            collect_lock(api,credit,player=recipient)
            if credit<3:ensure_playable(api)
        locked=api.marker('recipient-own-locks-before-mode')
        if mode=='regular':api.wait('regular MB initialized',lambda s:s['live']==3,limit=2400)
        elif mode=='burn':burn_rubber(api,recipient,extended)
        else:redline(api,recipient,extended)
        api.frames(300)
        mb=api.marker('recipient-multiball')
        assert mb['state']['lock_credits'][owner-1]==locks
        assert mb['state']['phase']==[0,0,0] and len(installed(mb['io']))==3
        if ending=='restart':
            clean,accepted=restart_and_recover(api,players,spec.get('slow_restart',False))
            final=accepted
        else:
            if ending=='tilt':tilt(api)
            drain_turn(api,recipient,mb['state']['ball']);advance_to(api,owner,players)
            returned=api.wait('owner next turn after recipient MB',lambda s:s['player']==owner
                              and s['ball']==saved['ball']+1 and s['switches'][78] and s['live']==1,limit=2400)
            assert returned['lock_credits'][owner-1]==saved['credits'],'Other player MB changed lock credit'
            assert returned['gears'][owner-1]==saved['gear'],'Other player MB changed gear'
            assert returned['qualified']==saved['qualified'] and lights(api)==saved['lights'],'Other player MB changed lock/light progress'
            assert not any(returned['switches'][n] for n in [74,75,76])
            owner_return=api.marker('owner-returned-with-virtual-locks')
            ensure_playable(api)
            for credit in range(locks+1,4):
                collect_lock(api,credit,player=owner)
                if credit<3:ensure_playable(api)
            api.wait('owner virtual-lock MB',lambda s:s['live']==3,limit=2400)
            final=api.marker('owner-legitimate-multiball')
            r['owner_returned']=owner_return
        traces=api.call('debugger/tracepoints')['log'];assert len(traces)<512
        normal=[bytes.fromhex(t['ram'])[0x40F] for t in traces if (t['pc'],t['bank'])==(0x6253,0x2A)]
        rlm=[bytes.fromhex(t['ram'])[0x40F] for t in traces if (t['pc'],t['bank'])==(0x6A88,0x2A)]
        assert rlm==([recipient] if mode=='redline' else []),('Unexpected Redline entries',rlm)
        assert normal==(([recipient] if mode!='redline' else [])+([owner] if ending!='restart' else [])),('Unexpected ordinary MB entries',normal)
        assert not any(t['pc']==0x56CB for t in traces),'Unplanned Secret Mania entry'
        assert sum((t['pc'],t['bank'])==(0x45A4,0x38) for t in traces)==int(ending=='restart')
        (folder/'traces.json').write_text(json.dumps({'log':traces},indent=2)+'\n')
        r.update(result='PASS',specification=spec,saved_owner=saved,before=before,
                 recipient_own_locks=locked,recipient_multiball=mb,final=final,
                 native_normal_start_players=normal,native_redline_start_players=rlm,
                 limits=['Selected mode/ending/operator profiles and directed pairs; not all shot timings',
                         'Native mode entry, turn/accounting and progress assertions; not all scoring awards',
                         'Digital output traces do not certify coil current, heat or ball release force'])
    return r

def design():
    return [dict(players=p,owner=o,recipient=r,locks=l,extended=x,mode=m,ending=e)
            for p in [2,3,4] for o,r in itertools.permutations(range(1,p+1),2)
            for l,x,m,e in itertools.product([1,2],[False,True],['regular','burn','redline'],['drain','tilt','restart'])
            if (m,e)!=('regular','drain')]
from lab.config import REPO as ROOT
