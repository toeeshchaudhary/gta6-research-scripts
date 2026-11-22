import sys
sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout,"reconfigure") else None
s=open("ENGINE.md",encoding="utf-8").read()
i=s.find("## Measured performance")
print(s[i:i+520])
