p=r'.\MISSION.md'
s=open(p,encoding='utf-8').read()
print('lines',len(s.splitlines()),'chars',len(s))
print('mojibake:', 'â€' in s, 'replacement:', s.count('\ufffd'))
