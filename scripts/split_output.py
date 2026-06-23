#!/usr/bin/env python3
import base64
import csv
import gzip
import io
import json
import os

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

memory = io.StringIO(newline='')
writer = csv.DictWriter(memory, fieldnames=fields, lineterminator='\n')
writer.writeheader()
for row in rows:
    writer.writerow({key: row.get(key, '') for key in fields})
raw = memory.getvalue().encode('utf-8')
encoded = base64.b64encode(gzip.compress(raw, compresslevel=9)).decode('ascii')
transfer_size = 18000
transfer_files = []
for start in range(0, len(encoded), transfer_size):
    filename = f'transfer_{start//transfer_size+1:03d}.txt'
    transfer_files.append(filename)
    with open(os.path.join(outdir, filename), 'w', encoding='ascii') as f:
        f.write(encoded[start:start+transfer_size])

manifest = {
    'rows': len(rows),
    'part_size': part_size,
    'files': files,
    'transfer_files': transfer_files,
    'transfer_characters': len(encoded),
    'raw_bytes': len(raw)
}
with open(os.path.join(outdir, 'manifest.json'), 'w', encoding='utf-8') as f:
    json.dump(manifest, f, indent=2)
print(json.dumps(manifest))
