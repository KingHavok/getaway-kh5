"""Adapt retained controllers to explicit portable case parameters and audits."""
import importlib,json,shutil
from pathlib import Path
from . import runtime
from .config import REPO

def module(name):return importlib.import_module(name)

def execute(case,folder,port,batch):
 s=case['specification'];group=case['group'];role=case.get('controller_role','gw_g6')
 if group=='calibration':
  from .calibration import run
  return run(folder,port)
 if group=='replay-award':
  from .replay_awards import run
  return run(folder,port,s['award'])
 if group=='multiball-casual':
  from .extensions import shared_casual
  return shared_casual(folder,port,s)
 if group=='devices':return module('fault_campaign_v3').run_case(folder,port,s,role)
 if group=='donut':return module('donut_ramp_tests').run_case(folder,port,s,role)
 if group=='endurance':return module('coil_endurance_tests_v2').run_case(folder,port,s,role)
 if group=='multiball':
  if (s['mode'],s['ending'])==('regular','drain'):return module('readiness_shared_matrix').run_case(folder,port,s)
  return module('remaining_multiball_matrix_v4').run_case(folder,port,s)
 if group=='ordinary':
  with runtime.session(folder,port,__file__) as (api,r):r.update(module('readiness_games').full_game(api,s['balls'],s['players'],s['extended']))
 elif group=='soak':
  with runtime.session(folder,port,__file__) as (api,r):
   games=[]
   for index in range(s.get('games',40)):
    before=api.frames_run;b,p,x=(3,1,False) if index%2==0 else (5,4,True)
    row=module('readiness_games').full_game(api,b,p,x);row['frames']=api.frames_run-before;row['game_number']=index+1;games.append(row)
   r.update(result='PASS',games=games,ordinary_turns=sum(len(g['ordinary_turns']) for g in games),restarts_between_games=0)
 elif group=='active-trap':
  from .extensions import active
  return active(folder,port,s['mode'],role)
 elif group=='entry-fault':
  from .extensions import entry_fault
  return entry_fault(folder,port,s,role)
 elif group=='search':return module('readiness_recovery').run_case(folder,port,s['locks'],s['stage'])
 elif group=='donut-long':return module('donut_ramp_endurance').run(folder,port,s['scenario'],role)
 elif group=='flipper':return module('flipper_fault_tests_v2').run_case(folder,port,role,s['flipper'],s['forced'])
 elif group=='settings':return module('readiness_pairwise').run_case(folder,port,s)
 elif group=='countdown':return module('readiness_getaway_countdown' if s['mode']=='getaway' else 'readiness_sc_countdown').run_case(folder,port,s['value'])
 elif group=='b6':return module('b6_reproduce_v7' if s['casual'] else 'b6_reproduce_v5').run_official(folder,port,s['history'],s['delay'])
 elif group=='feature':return feature(s,folder,port,batch)
 elif group=='boot':
  from .native import boot
  return boot(folder,port)
 elif group=='pwm-unit':
  from .pwm import run
  return run(folder,port)
 elif group=='variant':
  from .variants import run
  return run(case,folder,port)
 else:raise ValueError('No controller for group '+group)

def feature(spec,folder,port,batch):
 name=spec['name']
 if name.startswith('menu_'):
  from .replay import actions
  profile=name.split('_',1)[1]
  with runtime.session(folder,port,__file__) as (api,r):
   _,diffs,assertions,_=actions(api,REPO/'research/inputs'/f'menu-{profile}.json',folder)
   if diffs or assertions!=5:raise AssertionError('Native menu assertions missing')
   r.update(result='PASS',native_menu=True,menu_profile=profile,configuration_writes=0,final=api.marker('native-menu-complete'))
  return
 if name.startswith('persist_'):
  profile=name.split('_',1)[1];entry=runtime.PROJECT['images'][runtime.selected()]
  seed=batch/('menu_'+profile)/'runtime/nvram'/(entry['driver']+'.nv')
  if not seed.exists():raise ValueError('Run the matching menu case before its cold-boot persistence case')
  expected={0x1B1F:5 if profile=='kids' else 3,0x1B39:3,0x1B9D:1,0x1BCB:99 if profile=='kids' else 20,0x1BD5:99 if profile=='kids' else 20}
  with runtime.session(folder,port,__file__,nvram_seed=seed) as (api,r):
   api.frames(1200)
   actual={address:int.from_bytes(api.memory(address,2),'big') for address in expected}
   if actual!=expected:raise AssertionError('Native menu words did not persist')
   api.button('200',after=300);state=api.state()
   if (state['player'],state['ball'],state['live'],state['phase'])!=(1,1,1,[0,0,0]):raise AssertionError('Persisted free-play start failed')
   r.update(result='PASS',native_menu_persistence=True,settings=actual,final=api.marker('persisted-free-play-start'))
  return
 maps={'mixed_reference':'release_g6_mixed_v2','mixed_kids':'release_g6_mixed_v2','secret_eb':'release_g6_awards_v3',
  'special':'release_g6_special_v1','casual_reference':'release_g6_casual_v1','casual_kids':'release_g6_casual_v1',
  'video_complete':'release_g6_video_v11','video_extra':'release_g6_video_v12'}
 return module(maps[name]).run_case(folder,port,spec)

def qualify(case,folder,project):
 r=json.loads((folder/'result.json').read_text())
 if r['result']!='PASS':raise AssertionError('Controller did not pass')
 if r['image_sha256']!=project['images'][case['image']]['identity']['sha256']:raise AssertionError('Wrong image identity')
 if not r['source_nvram_unchanged']:raise AssertionError('Seed NVRAM changed')
 group=case['group'];spec=case['specification']
 if group not in ['pwm-unit','calibration']:
  from .driver import check_log
  check_log(folder/'runtime/PRIVATE-emulator.log')
 if group=='calibration':return dict(contract='Independent known-cycle instrumentation waveform; selected firmware not executed',sensor_checks=len(r['sensor_checks']),expected_pulse_seconds=r['expected_pulse_seconds'],observed_pulse_seconds=r['observed_pulse_seconds'])
 if group=='pwm-unit':return dict(contract='8192 native PWM vectors; not gameplay',vectors=r['vectors'])
 if group=='boot':return dict(contract='Native reset ROM-test success branch',checksum=r['native_checksum'])
 if group in ['devices','donut','endurance','multiball','entry-fault','multiball-casual']:
  return module('campaign_contracts').audit(folder,coils=True,specification=spec)
 rows=[json.loads(line) for line in (folder/'actions.jsonl').read_text().splitlines()]
 frames=sum(x['params']['count'] for x in rows if x['path']=='debugger/control' and x['params'].get('cmd')=='frames')
 if frames!=r['frames']:raise AssertionError('Frame accounting differs')
 if group=='feature' and not spec['name'].startswith(('menu_','persist_')):
  names={'mixed_reference':'mixed-v2/reference-two-player','mixed_kids':'mixed-v2/kids-four-player','secret_eb':'awards-v3/secret-nine-multiball-collect',
   'special':'special-v1/casual-tunnel-outlane','casual_reference':'casual-v1/reference','casual_kids':'casual-v1/kids',
   'video_complete':'video-v11/steering-gradient-video-award','video_extra':'video-v12/video-extra-ball-collection'}
  contract=module('release_contracts').contract(names[spec['name']],r,rows,folder)
 else:contract=dict(contract=group,frames=frames)
 if group=='b6':contract.update(observation_only=True,probe_outcome=r['probe_outcome'],meaning=r['meaning'])
 if group!='pwm-unit':
  analysis=module('analyze_coil_trace').analyze(folder)
  (folder/'coil-analysis.json').write_text(json.dumps(analysis,indent=2)+'\n')
  if analysis['ramp_opposing_command_overlaps']['count']:raise AssertionError('Opposing ramp commands require review')
  contract['pulse_maxima_seconds']={key:value['longest_on_seconds'] for key,value in analysis['coils'].items() if value['category'] in ['pulse coil','flipper stroke'] and value['activations']}
  contract['coil_analysis']='Raw edge accounting and no opposing ramp overlap; output durations retained for explicit comparisons, not thermal limits'
 return contract
