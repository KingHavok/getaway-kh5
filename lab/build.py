"""Build reviewed source into private candidates without changing release pins."""
import csv,json
from pathlib import Path
from kh5patch.core import gameplay_build,checksum,identity,make_ips
from kh5patch.led import transform
from .config import REPO,verify_image,candidate,sha,private_path

def build_candidate(project,output,name='candidate',revision=5,patch_dir=None):
 if not 0<=revision<=255:raise ValueError('Revision byte must be 0..255')
 _,base=verify_image(project,'l5');output=private_path(output)
 artifacts=[output,output.with_suffix(output.suffix+'.gameplay.ips'),output.with_suffix(output.suffix+'.build.json'),output.with_suffix(output.suffix+'.changes.csv')]
 if any(p.exists() for p in artifacts):raise ValueError('Refusing to overwrite candidate artifacts')
 stage,regions=gameplay_build(base,patch_dir);image=checksum(transform(stage),revision)
 output.parent.mkdir(parents=True,exist_ok=True)
 with output.open('xb') as f:f.write(image)
 with artifacts[-1].open('x',newline='') as log:
  writer=csv.writer(log);writer.writerow(['file_offset','before','after','reason'])
  for index,(before,after) in enumerate(zip(base,image)):
   if before!=after:
    reason=next((name for start,end,name in regions if start<=index<end),'OWNER_LOCAL_LED_OR_CHECKSUM')
    writer.writerow([f'{index:05X}',f'{before:02X}',f'{after:02X}',reason])
 # The stage contains authored edits only, with no relocated LED instructions.
 ips=output.with_suffix(output.suffix+'.gameplay.ips')
 with ips.open('xb') as f:f.write(make_ips(base,stage))
 report=dict(kind='UNQUALIFIED development candidate',identity=identity(image),revision_byte=revision,
  source_sha256={str(p):sha(p) for p in [Path(patch_dir or REPO/'patches')/'kh5.asm',Path(patch_dir or REPO/'patches')/'edits.json',REPO/'kh5patch/assembler.py',REPO/'kh5patch/core.py',REPO/'kh5patch/led.py']},
  changed_bytes=sum(a!=b for a,b in zip(base,image)),gameplay_patch=str(ips),LED='owner-local V2 transformation',qualified=False)
 output.with_suffix(output.suffix+'.build.json').write_text(json.dumps(report,indent=2)+'\n')
 candidate(project,output,name);return report
