#!/usr/bin/env python3
"""Create an owner-local lab, rebuild KH5, register candidates and run tests."""
import argparse,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'research'))
from lab import config,runtime

def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
 init=sub.add_parser('init');init.add_argument('--workspace',type=Path,required=True);init.add_argument('--baseline',type=Path,required=True);init.add_argument('--sound',type=Path)
 for name in ['build','sound','candidate','build-candidate','plan','run','replay','status']:
  child=sub.add_parser(name);child.add_argument('--project',type=Path,required=True)
  if name=='build':child.add_argument('--local-source',type=Path);child.add_argument('--jobs',type=int,default=2)
  elif name=='sound':child.add_argument('--file',type=Path,required=True)
  elif name=='candidate':child.add_argument('--rom',type=Path,required=True);child.add_argument('--name',default='candidate')
  elif name=='build-candidate':child.add_argument('--output',type=Path,required=True);child.add_argument('--name',default='candidate');child.add_argument('--revision',type=int,default=5);child.add_argument('--patch-dir',type=Path)
  elif name in ['plan','run']:
   child.add_argument('--suite',default='historical');child.add_argument('--image',default='kh5');child.add_argument('--case');child.add_argument('--limit',type=int);child.add_argument('--work',type=Path);child.add_argument('--output',type=Path,required=True)
   if name=='run':child.add_argument('--port',type=int,default=9070)
  elif name=='replay':
   child.add_argument('--image',default='kh5');child.add_argument('--case',default='all');child.add_argument('--output',type=Path,required=True);child.add_argument('--port',type=int,default=9070);child.add_argument('--observe',action='store_true');child.add_argument('--script',type=Path);child.add_argument('--expect',type=Path);child.add_argument('--ledger',type=Path)
 a=p.parse_args();lease=None
 try:
  if a.command=='init':
   x=config.initialize(a.workspace,a.baseline,a.sound);print(json.dumps(dict(project=str(Path(x['workspace'])/'project.json'),images={k:v['identity'] for k,v in x['images'].items()},sound_supplied=bool(x['sound'])),indent=2));return
  x=config.load(a.project)
  if a.command in ['build','sound','candidate','build-candidate','run','replay']:
   from lab.locking import acquire
   lease=acquire(x)
  if a.command=='build':
   source=Path(x['workspace'])/'emulator'
   if not source.exists():
    command=[sys.executable,str(ROOT/'tools/build_pinmame.py'),str(source),'--jobs',str(a.jobs)]
    if a.local_source:command+=['--local-source',str(a.local_source.resolve())]
    subprocess.run(command,check=True)
   else:
    if not (source/'.getaway-lab-source.json').exists():raise ValueError('Existing source is not an owned lab build')
    subprocess.run(['cmake','--build',str(source/'build'),'--parallel',str(a.jobs)],check=True)
   x.update(source=str(source),emulator=str(source/'build/sdl3pinmame'));config.save(x);print(x['emulator'])
  elif a.command=='sound':
   import hashlib
   data=a.file.read_bytes()
   if hashlib.sha1(data).hexdigest()!=config.SOUND_SHA1:raise ValueError('U18 identity mismatch')
   target=Path(x['workspace'])/'inputs/u18snd'
   if target.exists() and target.read_bytes()!=data:raise ValueError('Existing sound input differs')
   target.write_bytes(data);x['sound']=str(target);config.save(x);print('Matching owner-supplied U18 registered')
  elif a.command=='candidate':print(json.dumps(config.candidate(x,a.rom,a.name),indent=2))
  elif a.command=='build-candidate':
   from lab.build import build_candidate
   print(json.dumps(build_candidate(x,a.output,a.name,a.revision,a.patch_dir),indent=2))
  elif a.command=='status':
   for name in x['images']:config.verify_image(x,name)
   print(json.dumps(x,indent=2))
  else:
   runtime.configure_project(x,a.image)
   if a.command=='replay':
    from lab.replay import run
    if a.ledger:
     from lab.ledger import run as ledger_run
     result=ledger_run(x,a.image,a.ledger,a.output,a.port)
    else:result=run(x,a.image,a.case,a.output,a.port,a.observe,a.script,a.expect)
   else:
    from lab.campaign import plan,run
    work=json.loads(a.work.read_text())['cases'] if a.work else plan(a.suite,a.image,a.case,a.limit)
    if a.command=='plan':
     config.private_path(a.output);a.output.parent.mkdir(parents=True,exist_ok=True)
     with a.output.open('x') as f:json.dump(dict(suite=a.suite,image=a.image,cases=work),f,indent=2)
     print(f'{len(work)} cases planned; no emulator started');return
    result=run(x,work,a.output,a.port)
   print(json.dumps(result,indent=2));return 0 if result['result'] in ['PASS','OBSERVED'] else 1
 except (ValueError,OSError,KeyError,AssertionError,subprocess.CalledProcessError) as error:
  p.exit(1,f'Lab stopped: {error}\n')
 finally:
  if lease is not None:lease.close()
if __name__=='__main__':sys.exit(main())
