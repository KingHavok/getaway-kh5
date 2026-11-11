"""Verify word order using pixel-mask hashes; no fonts or artwork are bundled."""
import collections,hashlib,json,struct
from pathlib import Path
from .config import REPO

def red_light(saved):
 patterns=json.loads((REPO/'research/word-patterns.json').read_text())['patterns'];attempts=[]
 for capture in saved:
  if capture['route']!='debugger/dmdrec/data':continue
  data=Path(capture['path']).read_bytes()
  if len(data)<12:continue
  count,width,height=struct.unpack_from('<III',data)
  if (width,height)!=(128,32) or len(data)!=12+count*(4+width*height):continue
  hashes=[]
  for index in range(count):
   frame=data[16+index*(4+width*height):12+(index+1)*(4+width*height)]
   background=collections.Counter(frame).most_common(1)[0][0]
   hashes.append(hashlib.sha256(bytes(v!=background for v in frame)).hexdigest())
  previous=-1;matched=[]
  for pattern in patterns:
   candidates=[i for i in range(previous+1,len(hashes)) if hashes[i]==pattern['mask_sha256']]
   if not candidates:break
   previous=candidates[0];matched.append(dict(word=pattern['word'],frame=previous))
  if len(matched)==len(patterns):return dict(result='PASS',frames=count,ordered_words=matched)
  attempts.append(len(matched))
 raise AssertionError('Fresh recording lacks the complete ordered red-light sequence; matched word counts '+str(attempts))
