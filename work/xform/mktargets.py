def joaat(s):
    h=0
    for ch in s.lower():
        h=(h+ord(ch))&0xFFFFFFFF; h=(h+(h<<10))&0xFFFFFFFF; h^=h>>6
    h=(h+(h<<3))&0xFFFFFFFF; h^=h>>11
    return (h+(h<<15))&0xFFFFFFFF
names=["nm34_unq_1_gfa_bespoke_atrium","int_bnk1b_branding","des_bhf_tower_02_collapse_06",
       "prop_am_fencetech_rail_09_3m_nc","int_bnk1b_bank_desks_01"]
hs=[joaat(n) for n in names]
extra=[l.strip() for l in open(r"work\xform\out\targets.txt") if l.strip()]
with open(r"work\xform\out\targets2.txt","w") as f:
    for h in hs: f.write("%08X\n"%h)
    for e in extra: f.write(e+"\n")
print("targets", len(hs)+len(extra), [hex(h) for h in hs])
