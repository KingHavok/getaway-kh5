"""Run release inputs on official L5, KH5 or an explicitly registered candidate."""
import json,hashlib
from pathlib import Path
from . import runtime
from .config import REPO,private_path,verify_image
import sys
sys.path.insert(0,str(REPO/'tools'))
from replay import API as BinaryAPI,observation

def actions(api,script,folder,observe=False,observer=observation,events=None):
 observations=[];differences=[];saved=[];assertions=0
 for index,action in enumerate(json.loads(Path(script).read_text())):
  if 'frames' in action:
   api.frames(action['frames']);continue
  if 'assert_memory' in action:
   spec=action['assert_memory'];kwargs=dict(addr=spec['addr'],size=len(spec['data']))
   if 'bank' in spec:kwargs['bank']=spec['bank']
   actual=api.call('debugger/memory',**kwargs)['data'];assertions+=1
   if actual!=spec['data']:
    differences.append(dict(action=index,kind='memory assertion',address=spec['addr'],expected=spec['data'],actual=actual))
    if not observe:raise AssertionError('State assertion at '+spec['addr'])
   continue
  path=action['path']
  if not path.startswith('/api/'):raise ValueError('Only local emulator API routes are allowed')
  path=path[5:];params=action.get('params',{})
  if path in ['dmd/pnm','screenshot/pnm','debugger/dmdrec/data']:
   raw=BinaryAPI(api.port).raw(path,**params);data=dict(private_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
  else:
   data=api.call(path,**params);raw=json.dumps(data).encode()
  if 'save' in action:
   dest=folder/'captures'/(f'{index:04d}'+Path(action['save']).suffix)
   dest.parent.mkdir(exist_ok=True);dest.write_bytes(raw);saved.append(dict(action=index,route=path,path=str(dest)))
  if events is not None:events.append(dict(index=index,action=action,response=data))
  item=observer(action,data)
  if item:observations.append(item)
 (folder/'observations.json').write_text(json.dumps(observations,indent=2)+'\n')
 (folder/'captures.json').write_text(json.dumps(saved,indent=2)+'\n')
 return observations,differences,assertions,saved

def run(project,name,case_name,output,port,observe=False,script=None,expected=None):
 entry,_=verify_image(project,name);output=private_path(output);output.mkdir(parents=True,exist_ok=False)
 runtime.configure_project(project,name);runtime.prepare(name,port)
 public=json.loads((REPO/'tests/oracles.json').read_text());rows=[]
 cases=([dict(name='custom',script=str(Path(script).resolve()))] if script else
  [x for x in json.loads((REPO/'tests/scenarios.json').read_text()) if case_name=='all' or x['name']==case_name])
 if not cases:raise ValueError('Unknown release scenario')
 observed_mode=observe or entry['kind']=='official'
 for case in cases:
  folder=output/case['name'];path=Path(case['script']);path=path if path.is_absolute() else REPO/path
  try:
   with runtime.session(folder,port,__file__) as (api,record):
    seen,diffs,assertions,saved=actions(api,path,folder,observed_mode)
    oracle=json.loads(Path(expected).read_text()) if expected else public.get(case['name'])
    if oracle is not None:
     if oracle!=seen:
      diffs.append(dict(kind='scalar/count oracle',expected_records=len(oracle),actual_records=len(seen)))
      if not observed_mode:raise AssertionError('Release scalar/count oracle mismatch; retain captures, do not update expected values automatically')
    elif not assertions and not observed_mode:observed_mode=True
    visual=None
    if case['name']=='core_a1_cold' and not observed_mode:
     from .visual import red_light
     visual=red_light(saved)
    record.update(result='OBSERVED' if observed_mode else 'PASS',visual=visual,script_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
      qualification='OBSERVATION ONLY' if observed_mode else 'Release assertions and scalar/count oracle',
      assertion_count=assertions,oracle_checked=oracle is not None,differences=diffs)
   from .driver import check_log
   check_log(folder/'runtime/PRIVATE-emulator.log')
   row=dict(case=case['name'],result='OBSERVED' if observed_mode else 'PASS',frames=record['frames'],differences=diffs,image=entry['identity'])
  except Exception as error:
   row=dict(case=case['name'],result='FLAGGED',error=str(error),image=entry['identity'])
  rows.append(row);print(case['name']+': '+row['result'],flush=True)
 result=dict(result='FLAGGED' if any(x['result']=='FLAGGED' for x in rows) else 'OBSERVED' if observed_mode else 'PASS',image=entry['identity'],cases=rows,
  scope='Fresh image-bound sessions; official L5 observations are not passes of KH5 assertions; raw output stays private')
 (output/'summary.json').write_text(json.dumps(result,indent=2)+'\n');return result
