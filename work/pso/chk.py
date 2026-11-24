for f in ('work/pso/dump/script.jsonl','work/pso/dump/story.jsonl'):
    n=0; mx=0; bad=0
    for line in open(f,encoding='utf-8',newline=''):
        n+=1; mx=max(mx,len(line))
        if not line.rstrip('\r\n').endswith('}'): bad+=1; print(f,"BAD line",n,len(line))
    print(f,"lines",n,"maxlen",mx,"bad",bad)
