import csv,hashlib,json,os,pathlib,subprocess,sys,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from kh5patch.core import apply_ips,make_ips,checksum,identity,convert,source_build
from kh5patch.assembler import assemble

class PublicTests(unittest.TestCase):
 def test_ips_roundtrip_and_only_changed_payload(self):
  base=bytes(range(256));target=bytearray(base);target[0]=19;target[50:53]=b'abc';target[-1]=0
  patch=make_ips(base,target);self.assertEqual(apply_ips(base,patch),target)
  self.assertEqual(len(patch),8+3*5+5)
 def test_ips_rejects_bad_header_and_truncation(self):
  for patch in [b'',b'PATCH',b'PATCH\x00\x00',b'PATCH\x00\x00\x00\x00\x02A']:
   with self.assertRaises(ValueError):apply_ips(b'\0'*8,patch)
 def test_ips_rejects_resize_trailing_and_overlap(self):
  for patch in [b'PATCHEOFx',b'PATCH\0\0\x08\0\1AEOF',b'PATCH\0\0\0\0\1A\0\0\0\0\1BEOF']:
   with self.assertRaises(ValueError):apply_ips(b'\0'*8,patch)
 def test_rle(self):
  self.assertEqual(apply_ips(b'0000',b'PATCH\0\0\1\0\0\0\2AEOF'),b'0AA0')
 def test_checksum_is_native_sum_with_revision_five(self):
  image=checksum(bytes(range(256))*2048)
  self.assertEqual(len(image),524288);self.assertEqual(sum(image)&65535,int.from_bytes(image[-18:-16],'big'));self.assertEqual(image[-17],5)
 def test_public_patch_identity_and_csv(self):
  meta=json.loads((ROOT/'patches/release.json').read_text());patch=(ROOT/meta['patch_file']).read_bytes()
  self.assertEqual(hashlib.sha256(patch).hexdigest(),meta['patch_sha256']);pos=5;changed={}
  while patch[pos:pos+3]!=b'EOF':
   address=int.from_bytes(patch[pos:pos+3],'big');count=int.from_bytes(patch[pos+3:pos+5],'big');self.assertGreater(count,0);pos+=5
   for n,value in enumerate(patch[pos:pos+count]):self.assertNotIn(address+n,changed);changed[address+n]=value
   pos+=count
  rows=list(csv.DictReader((ROOT/'patches/changed-bytes.csv').read_text().splitlines()));self.assertEqual(len(changed),meta['patch_changed_bytes'])
  self.assertEqual(changed,{int(r['file_offset'],16):int(r['after'],16) for r in rows});self.assertNotIn('before',rows[0])
 def test_added_assembly_has_only_reviewed_code_locations(self):
  segments,listing=assemble(ROOT/'patches/kh5.asm');self.assertEqual([off for off,data in segments],[0x2af98,0x2afd0,0x2b000,0x2b040]);self.assertEqual(len(segments[0][1]),25)
  self.assertEqual([dict(file_offset=f'{0x28000+r["pc"]-0x4000:05X}',bank='2A',cpu_address=f'{r["pc"]:04X}',instruction=r['op']+' '+r['arg'],encoding=r['data'].hex()) for r in listing],json.loads((ROOT/'patches/assembly-listing.json').read_text()))
 def test_wrong_inputs_are_refused(self):
  for image in [b'PK\x03\x04',b'\xff'*524288,b'\0'*524287]:
   with self.assertRaises(ValueError):convert(image)
 def test_rejected_cli_leaves_no_output(self):
  with tempfile.TemporaryDirectory() as d:
   d=pathlib.Path(d);src=d/'wrong';src.write_bytes(b'bad');out=d/'out'
   r=subprocess.run([sys.executable,str(ROOT/'convert.py'),str(src),str(out)],capture_output=True)
   self.assertNotEqual(r.returncode,0);self.assertFalse(out.exists());self.assertEqual(src.read_bytes(),b'bad')
 def test_cli_never_overwrites_input_or_output(self):
  with tempfile.TemporaryDirectory() as d:
   src=pathlib.Path(d)/'file';src.write_bytes(b'keep')
   r=subprocess.run([sys.executable,str(ROOT/'convert.py'),str(src),str(src)],capture_output=True)
   self.assertNotEqual(r.returncode,0);self.assertEqual(src.read_bytes(),b'keep')
 @unittest.skipUnless(os.environ.get('KH5_BASELINE'),'No proprietary ROM provided to public tests')
 def test_owned_baseline_integration(self):
  baseline=pathlib.Path(os.environ['KH5_BASELINE']).read_bytes();target,regions=convert(baseline);self.assertEqual(target,source_build(baseline)[0])
  meta=json.loads((ROOT/'patches/release.json').read_text());self.assertEqual(identity(target),meta['target'])
  for offset in [0,0x2a091,0x7ffff]:
   wrong=bytearray(baseline);wrong[offset]^=1
   with self.assertRaises(ValueError):convert(wrong)
  with tempfile.TemporaryDirectory() as d:
   d=pathlib.Path(d);output=d/'output';log=d/'private-log.csv';source=pathlib.Path(os.environ['KH5_BASELINE'])
   original=source.read_bytes();r=subprocess.run([sys.executable,str(ROOT/'convert.py'),str(source),str(output),'--log',str(log)],capture_output=True)
   self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(output.read_bytes(),target);self.assertEqual(source.read_bytes(),original)
   rows=list(csv.DictReader(log.read_text().splitlines()));self.assertEqual(len(rows),meta['changed_bytes'])
   for row in rows:
    i=int(row['file_offset'],16);self.assertEqual(int(row['before'],16),baseline[i]);self.assertEqual(int(row['after'],16),target[i])
if __name__=='__main__':unittest.main()
