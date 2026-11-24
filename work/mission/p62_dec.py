p=r'.\MISSION.md'
s=open(p,encoding='utf-8').read()
s=s.replace('\u2014','@@EMD@@')
raw=s.encode('latin-1',errors='replace')
s2=raw.decode('utf-8',errors='replace')
s2=s2.replace('@@EMD@@','\u2014')
open(p,'w',encoding='utf-8',newline='\n').write(s2)
import collections
c=collections.Counter(ch for ch in s2 if ord(ch)>127)
print([hex(ord(k)) for k,_ in c.most_common(6)])
print(s2.count('\ufffd'),'replacement chars')
print(s2.splitlines()[33])
print(s2.splitlines()[48])
