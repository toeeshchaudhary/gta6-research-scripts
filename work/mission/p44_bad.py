import sys,os,struct
sys.path.insert(0,r'.\work\mission')
import lib_min as L
b=open(os.path.join(L.GROUPS,'g0023_0318E000.bin'),'rb').read()
c=L.parse_container(b)
for ch in c['chunks']:
    if ch['tag']==0x10d:
        print('chunk size',ch['size'],'off',ch['off'])
        print(b[ch['off']:ch['off']+160].hex(' '))
        recs=L.parse_records(b,ch['off'],ch['size'])
        print('nrec',len(recs))
        for r in recs[:8]: print(hex(r['key']),r['kind'],r['offset'],r['count'],r['count_dup'],r['dword'])
        break
