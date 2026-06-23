#!/usr/bin/env python3
import csv, json, os

source = 'npc_output/unique_contacts.csv'
outdir = 'npc_output/compact_parts'
fields = ['contact_id','phone_e164','phone_local','contact_type','agent_company','market_states','office_address','website','npc_profile_url','extraction_date','verification_note']
os.makedirs(outdir, exist_ok=True)
for filename in os.listdir(outdir):
    os.remove(os.path.join(outdir, filename))
with open(source, encoding='utf-8-sig', newline='') as f:
    rows = list(csv.DictReader(f))
part_size = 50
files = []
for start in range(0, len(rows), part_size):
    filename = f'part_{start//part_size+1:03d}.csv'
    files.append(filename)
    with open(os.path.join(outdir, filename), 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows[start:start+part_size]:
            writer.writerow({key: row.get(key, '') for key in fields})
with open(os.path.join(outdir, 'manifest.json'), 'w', encoding='utf-8') as f:
    json.dump({'rows': len(rows), 'part_size': part_size, 'files': files}, f, indent=2)
print(len(rows), len(files))
