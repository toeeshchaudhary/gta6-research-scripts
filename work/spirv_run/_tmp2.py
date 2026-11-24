import json,os
n='022275_vs_VS_HeightmapDrawLines_110179a6_Wrapped'
for d in ['..\\shaders','..\\shaders2']:
    idx=json.load(open(os.path.join(d,'index.json'),encoding='utf-8'))
    hit=[e for e in idx if n in e['file'] or n==os.path.splitext(e['file'])[0]]
    print(d,len(idx),hit[:1])
for f in ['spirv_in\\index.json','s2_in\\index.json']:
    idx=json.load(open(f,encoding='utf-8'))
    print(f,len(idx),sum(1 for e in idx if n in e['file']))
