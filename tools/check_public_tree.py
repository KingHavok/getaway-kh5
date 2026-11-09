#!/usr/bin/env python3
"""Enforce the explicit public file boundary; inspect reachable Git blobs too."""
import csv,hashlib,json,pathlib,re,subprocess,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from kh5patch.core import gameplay_build, make_ips
ROOT=pathlib.Path(__file__).resolve().parents[1]
FORBIDDEN={'.bin','.rom','.u6','.u18','.nv','.cfg','.zip','.7z','.raw','.jsonl','.pgm','.ppm','.png','.jpg','.jpeg','.gif','.mp4','.mp3','.wav','.dmd','.pdf','.exe','.so','.dylib','.dll','.pyc'}
BAD_KEYS={'ram','stack','data_hex','rom_bytes','nvram_data','full_memory'}

def inspect(name,data):
 path=pathlib.PurePosixPath(name)
 if path.suffix.lower() in FORBIDDEN or any(part in ['private','outputs','runtime','vendor','__pycache__'] for part in path.parts):raise ValueError('Forbidden public artifact: '+name)
 if len(data)>2_000_000:raise ValueError('Unexpectedly large public file: '+name)
 if any(x in data for x in [b'/'+b'Users/',b'/'+b'home/',b'gh'+b'p_',b'gh'+b'o_',b'github'+b'_pat_',b'-----BEGIN '+b'PRIVATE KEY-----']):raise ValueError('Private path or credential pattern: '+name)
 if path.suffix=='.ips':
  if not data.startswith(b'PATCH') or not data.endswith(b'EOF') or len(data)>4096:raise ValueError('Unexpected IPS container: '+name)
  return
 try:text=data.decode('utf-8')
 except UnicodeDecodeError:raise ValueError('Unreviewed binary file: '+name)
 if path.suffix=='.csv':
  columns=next(csv.reader(text.splitlines()))
  if any(c.lower() in ['before','before_hex','original','original_bytes'] for c in columns):raise ValueError('Baseline byte log must remain private')
 if path.suffix=='.json':
  def walk(x):
   if isinstance(x,dict):
    if BAD_KEYS.intersection(x):raise ValueError('Raw debugger payload key: '+name)
    for v in x.values():walk(v)
   elif isinstance(x,list):
    for v in x:walk(v)
  walk(json.loads(text))
 if re.search(r'(?<![a-zA-Z0-9])[a-fA-F0-9]{96,}(?![a-zA-Z0-9])',text):raise ValueError('Opaque long hex payload needs review: '+name)

def main():
 allowed=set((ROOT/'PUBLIC_FILES.txt').read_text().splitlines());actual={str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.relative_to(ROOT).parts and '__pycache__' not in p.relative_to(ROOT).parts}
 if actual!=allowed:raise ValueError('Allowlist mismatch: added='+str(sorted(actual-allowed))+' missing='+str(sorted(allowed-actual)))
 for name in sorted(allowed):
  p=ROOT/name
  if p.is_symlink():raise ValueError('Symlinks are not a public payload')
  inspect(name,p.read_bytes())
 # Reconstruct the authored stage without a game: FF holes plus explicit edits.
 # Comparing a sparse synthetic image proves there is no extra IPS payload.
 metadata=json.loads((ROOT/'patches/release.json').read_text())
 patch=(ROOT/metadata['patch_file']).read_bytes()
 sentinel=bytearray(b'\xff'*metadata['baseline']['bytes'])
 # Source edits sometimes retain padding. For this boundary check compare every
 # IPS byte with source-emitted bytes, rather than treating sentinels as L5.
 authored,regions=gameplay_build(bytes(sentinel));pos=5;count=0
 while patch[pos:pos+3]!=b'EOF':
  off=int.from_bytes(patch[pos:pos+3],'big');n=int.from_bytes(patch[pos+3:pos+5],'big');pos+=5
  if not n or off+n>len(authored):raise ValueError('Unexpected stage IPS record')
  for index,value in enumerate(patch[pos:pos+n],off):
   if not any(start<=index<end for start,end,name in regions):raise ValueError('IPS payload outside authored source')
   if 0x7DCF5<=index<0x7DD5C or index>=0x7FFEC:raise ValueError('Native driver/checksum payload in public IPS')
   if authored[index]!=value:raise ValueError('IPS payload differs from authored source')
  pos+=n;count+=n
 if pos+3!=len(patch) or count!=metadata['patch_changed_bytes']:raise ValueError('Stage IPS size mismatch')
 if hashlib.sha256(patch).hexdigest()!=metadata['patch_sha256']:raise ValueError('Stage IPS digest mismatch')
 objects=0
 if (ROOT/'.git').exists():
  staged=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
  if set(filter(None,staged))!=allowed:raise ValueError('Git index differs from the reviewed allowlist')
  history=subprocess.run(['git','rev-list','--objects','--all'],cwd=ROOT,capture_output=True,text=True)
  if history.returncode==0:
   for line in history.stdout.splitlines():
    fields=line.split(' ',1)
    if len(fields)!=2:continue
    oid,name=fields
    kind=subprocess.check_output(['git','cat-file','-t',oid],cwd=ROOT,text=True).strip()
    if kind!='blob':continue
    inspect(name,subprocess.check_output(['git','cat-file','blob',oid],cwd=ROOT));objects+=1
 print(json.dumps(dict(result='PASS',public_files=len(allowed),reachable_blobs_checked=objects,roms_or_assets_distributed=False)))
if __name__=='__main__':main()
