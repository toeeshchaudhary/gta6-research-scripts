import io
p=r'.\MISSION.md'
s=open(p,encoding='utf-8',errors='replace').read()
s=s.replace('62.7 % of their dwords','73.7 % of their dwords')
open(p,'w',encoding='utf-8').write(s)
import re
print([l for l in s.splitlines() if '73.7' in l or '62.7' in l])
print('mojibake check:', 'â€”' in s)
