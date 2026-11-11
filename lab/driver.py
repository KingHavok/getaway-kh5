"""Register exact candidate metadata in an owned pinned emulator source tree."""
import hashlib,json,subprocess
from pathlib import Path
from .config import REPO,verify_image
BEGIN='/* BEGIN KH5 LOCAL CANDIDATE */';END='/* END KH5 LOCAL CANDIDATE */'

def ensure(project,name):
 entry,_=verify_image(project,name)
 if entry['driver']!='gw_lab':return
 source=Path(project['source']) if project.get('source') else None
 if source is None or not (source/'.getaway-lab-source.json').is_file():raise ValueError('Build an owned lab emulator first with lab.py build')
 marker=json.loads((source/'.getaway-lab-source.json').read_text())
 if marker['pin']!='47ac466023e488e1cbeb19448fa3f56ff9cc8788':raise ValueError('Unrecognized emulator source pin')
 identity=entry['identity'];gw=source/'src/wpc/sims/wpc/full/gw.c';registry=source/'src/wpc/driver.c'
 block=(BEGIN+'\n'+f'WPC_ROMSTART(gw,lab,"getaw_lab.rom",0x80000,CRC({identity["crc32"]}) SHA1({identity["sha1"]}))\n'
  'WPCS_SOUNDROM8xx("u18snd",CRC(37bbe485) SHA1(e6b7ccef250db0c801e3dd8ebf93522b466ca1ec))\nWPC_ROMEND\n'
  'CORE_CLONEDEF(gw,lab,l5,"Getaway local development candidate",2026,"Local research",wpc_mFliptronS,0)\n'+END+'\n')
 text=gw.read_text()
 if BEGIN in text:
  start=text.index(BEGIN);end=text.index(END,start)+len(END);text=text[:start]+text[end:].lstrip('\n')
 new=text.rstrip()+'\n\n'+block
 driver=registry.read_text()
 if 'DRIVER(gw,lab)' not in driver:
  if 'DRIVER(gw,kh5)' not in driver:raise ValueError('Expected public KH5 driver registry anchor')
  driver=driver.replace('DRIVER(gw,kh5)','DRIVER(gw,lab) // owner-local exact candidate metadata\nDRIVER(gw,kh5)',1)
 stamp=source/'.getaway-lab-candidate.json'
 if stamp.exists() and json.loads(stamp.read_text()).get('identity')==identity and new==gw.read_text() and driver==registry.read_text():return
 gw.write_text(new);registry.write_text(driver)
 with (Path(project['workspace'])/'candidate-emulator-build.log').open('w') as log:
  subprocess.run(['cmake','--build',str(source/'build'),'--parallel','2'],stdout=log,stderr=subprocess.STDOUT,check=True)
 stamp.write_text(json.dumps(dict(identity=identity),indent=2)+'\n')

def check_log(path):
 """Ordinary runs must not silently accept PinMAME catalogue mismatch warnings."""
 text=Path(path).read_text(errors='replace').upper()
 if 'WRONG CHECKSUM' in text or 'WRONG LENGTH' in text:
  raise AssertionError('PinMAME reported a ROM catalogue identity/length mismatch; not a qualified ordinary run')
 return 'No catalogue checksum/length warning'
