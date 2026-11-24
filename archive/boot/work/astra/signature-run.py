from pathlib import Path
import subprocess,os,tempfile,json,hashlib
root=Path(__file__).resolve().parent
binary=root/"sampler-build/gta6rt.exe"
pkg=Path.home()/"Downloads/GTA6.Xbox.v1.0.2.1"
env=dict(os.environ,LEONIDA_D3D12="vulkan",LEONIDA_SHADERS=str(root/"shaders-probe"))
print("runtime sha256",hashlib.sha256(binary.read_bytes()).hexdigest(),flush=True)
for label in ("signature-normal",):
 run=Path(tempfile.mkdtemp(prefix="sampler-"+label+"-",dir=root))
 env.pop("LEONIDA_SKIP_INT3",None)
 if label=="diagnostic":env["LEONIDA_SKIP_INT3"]="1"
 for mode in ("dry-run","run"):
  log=run/(mode+".log"); trace=run/(mode+".jsonl")
  args=[str(binary),"--"+mode,str(root.parent/"exe_dec/game_scarlett_master.exe"),"--game-dir",str(pkg),"--overlay",str(run/"overlay"),"--trace",str(trace)]
  with log.open("wb") as stream:
   try: rc=subprocess.run(args,cwd=run,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=60).returncode
   except subprocess.TimeoutExpired: print(run.name,"timeout",flush=True);break
  print(run.name,mode,hex(rc&0xffffffff),flush=True)
  if mode=="dry-run" and rc: break
  if mode=="run":
   rows=[json.loads(s) for s in trace.read_bytes().splitlines() if s]
   for r in rows[-3:]:print(r["kind"],r.get("code"),r.get("at"))


