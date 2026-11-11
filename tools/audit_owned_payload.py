#!/usr/bin/env python3
"""Optional owner-local ROM substring/carrier audit; no ROM bytes are printed.
Run the public tree scanner too. This is a payload check, not legal clearance.
"""
import argparse,hashlib,json,pathlib,re,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from kh5patch.core import convert,identity,gameplay_build
from lab.config import private_path,SOUND_SHA1

def windows(images):
 return {b for image in images for i in range(len(image)-95) if len(set(b:=image[i:i+96]))>=16}

def scan(name,data,blocks,reference_guard=None):
 if reference_guard and (reference_guard in data or reference_guard.hex().encode() in data.lower()):raise ValueError('Reference guard payload in '+name)
 for i in range(len(data)-95):
  if data[i:i+96] in blocks:raise ValueError('Nontrivial owner-ROM substring in '+name)
 # Also catch long directly encoded hex payloads, not only raw binary matches.
 for match in re.finditer(rb'(?<![A-Za-z0-9])[0-9A-Fa-f]{192,}(?![A-Za-z0-9])',data):
  decoded=bytes.fromhex(match[0].decode())
  for i in range(len(decoded)-95):
   if decoded[i:i+96] in blocks:raise ValueError('Encoded owner-ROM substring in '+name)

def audit(baseline,sound=None,l5c=None):
 base=pathlib.Path(baseline).read_bytes();target,_=convert(base);images=[base];guard=None
 if sound:
  data=pathlib.Path(sound).read_bytes()
  if hashlib.sha1(data).hexdigest()!=SOUND_SHA1:raise ValueError('U18 identity mismatch')
  images.append(data)
 if l5c:
  data=pathlib.Path(l5c).read_bytes()
  if hashlib.sha1(data).hexdigest()!='16e83bc01c452781150275a0e88a71072cf9bc43':raise ValueError('L5C reference identity mismatch')
  guard=data[0x2AF98:0x2AFB4]
 stage,_=gameplay_build(base);meta=json.loads((ROOT/'patches/release.json').read_text());patch=(ROOT/meta['patch_file']).read_bytes();pos=5;payload=0
 while patch[pos:pos+3]!=b'EOF':
  offset=int.from_bytes(patch[pos:pos+3],'big');size=int.from_bytes(patch[pos+3:pos+5],'big');pos+=5
  if not size or pos+size>len(patch):raise ValueError('Unexpected authored IPS record')
  for address,value in enumerate(patch[pos:pos+size],offset):
   if base[address]==value or stage[address]!=value:raise ValueError('IPS carrier/source mismatch')
   if 0x7DCF5<=address<0x7DD5C or address>=0x7FFEC:raise ValueError('Native LED/checksum payload in authored IPS')
  payload+=size;pos+=size
 if pos+3!=len(patch):raise ValueError('Unexpected IPS trailer')
 blocks=windows(images);files=(ROOT/'PUBLIC_FILES.txt').read_text().splitlines();total=0
 for name in files:
  data=(ROOT/name).read_bytes();scan(name,data,blocks,guard);total+=len(data)
 return dict(result='PASS',baseline=identity(base),target=identity(target),public_files=len(files),public_bytes_scanned=total,
  authored_payload_bytes=payload,owner_sound_checked=bool(sound),owner_reference_guard_checked=bool(l5c),
  nontrivial_96_byte_ROM_matches=0,unchanged_IPS_carrier_bytes=0,
  limits=['Checks approved working-tree files; check_public_tree.py separately checks the staged boundary and reachable Git history',
          'Short interface/opcode constants and arbitrary encodings require source review; not legal clearance'])

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=pathlib.Path,required=True);p.add_argument('--sound',type=pathlib.Path);p.add_argument('--l5c',type=pathlib.Path);p.add_argument('--output',type=pathlib.Path);a=p.parse_args()
 if a.output:
  private_path(a.output)
  if a.output.exists():p.error('Refusing to overwrite an audit report')
 x=audit(a.baseline,a.sound,a.l5c)
 if a.output:
  with a.output.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
 print(json.dumps(x,indent=2))
if __name__=='__main__':main()
