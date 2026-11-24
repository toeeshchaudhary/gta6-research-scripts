p=r'.\work\scripts\out\story_groups\g1730_045AE000.bin'
b=open(p,'rb').read()
def show(s,e):
    for i in range(s,e,16):
        row=b[i:i+16]
        print('%6d %-47s'%(i,row.hex(' ')))
show(37952,38300)
