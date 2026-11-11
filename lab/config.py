"""Explicit owner-local image identities; no implicit acceptance of changed files."""
import hashlib,json,re
from pathlib import Path
from kh5patch.core import identity,convert
REPO=Path(__file__).resolve().parents[1]
SOUND_SHA1='e6b7ccef250db0c801e3dd8ebf93522b466ca1ec'

def release():return json.loads((REPO/'patches/release.json').read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def private_path(path):
 p=Path(path).resolve()
 if p==REPO or p.is_relative_to(REPO):raise ValueError('Private workspace must be outside the public repository')
 return p

def image_entry(path,driver,filename,kind):
 p=Path(path).resolve();data=p.read_bytes();meta=identity(data)
 if len(data)!=524288:raise ValueError('Expected a 512 KiB raw U6 image')
 if int.from_bytes(data[-18:-16],'big')!=sum(data)&65535:raise ValueError('Native stored checksum does not match byte sum')
 return dict(path=str(p),driver=driver,filename=filename,kind=kind,identity=meta,layout='l5')

def save(project):
 p=Path(project['workspace'])/'project.json';temp=p.with_suffix('.json.tmp');temp.write_text(json.dumps(project,indent=2)+'\n');temp.replace(p);return p

def load(path):
 p=Path(path).resolve();p=p/'project.json' if p.is_dir() else p
 x=json.loads(p.read_text());private_path(x['workspace'])
 if x.get('format')!=1 or p!=Path(x['workspace'])/'project.json':raise ValueError('Unsupported or relocated project manifest')
 return x

def verify_image(project,name):
 if name not in project['images']:raise ValueError('Image not registered: '+name)
 entry=project['images'][name]
 expected={'official':('gw_l5','getaw_l5.rom'),'release':('gw_kh5','getaw_kh5.rom'),'candidate':('gw_lab','getaw_lab.rom')}
 if entry.get('kind') not in expected or (entry.get('driver'),entry.get('filename'))!=expected[entry['kind']]:raise ValueError('Unrecognized image driver/filename declaration')
 if (name=='l5' and entry['kind']!='official') or (name=='kh5' and entry['kind']!='release'):raise ValueError('Reserved release/baseline name changed')
 data=Path(entry['path']).read_bytes()
 if identity(data)!=entry['identity']:raise ValueError('Registered image changed; explicitly register a new candidate identity')
 if entry['kind']=='official' and entry['identity']!=release()['baseline']:raise ValueError('Official baseline identity changed')
 if entry['kind']=='release' and entry['identity']!=release()['target']:raise ValueError('Published KH5 identity changed')
 if entry.get('layout')!='l5':raise ValueError('No test layout adapter for this image')
 return entry,data

def sound(project):
 p=Path(project['sound']) if project.get('sound') else None
 if p is None:raise ValueError('Supply your own matching U18 with lab.py sound before emulator tests')
 data=p.read_bytes()
 if hashlib.sha1(data).hexdigest()!=SOUND_SHA1:raise ValueError('U18 identity mismatch')
 return data

def initialize(workspace,baseline,sound_path=None):
 workspace=private_path(workspace);base=Path(baseline).read_bytes();kh5,_=convert(base)
 if sound_path and hashlib.sha1(Path(sound_path).read_bytes()).hexdigest()!=SOUND_SHA1:raise ValueError('Matching production U18 required')
 workspace.mkdir(parents=True,exist_ok=False);inputs=workspace/'inputs';inputs.mkdir()
 (inputs/'l5.u6').write_bytes(base);(inputs/'kh5.u6').write_bytes(kh5)
 x=dict(format=1,workspace=str(workspace),sound=None,images={
  'l5':image_entry(inputs/'l5.u6','gw_l5','getaw_l5.rom','official'),
  'kh5':image_entry(inputs/'kh5.u6','gw_kh5','getaw_kh5.rom','release')},emulator=None,source=None)
 if sound_path:(inputs/'u18snd').write_bytes(Path(sound_path).read_bytes());x['sound']=str(inputs/'u18snd')
 save(x);return x

def candidate(project,path,name='candidate'):
 if not re.fullmatch(r'[a-z][a-z0-9_-]{0,31}',name) or name in ['l5','kh5']:raise ValueError('Choose a new candidate name, not l5 or kh5')
 entry=image_entry(private_path(path),'gw_lab','getaw_lab.rom','candidate');project['images'][name]=entry;save(project);return entry
