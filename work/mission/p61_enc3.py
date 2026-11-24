p=r'.\MISSION.md'
s=open(p,encoding='utf-8').read()
import collections
c=collections.Counter(ch for ch in s if ord(ch)>127)
for ch,n in c.most_common(10): print(hex(ord(ch)),n)
print('â€”' in s, '\u2014' in s)
