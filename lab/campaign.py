"""Deterministic campaign catalogues and serial, owned case execution."""
import importlib,json,hashlib,re,traceback
from pathlib import Path
from . import runtime
from .config import REPO,private_path,verify_image

def historical(target):
 source=json.loads((REPO/'evidence/historical-g6-cases.json').read_text());rows=[]
 for old in source['records']:
  spec=old['specification']
  group=('multiball' if 'mode' in spec else 'devices' if spec.get('kind') in ['mechanism','switch'] else 'donut' if 'scenario' in spec else 'endurance')
  rows.append(dict(id=f'historical-{old["id"]:04d}',group=group,specification=spec,
   image='l5' if old['game']=='gw_l5' else target,controller_role=old['game'],historical_case=old['case'],
   origin='Published historical specification; new execution is bound to the selected image, not historical evidence'))
 return rows

def plan(suite,target='kh5',case=None,limit=None):
 if suite in ['historical','devices','donut','endurance','multiball','shared','remaining']:
  rows=historical(target)
  if suite not in ['historical','shared','remaining']:rows=[r for r in rows if r['group']==suite]
  if suite in ['shared','remaining']:
   rows=[r for r in rows if r['group']=='multiball' and ((r['specification']['mode'],r['specification']['ending'])==('regular','drain'))==(suite=='shared')]
 elif suite=='shared-casual':rows=[dict(id=f'casual-p{p}-l{l}-x{int(x)}',group='multiball-casual',image=target,specification=dict(players=p,owner=1,recipient=2,locks=l,extended=x,mode='regular',ending='drain')) for p in [2,3,4] for l in [1,2] for x in [False,True]]
 elif suite=='replay-awards':rows=[dict(id='replay-'+name,group='replay-award',image=target,specification=dict(award=v)) for v,name in [(0,'credit-positive'),(3,'audit-no-award')]]
 elif suite=='features':
  names=['mixed_reference','mixed_kids','secret_eb','special','casual_reference','casual_kids','menu_kids','menu_reference','persist_kids','persist_reference','video_complete','video_extra']
  rows=[dict(id=n,group='feature',image=target,specification=dict(name=n,kids=n.endswith('kids'))) for n in names]
 elif suite=='ordinary':rows=[dict(id=f'ordinary-b{b}-p{p}-x{int(x)}',group='ordinary',image=target,specification=dict(balls=b,players=p,extended=x)) for b in range(1,11) for p in range(1,5) for x in [False,True]]
 elif suite=='soak':rows=[dict(id='continuous-40-games',group='soak',image=target,specification=dict(games=40))]
 elif suite=='search':rows=[dict(id=f'search-l{l}-s{s}',group='search',image=target,specification=dict(locks=l,stage=s)) for l in [0,1,2] for s in [1,3,5]]
 elif suite=='active-traps':rows=[dict(id='active-trap-'+mode,group='active-trap',image=target,specification=dict(mode=mode)) for mode in ['regular','redline']]
 elif suite=='entry-faults':rows=[dict(id=f'entry-{n}-{v}',group='entry-fault',image=target,specification=dict(kind='switch',id=n,value=v,phase='right-freeway',seconds=30,extended=True)) for n in [17,18] for v in [0,1]]
 elif suite=='donut-long':rows=[dict(id=n,group='donut-long',image=target,specification=dict(scenario=n)) for n in ['failed-lift-long','feedback-long-0','feedback-long-1']]
 elif suite=='flippers':rows=[dict(id=f'flipper-{f["name"]}-{v}',group='flipper',image=target,specification=dict(flipper=f,forced=v)) for f in importlib.import_module('flipper_fault_tests_v2').FLIPPERS for v in [-1,0,1]]
 elif suite in ['countdowns','settings']:
  if suite=='countdowns':rows=[dict(id=f'{mode}-{v}',group='countdown',image=target,specification=dict(mode=mode,value=v)) for mode in ['getaway','supercharger'] for v in [10,20,99]]
  else:
   data=json.loads((REPO/'research/settings-plan.json').read_text());rows=[dict(id=f'settings-{i:03d}',group='settings',image=target,specification=s) for i,s in enumerate(data)]
 elif suite=='b6':
  histories=['baseline','mb_grace','mb_expired','redline_after','redline_then_regular','regular_then_redline','multiplayer_regular','multiplayer_redline','mb_restart','redline_restart_after']
  rows=[dict(id='b6-'+n,group='b6',image=target,specification=dict(history=n,delay=0,casual=False)) for n in histories]
  rows += [dict(id=f'b6-boundary-{d}',group='b6',image=target,specification=dict(history='mb_grace',delay=d,casual=False)) for d in [900,1200,1260,1320,1380,1500]]
  rows += [dict(id='b6-casual-'+n,group='b6',image=target,specification=dict(history=n,delay=0,casual=True)) for n in ['baseline','mb_grace','mb_restart','redline_after']]
  rows += [dict(id='b6-'+n,group='b6',image=target,specification=dict(history=n,delay=0,casual=True)) for n in ['mb_no_probe_loop','mb_many_loops']]
 elif suite=='calibration':rows=[dict(id='known-waveform-and-sensors',group='calibration',image=target,specification={})]
 elif suite=='boot':rows=[dict(id='native-boot-checksum',group='boot',image=target,specification={})]
 elif suite=='pwm-unit':rows=[dict(id='atomic-stop-8192',group='pwm-unit',image=target,specification={})]
 elif suite=='variants':
  from .variants import design
  rows=design(target)
 else:raise ValueError('Unknown suite: '+suite)
 if case:
  requested={case}
  if case in ['persist_kids','persist_reference']:requested.add('menu_'+case.split('_',1)[1])
  rows=[r for r in rows if r['id'] in requested]
 if limit is not None:
  if limit<1:raise ValueError('Limit must be positive')
  rows=rows[:limit]
 if not rows:raise ValueError('No cases selected')
 return rows

def run(project,work,output,port):
 from .dispatch import execute,qualify
 output=private_path(output)
 if not isinstance(work,list) or not work:raise ValueError('An explicit nonempty case plan is required')
 allowed={'devices','donut','endurance','multiball','ordinary','soak','active-trap','entry-fault','search','donut-long','flipper','settings','countdown','b6','feature','boot','pwm-unit','variant','multiball-casual','replay-award','calibration'}
 for row in work:
  if row.get('group') not in allowed or not isinstance(row.get('specification'),dict):raise ValueError('Unsupported case declaration')
  verify_image(project,row['image'])
 ids=[r['id'] for r in work]
 if len(ids)!=len(set(ids)) or any(not re.fullmatch(r'[a-zA-Z0-9_-]+',n) for n in ids):raise ValueError('Case identifiers must be unique safe path components')
 output.mkdir(parents=True,exist_ok=False)
 (output/'plan.json').write_text(json.dumps(dict(cases=work),indent=2)+'\n');rows=[]
 for case in work:
  name=case['image'];entry,_=verify_image(project,name);runtime.prepare(name,port);folder=output/case['id']
  try:
   with runtime.select(name):execute(case,folder,port,output)
   audit=qualify(case,folder,project)
   row=dict(id=case['id'],group=case['group'],specification=case['specification'],result='OBSERVED' if audit.get('observation_only') else 'PASS',image=entry['identity'],image_name=name,audit=audit)
  except Exception as error:
   folder.mkdir(parents=True,exist_ok=True);(folder/'failure.txt').write_text(traceback.format_exc())
   row=dict(id=case['id'],group=case['group'],specification=case['specification'],result='FLAGGED',image=entry['identity'],image_name=name,error=str(error))
  rows.append(row);(folder/'qualification.json').write_text(json.dumps(row,indent=2)+'\n');print(case['id']+': '+row['result'],flush=True)
  (output/'summary.json').write_text(json.dumps(dict(result='INCOMPLETE',cases=rows,planned=len(work)),indent=2)+'\n')
 result=dict(result='FLAGGED' if any(r['result']=='FLAGGED' for r in rows) else 'OBSERVED' if any(r['result']=='OBSERVED' for r in rows) else 'PASS',cases=rows,planned=len(work),
  scope='New executions of published controller/specification ports; historical passes are not relabelled; no hardware certification')
 (output/'summary.json').write_text(json.dumps(result,indent=2)+'\n');return result
