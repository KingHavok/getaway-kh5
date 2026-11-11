"""ROM-free checks for development boundaries and the portable catalogues."""
import copy,importlib,json,os,pathlib,subprocess,sys,tempfile,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'research')]
from kh5patch.core import checksum,identity,gameplay_build
from kh5patch.assembler import assemble
from lab import config,campaign,variants
from lab.compare import compare

class LabTests(unittest.TestCase):
 def test_catalogue_counts_and_roles(self):
  expected={'historical':913,'devices':74,'donut':56,'endurance':60,'multiball':723,'shared':80,'remaining':643,'features':12,'ordinary':80,'settings':23,'variants':128,'b6':22,'entry-faults':4,'active-traps':2,'shared-casual':12,'replay-awards':2}
  for name,count in expected.items():
   rows=campaign.plan(name,'new');self.assertEqual(len(rows),count,name);self.assertEqual(len({r['id'] for r in rows}),count)
  rows=campaign.plan('historical','new');self.assertTrue(any(r['image']=='l5' for r in rows));self.assertTrue(any(r['image']=='new' for r in rows));self.assertTrue(all(r['image'] in ['l5','new'] for r in rows))
 def test_native_persistence_plan_has_menu_dependency(self):
  self.assertEqual([r['id'] for r in campaign.plan('features',case='persist_kids')],['menu_kids','persist_kids'])
 def test_every_variant_generates_without_rom(self):
  for row in variants.design('new'):
   actions,n=variants.generate(row['specification']);self.assertGreater(n,0)
   for action in actions:
    if 'assert_memory' in action:self.assertLessEqual(len(action['assert_memory']['data']),8)
    if 'save' in action:
     self.assertFalse(pathlib.PurePosixPath(action['save']).is_absolute());self.assertNotIn('..',pathlib.PurePosixPath(action['save']).parts)
 def test_research_imports_without_private_project(self):
  for file in sorted((ROOT/'research').glob('*.py')):importlib.import_module(file.stem)
 def test_candidate_identity_pinned_and_driver_not_editable(self):
  with tempfile.TemporaryDirectory() as d:
   path=pathlib.Path(d)/'candidate';path.write_bytes(checksum(b'\0'*524288))
   entry=config.image_entry(path,'gw_lab','getaw_lab.rom','candidate');project={'images':{'test':entry}}
   self.assertEqual(config.verify_image(project,'test')[1],path.read_bytes())
   entry['driver']='gw_kh5'
   with self.assertRaises(ValueError):config.verify_image(project,'test')
   entry['driver']='gw_lab';data=bytearray(path.read_bytes());data[0]^=1;path.write_bytes(data)
   with self.assertRaises(ValueError):config.verify_image(project,'test')
 def test_missing_sound_is_required_for_native_tests(self):
  with self.assertRaisesRegex(ValueError,'U18'):config.sound({})
 def test_public_workspace_and_bad_checksum_refused(self):
  with self.assertRaises(ValueError):config.private_path(ROOT/'private')
  with tempfile.TemporaryDirectory() as d:
   f=pathlib.Path(d)/'bad';f.write_bytes(b'\xff'*524288)
   with self.assertRaises(ValueError):config.image_entry(f,'gw_lab','getaw_lab.rom','candidate')
 def test_future_assembly_operand_modes_and_boundaries(self):
  with tempfile.TemporaryDirectory() as d:
   f=pathlib.Path(d)/'a.asm';f.write_text('.org $7000\nLDA #$12\nLDA $1234\nLDX #$1234\nLDX $1234\nLDD #$1234\nLDD $1234\n')
   self.assertEqual(assemble(f)[0][0][1],bytes.fromhex('8612B612348E1234BE1234CC1234FC1234'))
   for code in ['.org $8000\nNOP','.org $7FFF\nJSR $8000','.org $7000\nSTA #$12']:
    f.write_text(code)
    with self.assertRaises(ValueError):assemble(f)
 def test_external_patch_rejects_overlap_and_negative_offset(self):
  with tempfile.TemporaryDirectory() as d:
   d=pathlib.Path(d);(d/'kh5.asm').write_text('.org $7000\nRTS\n')
   for off in ['2B000','-1']:
    (d/'edits.json').write_text(json.dumps({'edits':[{'id':'new','offset':off,'after':'12'}]}))
    with self.assertRaises(ValueError):gameplay_build(b'\xff'*524288,d)
 def test_public_audit_checks_actual_staged_bytes(self):
  import importlib.util
  spec=importlib.util.spec_from_file_location('public_boundary',ROOT/'tools/check_public_tree.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  with tempfile.TemporaryDirectory() as d:
   d=pathlib.Path(d);subprocess.run(['git','init','-q'],cwd=d,check=True)
   f=d/'public.txt';f.write_text('reviewed text\n');subprocess.run(['git','add','public.txt'],cwd=d,check=True)
   module.check_index(d,{'public.txt'})
   f.write_text('different working text\n')
   with self.assertRaisesRegex(ValueError,'Staged content differs'):module.check_index(d,{'public.txt'})
 def test_owned_payload_audit_rejects_raw_and_encoded_native_blocks(self):
  import importlib.util
  spec=importlib.util.spec_from_file_location('owned_audit',ROOT/'tools/audit_owned_payload.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  synthetic=bytes(range(32))*3;blocks=module.windows([synthetic])
  for data in [b'prefix '+synthetic,b'prefix '+synthetic.hex().encode()]:
   with self.assertRaises(ValueError):module.scan('synthetic',data,blocks)
  module.scan('synthetic',b'authored source without a native payload',blocks)
 def test_catalogue_warnings_never_qualify_as_ordinary_runs(self):
  from lab.driver import check_log
  with tempfile.TemporaryDirectory() as d:
   f=pathlib.Path(d)/'emulator.log';f.write_text('loading rom 0: getaw_lab.rom\nwarning: no mixer plugins available\ndone\n')
   check_log(f)
   for warning in ['getaw_lab.rom WRONG CHECKSUMS:', 'getaw_lab.rom WRONG LENGTH:']:
    f.write_text(warning)
    with self.assertRaises(AssertionError):check_log(f)
 def test_frame_and_ram_mutation_boundaries(self):
  from lab.api import API
  import io
  api=API(1,io.StringIO())
  for path,params in [('debugger/state/write',{}),('debugger/control',{'cmd':'resume'}),('debugger/memory/write',{'addr':'0805','data':'01'})]:
   with self.assertRaises(ValueError):api.call(path,**params)
 def test_binary_captures_do_not_decode_as_json(self):
  from lab.replay import actions
  from lab.api import API
  import io
  with tempfile.TemporaryDirectory() as d:
   d=pathlib.Path(d);script=d/'script';script.write_text(json.dumps([{'path':'/api/dmd/pnm','save':'test.pgm'}]))
   with patch('lab.replay.BinaryAPI.raw',return_value=b'P5\xff\0'):
    _,_,_,saved=actions(API(1,io.StringIO()),script,d)
   self.assertEqual(pathlib.Path(saved[0]['path']).read_bytes(),b'P5\xff\0')
 @unittest.skipUnless(os.environ.get('KH5_BASELINE'),'No proprietary ROM provided to public tests')
 def test_owned_candidate_rebuild_and_output_preservation(self):
  from lab.build import build_candidate
  with tempfile.TemporaryDirectory() as d:
   d=pathlib.Path(d);base=pathlib.Path(os.environ['KH5_BASELINE']);original=base.read_bytes()
   project={'workspace':str(d),'images':{'l5':config.image_entry(base,'gw_l5','getaw_l5.rom','official')}}
   output=d/'candidate.bin';report=build_candidate(project,output)
   self.assertEqual(report['identity'],config.release()['target']);self.assertFalse(report['qualified'])
   self.assertEqual(config.verify_image(project,'candidate')[1],output.read_bytes())
   self.assertTrue(output.with_suffix('.bin.gameplay.ips').exists());self.assertTrue(output.with_suffix('.bin.changes.csv').exists())
   with self.assertRaises(ValueError):build_candidate(project,output)
   self.assertEqual(base.read_bytes(),original);self.assertEqual(identity(output.read_bytes()),config.release()['target'])
 def test_pulse_comparison_rejects_missing_failed_and_changed_contracts(self):
  with tempfile.TemporaryDirectory() as d:
   a,b=[pathlib.Path(d)/n for n in ['a','b']]
   row={'id':'case','group':'test','specification':{'seconds':30},'result':'PASS','image':{'sha256':'synthetic'},'audit':{'pulse_maxima_seconds':{'1':.03}}}
   def run(other):
    a.write_text(json.dumps({'result':'PASS','planned':1,'cases':[row]}));b.write_text(json.dumps({'result':'PASS','planned':len(other),'cases':other}));return compare(a,b)
   self.assertEqual(run([row])['result'],'PASS')
   self.assertEqual(run([])['result'],'FLAGGED')
   run([row]);partial=json.loads(b.read_text());partial['result']='INCOMPLETE';partial['planned']=2;b.write_text(json.dumps(partial));self.assertEqual(compare(a,b)['result'],'FLAGGED')
   for change in [{'result':'FLAGGED'},{'specification':{'seconds':60}},{'audit':{'pulse_maxima_seconds':{}}},{'audit':{'pulse_maxima_seconds':{'1':.04}}}]:
    bad=copy.deepcopy(row);bad.update(change);self.assertEqual(run([bad])['result'],'FLAGGED')
   with self.assertRaises(ValueError):compare(a,b,float('nan'))

if __name__=='__main__':unittest.main()
