from pathlib import Path
import subprocess,os,tempfile,sys
root=Path(__file__).resolve().parent
run=Path(tempfile.mkdtemp(prefix="signature-measure-",dir=root))
binary=root/"sampler-build"/sys.argv[1]
env=dict(os.environ,LEONIDA_D3D12="vulkan",LEONIDA_SHADERS=str(root/"shaders-probe"))
env.pop("LEONIDA_SKIP_INT3",None)
script=run/"measure.gdb"
script.write_text('''set pagination off
set auto-solib-add off
set print thread-events off
handle SIGSEGV nostop noprint pass
set confirm off
set debuginfod enabled off
set breakpoint pending on
starti
hbreak *0x144e9b660 if *(unsigned long long*)$rsp >= 0x142479554 && *(unsigned long long*)$rsp <= 0x142479655
commands
silent
printf "SIGNATURE next=%#llx hr=%#x\\n", *(unsigned long long*)$rsp, $ecx
continue
end
hbreak *0x1419f4f58
commands
silent
quit
end
continue
''')
with (run/"gdb.log").open("wb") as f:
 try:subprocess.run(["C:/msys64/mingw64/bin/gdb.exe","-nx","--batch","-x",str(script),"--args",str(binary),"--run",str(root.parent/"exe_dec/game_scarlett_master.exe"),"--game-dir",str(Path.home()/"Downloads/GTA6.Xbox.v1.0.2.1"),"--overlay",str(run/"overlay")],cwd=run,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=40)
 except subprocess.TimeoutExpired:print("debugger timeout")
lines=(run/"gdb.log").read_bytes().decode(errors="replace").splitlines();print(run.name,[s[:160] for s in lines if "SIGNATURE " in s or "SIG" in s or "breakpoint" in s.lower()][-10:])


