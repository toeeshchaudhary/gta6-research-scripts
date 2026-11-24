p=r'.\work\scripts\out\story_groups\g1730_045AE000.bin'
b=open(p,'rb').read()
def show(s,e):
    for i in range(s,e,16): print('%6d %s'%(i,b[i:i+16].hex(' ')))
show(1960,2120)
print('=== around 9900')
show(9900,10060)
