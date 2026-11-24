p=r'.\MISSION.md'
s=open(p,encoding='utf-8').read()
s=s.replace('\u00e2\u20ac\u201d','\u2014').replace('\u00e2\u0080\u0094','\u2014')
open(p,'w',encoding='utf-8',newline='\n').write(s)
print('mojibake left:', 'â€' in s)
print(s.splitlines()[33])
