from pathlib import Path
import subprocess,sys,os
from datetime import datetime
root=Path(__file__).resolve().parent
pkg=Path.home()/"Downloads/GTA6.Xbox.v1.0.2.1"
exe=root.parent/"exe_dec/game_scarlett_master.exe"
run=root/("boot-"+datetime.now().strftime("%H%M%S"))
run.mkdir()
for mode in ("dry-run","run"):
 args=[str(root/"boot-main/gta6rt.exe"),"--"+mode,str(exe),"--game-dir",str(pkg),"--overlay",str(run/"overlay"),"--trace",str(run/(mode+".jsonl"))]
 with (run/(mode+".log")).open("wb") as f:
  try: result=subprocess.run(args,cwd=run,stdout=f,stderr=subprocess.STDOUT,timeout=75)
  except subprocess.TimeoutExpired: print(mode,"timeout",run);break
 print(run.name,mode,hex(result.returncode&0xffffffff),flush=True)
 if result.returncode and mode=="dry-run": break
