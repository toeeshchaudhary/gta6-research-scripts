p=r'.\MISSION.md'
b=open(p,'rb').read()
s=b.decode('utf-8',errors='replace')
i=s.find('\u00e2')
print(repr(s[i-20:i+10]))
import collections
c=collections.Counter(ch for ch in s if ord(ch)>127)
print(c.most_common(8))
