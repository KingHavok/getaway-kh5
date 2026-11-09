"""Fail-closed, local-only L5 conversion. No ROM downloads or bundled game data."""
import hashlib,json,zlib
from pathlib import Path
from .assembler import assemble
from .led import transform as led_transform
ROOT=Path(__file__).resolve().parents[1]

def identity(data):
    return dict(bytes=len(data),crc32=f'{zlib.crc32(data)&0xffffffff:08x}',sha1=hashlib.sha1(data).hexdigest(),sha256=hashlib.sha256(data).hexdigest(),wpc_checksum=f'{sum(data)&65535:04X}')

def checksum(data,revision=5):
    out=bytearray(data);out[-20:-16]=bytes([0,255,0,255])
    total=sum(out)&65535;word=(total&0xff00)|revision
    out[-20:-18]=bytes([255-(total&255),255-(total>>8)])
    out[-18:-16]=word.to_bytes(2,'big')
    if sum(out)&65535!=word:raise ValueError('Checksum construction failed')
    return bytes(out)

def make_ips(base,target):
    if len(base)!=len(target):raise ValueError('Image size mismatch')
    out=bytearray(b'PATCH');i=0
    while i<len(base):
        if base[i]==target[i]:i+=1;continue
        start=i
        while i<len(base) and base[i]!=target[i] and i-start<65535:i+=1
        if start==0x454f46:raise ValueError('Reserved IPS address')
        out+=start.to_bytes(3,'big')+(i-start).to_bytes(2,'big')+target[start:i]
    return bytes(out+b'EOF')

def apply_ips(base,patch):
    if not patch.startswith(b'PATCH'):raise ValueError('Invalid IPS header')
    out=bytearray(base);pos=5;occupied=set()
    while True:
        if patch[pos:pos+3]==b'EOF':
            if pos+3!=len(patch):raise ValueError('Trailing IPS data')
            return bytes(out)
        if pos+5>len(patch):raise ValueError('Truncated IPS record')
        offset=int.from_bytes(patch[pos:pos+3],'big');count=int.from_bytes(patch[pos+3:pos+5],'big');pos+=5
        if count:
            data=patch[pos:pos+count];pos+=count
            if len(data)!=count:raise ValueError('Truncated IPS payload')
        else:
            if pos+3>len(patch):raise ValueError('Truncated RLE record')
            count=int.from_bytes(patch[pos:pos+2],'big');data=patch[pos+2:pos+3]*count;pos+=3
            if not count:raise ValueError('Empty RLE record')
        if offset+count>len(out):raise ValueError('IPS record outside U6')
        addresses=set(range(offset,offset+count))
        if occupied&addresses:raise ValueError('Overlapping IPS records')
        occupied|=addresses;out[offset:offset+count]=data

def gameplay_build(base):
    spec=json.loads((ROOT/'patches/edits.json').read_text());out=bytearray(base);regions=[]
    for edit in spec['edits']:
        off=int(edit['offset'],16);data=bytes.fromhex(edit['after'])
        if off+len(data)>len(out):raise ValueError('Source edit out of range')
        out[off:off+len(data)]=data;regions.append((off,off+len(data),edit['id']))
    segments,_=assemble(ROOT/'patches/kh5.asm')
    for off,data in segments:
        if base[off:off+len(data)]!=b'\xff'*len(data):raise ValueError('Patch code is not in baseline FF fill')
        out[off:off+len(data)]=data;regions.append((off,off+len(data),'ASM'))
    return bytes(out),regions

def source_build(base):
    gameplay,regions=gameplay_build(base)
    regions.append((0x7DCF5,0x7DD5C,'LED-V2'))
    return checksum(led_transform(gameplay)),regions

def convert(base):
    release=json.loads((ROOT/'patches/release.json').read_text())
    actual=identity(base);expected=release['baseline']
    if any(actual[k]!=expected[k] for k in ['bytes','crc32','sha1','sha256','wpc_checksum']):raise ValueError('Input is not the exact official L5 baseline; unzip your own raw U6 first')
    if int.from_bytes(base[-18:-16],'big')!=0x4905:raise ValueError('Baseline stored checksum mismatch')
    patch=(ROOT/release['patch_file']).read_bytes()
    if hashlib.sha256(patch).hexdigest()!=release['patch_sha256']:raise ValueError('Published IPS integrity mismatch')
    gameplay=apply_ips(base,patch)
    if gameplay!=gameplay_build(base)[0]:raise ValueError('IPS differs from gameplay source')
    target=checksum(led_transform(gameplay));built,regions=source_build(base)
    if target!=built:raise ValueError('IPS differs from annotated patch source')
    actual=identity(target)
    if actual!=release['target']:raise ValueError('Output does not match the qualified KH5 image')
    if int.from_bytes(target[-18:-16],'big')!=sum(target)&65535:raise ValueError('Output stored checksum mismatch')
    return target,regions
