import json

with open('cache/research_paper11.json') as f:
    data = json.load(f)

print('Total refs:', len(data['references']))
print()
for r in data['references'][:10]:
    print(f"[{r['number']}] {r['raw'][:100]}")