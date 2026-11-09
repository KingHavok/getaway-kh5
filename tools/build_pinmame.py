#!/usr/bin/env python3
"""Build the pinned source-only research emulator. Never downloads a game ROM."""
import argparse,pathlib,subprocess,shutil,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
PIN='47ac466023e488e1cbeb19448fa3f56ff9cc8788'
def run(*args,cwd=None):subprocess.run(list(args),cwd=cwd,check=True)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('destination',type=pathlib.Path)
 p.add_argument('--local-source',type=pathlib.Path,help='Optional local PinMAME Git clone, for offline source-only builds')
 p.add_argument('--prepare-only',action='store_true');p.add_argument('--jobs',type=int,default=4)
 a=p.parse_args();source=a.destination.resolve()
 if source.exists():p.error('Destination must not exist; refusing to overwrite a source/build tree')
 run('git','clone','--no-checkout',str(a.local_source.resolve()) if a.local_source else 'https://github.com/vpinball/pinmame.git',str(source))
 run('git','checkout','--detach',PIN,cwd=source)
 run('git','apply','--check',str(ROOT/'tools/pinmame-instrumentation.patch'),cwd=source)
 run('git','apply',str(ROOT/'tools/pinmame-instrumentation.patch'),cwd=source)
 for name in ['getaway_test.c','getaway_test.h']:shutil.copyfile(ROOT/'tools/pinmame'/name,source/'src/wpc'/name)
 cmake=(source/'cmake/sdl3pinmame/CMakeLists.txt').read_text()
 cmake+='\ntarget_compile_definitions(sdl3pinmame PRIVATE REMOTE_DEBUG)\ntarget_sources(sdl3pinmame PRIVATE src/remote_debug/remote_debug.c src/remote_debug/http_server.c src/remote_debug/api_handler.c)\n'
 (source/'CMakeLists.txt').write_text(cmake)
 ui=(source/'src/remote_debug/ui.html').read_bytes()
 (source/'src/remote_debug/ui_html.h').write_text('unsigned char src_remote_debug_ui_html[] = {'+','.join(map(str,ui))+'};\nunsigned int src_remote_debug_ui_html_len = '+str(len(ui))+';\n')
 if a.prepare_only:return
 platform='macos' if sys.platform=='darwin' else 'linux';build=source/'build'
 run('cmake','-S',str(source),'-B',str(build),'-DPLATFORM='+platform,'-DARCH=x64','-DCMAKE_BUILD_TYPE=RelWithDebInfo','-DSDL3PINMAME_SYSTEM_SDL=ON','-DSDL3PINMAME_MAME_DEBUG=ON','-DPINMAME_JIT_ASMJIT=OFF','-DPINMAME_P2K=OFF','-DPINMAME_SPIKE1=OFF')
 run('cmake','--build',str(build),'--parallel',str(a.jobs))
 print(build/'sdl3pinmame')
if __name__=='__main__':main()
