"""Authored wrappers for active-MB traps and right-entry sensor failures.
Ports remove old queue/file coordination; stimulus and recovery assertions remain.
"""
import contextlib,hashlib,pathlib
from unittest.mock import patch
from .runtime import session,qualify_locks
from pilot_donut_trap import edge
from donut_ramp_tests import down

def active(folder,port,mode,game='gw_g6'):
 import active_multiball_traps as original
 if mode!='regular':return original.run(folder,port,mode,game)
 records={};qualify=original.qualify_locks

 @contextlib.contextmanager
 def owned(folder, port, source, game):
     with session(folder, port, __file__, game=game) as (api, record):
         record.update(contract_source=str(source),
                       contract_source_sha256=hashlib.sha256(pathlib.Path(source).read_bytes()).hexdigest(),
                       fixture_revision='regular follow-up waits for native Getaway cleanup')
         records[api] = record
         try:
             yield api, record
         finally:
             records.pop(api)

 def qualify_after_grace(api):
     state = api.state(tasks=True)
     assert (state['player'], state['ball'], state['live'], state['phase']) == (1, 1, 1, [0, 0, 0])
     assert state['qualified'] == 0 and state['lock_credits'][0] == 0
     assert {0xF7, 0x89} <= set(state['task_ids'])
     for address in ['6DC8', '6DCD', '6DDB', '4755', '475C']:
         api.call('debugger/tracepoints', cmd='add', addr=address, bank='2A')
     before = api.marker('before-normal-target-during-Getaway-grace')
     edge(api, 51)
     blocked = api.marker('normal-target-during-grace-does-not-qualify-new-lock')
     assert blocked['state']['qualified'] == 0
     samples = []
     for _ in range(230):
         state = api.state(tasks=True)
         counter = api.memory(0x874, 1)[0]
         samples.append(dict(frame=api.frames_run, counter=counter,
                             grace=0xF7 in state['task_ids'], gate=0x89 in state['task_ids']))
         if counter == 0 and not ({0xF7, 0x89} & set(state['task_ids'])):
             break
         edge(api, 31)
         api.frames(54)
     else:
         raise TimeoutError('Native Getaway grace did not finish after trap recovery')
     ended = api.marker('Getaway-cleanup-complete-before-new-lock-qualification')
     assert (state['player'], state['ball'], state['live'], state['phase']) == (1, 1, 1, [0, 0, 0])
     assert state['qualified'] == state['lock_credits'][0] == 0
     qualify(api)
     qualified = api.marker('new-lock-qualified-after-native-grace-cleanup')
     records[api]['regular_grace_followup'] = dict(before=before, blocked=blocked, samples=samples,
                                                  ended=ended, qualified=qualified)

 with patch.object(original,'session',owned),patch.object(original,'qualify_locks',qualify_after_grace):
  return original.run(folder,port,mode,game)


def entry_fault(folder,port,spec,game='gw_g6'):
 import fault_campaign_v3 as contract

 @contextlib.contextmanager
 def owned(folder,port,source,game):
     with session(folder,port,__file__,game=game) as (api,r):
         r.update(contract_source=str(source),contract_source_sha256=hashlib.sha256(pathlib.Path(source).read_bytes()).hexdigest())
         fault,marker=api.fault,api.marker
         def inject(kind,n,value):
             if value>=0:
                 qualify_locks(api);api.wait('ramp down before right-passage sensor fault',lambda s:s['switches'][54]==1)
                 for address in ['4932','4152','4C09','4C7B','4C1A','4C82','5B44']:
                     api.call('debugger/tracepoints',cmd='add',addr=address,bank='2A')
             result=fault(kind,n,value)
             if value==-1:
                 # Do not claim a free simulator slot means a trapped ball
                 # has escaped. Require a model lift before return contacts.
                 for _ in range(1200):
                     if down(api.io())==0:break
                     api.frames(6)
                 else:raise TimeoutError('No ramp-model lift after repairing entry sensor')
                 r['entry_fault_repaired_lift']=marker('repaired-right-entry-lift-permits-return')
                 edge(api,16);edge(api,15);api.frames(180)
                 r['entry_fault_return']=marker('repaired-entry-ball-returned-through-left-contacts')
             return result
         def marked(name):
             snap=marker(name)
             if name=='fault-before-stimulus':
                 edge(api,18);edge(api,17);api.frames(180)
                 r['right_entry_after_stimulus']=marker('right-entry-contact-impulse-complete')
             return snap
         api.fault=inject;api.marker=marked
         yield api,r

 with patch.object(contract,'session',owned):return contract.run_case(folder,port,spec,game)


def shared_casual(folder,port,spec):
 import readiness_shared_matrix as workflow
 configure=workflow.configure
 def casual(api,values):
  if values[0x1B51]!=1:raise AssertionError('Unexpected tournament source profile')
  configure(api,{**values,0x1B51:0})
 with patch.object(workflow,'configure',casual):return workflow.run_case(folder,port,spec)
