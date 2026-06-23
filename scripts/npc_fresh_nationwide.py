#!/usr/bin/env python3
import csv
import json
import os
from datetime import datetime, timezone

import npc_contact_extract as npc

npc.STATES = [
    ("Abia", "abia"), ("Adamawa", "adamawa"), ("Akwa Ibom", "akwa-ibom"),
    ("Anambra", "anambra"), ("Bauchi", "bauchi"), ("Bayelsa", "bayelsa"),
    ("Benue", "benue"), ("Borno", "borno"), ("Cross River", "cross-river"),
    ("Delta", "delta"), ("Ebonyi", "ebonyi"), ("Edo", "edo"),
    ("Ekiti", "ekiti"), ("Enugu", "enugu"), ("Gombe", "gombe"),
    ("Imo", "imo"), ("Jigawa", "jigawa"), ("Kaduna", "kaduna"),
    ("Kano", "kano"), ("Katsina", "katsina"), ("Kebbi", "kebbi"),
    ("Kogi", "kogi"), ("Kwara", "kwara"), ("Lagos", "lagos"),
    ("Nasarawa", "nasarawa"), ("Niger", "niger"), ("Ogun", "ogun"),
    ("Ondo", "ondo"), ("Osun", "osun"), ("Oyo", "oyo"),
    ("Plateau", "plateau"), ("Rivers", "rivers"), ("Sokoto", "sokoto"),
    ("Taraba", "taraba"), ("Yobe", "yobe"), ("Zamfara", "zamfara"),
    ("Abuja", "abuja")
]
npc.OUTDIR = "npc_fresh_output"
npc.TARGET = 10000
npc.main()


def phones_from(path):
    out = set()
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            value = npc.normalize_phone(row.get("phone_e164") or row.get("phone_local"))
            if value:
                out.add(value)
    return out

baseline = phones_from("npc_output/unique_contacts.csv")
all_path = os.path.join(npc.OUTDIR, "unique_contacts.csv")
with open(all_path, newline="", encoding="utf-8-sig") as f:
    all_rows = list(csv.DictReader(f))

new_rows = []
seen = set()
for row in all_rows:
    phone = npc.normalize_phone(row.get("phone_e164") or row.get("phone_local"))
    if phone and phone not in baseline and phone not in seen:
        seen.add(phone)
        row["contact_id"] = f"NPC-NEW-{len(new_rows)+1:05d}"
        new_rows.append(row)

new_path = os.path.join(npc.OUTDIR, "new_unique_contacts_excluding_baseline.csv")
fields = list(all_rows[0].keys()) if all_rows else ["contact_id"]
with open(new_path, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(new_rows)

with open(os.path.join(npc.OUTDIR, "status.json"), encoding="utf-8") as f:
    status = json.load(f)
status.update({
    "fresh_run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "jurisdictions_requested": len(npc.STATES),
    "baseline_unique_phones": len(baseline),
    "overlap_removed_against_baseline": len(all_rows) - len(new_rows),
    "new_unique_contacts_excluding_baseline": len(new_rows),
    "new_output_duplicate_count": len(new_rows) - len(seen),
})
with open(os.path.join(npc.OUTDIR, "status.json"), "w", encoding="utf-8") as f:
    json.dump(status, f, indent=2)
print(json.dumps(status, indent=2))
