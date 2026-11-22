p="ENGINE.md"
s=open(p,encoding="utf-8").read()
bad=[(i,c) for i,c in enumerate(s) if ord(c)>127]
print("non-ascii count",len(bad), set(c for _,c in bad))
