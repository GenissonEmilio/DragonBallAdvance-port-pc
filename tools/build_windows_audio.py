"""Build the native Windows WASAPI audio runner and validation DLL."""
from pathlib import Path
import argparse,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
GCC=ROOT/'tools/local/w64devkit/bin/gcc.exe'
SOURCES=['port/audio/music_player_update.c','port/audio/audio_helpers.c','port/native/audio_runtime.c']

def build(out,source=None,helpers_source=None,player_source=None):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    sources=[ROOT/p for p in SOURCES]
    if source:sources[-1]=Path(source).resolve()
    if helpers_source:sources[1]=Path(helpers_source).resolve()
    if player_source:sources[0]=Path(player_source).resolve()
    flags=['-std=c99','-O2','-Wall','-Wextra','-Werror','-I'+str(ROOT/'port/include'),'-I'+str(ROOT/'port/native')]
    commands=[
        [str(GCC),*flags,'-shared',*map(str,sources),'-o',str(out/'audio_runtime.dll')],
        [str(GCC),*flags,*map(str,sources),str(ROOT/'port/windows/audio_main.c'),
            '-o',str(out/'dbaa_audio.exe'),'-lole32','-luuid']]
    for command in commands:
        r=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
        if r.returncode:raise RuntimeError(r.stdout+r.stderr)
    paths=[*sources,ROOT/'port/windows/audio_main.c',ROOT/'port/native/audio_runtime.h',
        *sorted((ROOT/'port/include').glob('*.h'))]
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    proof=dict(commands=commands,sources_sha256={str(p.relative_to(ROOT))if p.is_relative_to(ROOT)else str(p):sha(p)for p in paths},
        compiler_sha256=sha(GCC),tool_sha256=sha(__file__),
        exe_sha256=sha(out/'dbaa_audio.exe'),dll_sha256=sha(out/'audio_runtime.dll'))
    (out/'build.json').write_text(json.dumps(proof,indent=2)+'\n')
    return out/'audio_runtime.dll'

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out-dir',type=Path,default=ROOT/'build/windows_audio')
    a=p.parse_args();build(a.out_dir);print('Built',a.out_dir/'dbaa_audio.exe')
if __name__=='__main__':main()
