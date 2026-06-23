#!/usr/bin/env python3
import csv
import json
import math
import os
import random
import re
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE = "https://nigeriapropertycentre.com"
STATES = [
    ("Enugu", "enugu"),
    ("Ebonyi", "ebonyi"),
    ("Imo", "imo"),
    ("Anambra", "anambra"),
    ("Delta", "delta"),
    ("Abia", "abia"),
    ("Edo", "edo"),
    ("Rivers", "rivers"),
    ("Cross River", "cross-river"),
    ("Akwa Ibom", "akwa-ibom"),
    ("Abuja", "abuja"),
    ("Ondo", "ondo"),
    ("Ekiti", "ekiti"),
    ("Kaduna", "kaduna"),
]
OUTDIR = "npc_output"
TARGET = 1000
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

session = requests.Session()
session.headers.update(HEADERS)


def fetch(url, retries=4):
    last = None
    for attempt in range(retries):
        try:
            r = session.get(url, timeout=35)
            if r.status_code == 200 and len(r.text) > 500:
                return r.text
            last = RuntimeError(f"HTTP {r.status_code}, {len(r.text)} bytes")
        except Exception as exc:
            last = exc
        time.sleep(1.0 + attempt * 1.5 + random.random())
    raise RuntimeError(f"Failed {url}: {last}")


def normalize_phone(raw):
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("00234"):
        digits = digits[2:]
    if digits.startswith("234") and len(digits) == 13:
        local = "0" + digits[3:]
    elif len(digits) == 11 and digits.startswith("0"):
        local = digits
    elif len(digits) == 10 and digits[0] in "789":
        local = "0" + digits
    else:
        return None
    if len(local) != 11 or local[1] not in "789":
        return None
    return "+234" + local[1:]


def extract_phone_candidates(blob):
    if not blob:
        return []
    # Capture Nigerian mobile numbers whether written as 0XXXXXXXXXX, 234XXXXXXXXXX or +234XXXXXXXXXX.
    pats = re.findall(r"(?<!\d)(?:\+?234[\s\-]?|0)?[789]\d(?:[\s\-]?\d){8}(?!\d)", blob)
    out = []
    for p in pats:
        n = normalize_phone(p)
        if n and n not in out:
            out.append(n)
    return out


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip(" \t\r\n,|")


def directory_profiles(state_name, slug):
    first_url = f"{BASE}/{slug}/agents"
    html = fetch(first_url)
    soup = BeautifulSoup(html, "html.parser")
    txt = soup.get_text(" ", strip=True)
    m = re.search(r"Results\s+\d+\s*-\s*\d+\s+of\s+([\d,]+)", txt, re.I)
    total = int(m.group(1).replace(",", "")) if m else 20
    pages = max(1, math.ceil(total / 20))
    found = {}
    page_urls = []
    for page in range(1, pages + 1):
        url = first_url if page == 1 else f"{first_url}?page={page}"
        page_urls.append(url)
        if page > 1:
            try:
                html = fetch(url)
                soup = BeautifulSoup(html, "html.parser")
            except Exception:
                continue
        for a in soup.find_all("a", href=True):
            href = urljoin(BASE, a.get("href"))
            path = urlparse(href).path.rstrip("/")
            if re.fullmatch(r"/agents/[a-zA-Z0-9_%.'()&+\-]+-\d+", path):
                name = clean(a.get_text(" ", strip=True))
                if not name or name.lower().startswith("view property"):
                    continue
                found[href] = name
        time.sleep(0.12)
    return total, found, page_urls


def between(text, start_label, end_labels):
    start = re.search(rf"(?:^|\n){re.escape(start_label)}\s*(?:\n|$)", text, re.I)
    if not start:
        return ""
    tail = text[start.end():]
    positions = []
    for label in end_labels:
        mm = re.search(rf"(?:^|\n){re.escape(label)}\s*(?:\n|$)", tail, re.I)
        if mm:
            positions.append(mm.start())
    end = min(positions) if positions else min(len(tail), 1000)
    return clean(tail[:end])


def parse_profile(item):
    url, seed_name, market_states, directory_urls = item
    try:
        html = fetch(url)
    except Exception as exc:
        return {"profile_url": url, "error": str(exc)}
    soup = BeautifulSoup(html, "html.parser")
    title = clean(soup.title.get_text(" ", strip=True) if soup.title else seed_name)
    name = re.sub(r"\s*-\s*Property Listings.*$", "", title, flags=re.I).strip() or seed_name
    text = soup.get_text("\n", strip=True)
    pos = text.lower().rfind("contact agent")
    section = text[pos:pos + 1800] if pos >= 0 else text
    address = between(section, "Address", ["Phone", "Whatsapp", "Website", "Filter Property"])
    phone_blob = between(section, "Phone", ["Whatsapp", "Website", "Filter Property"])
    wa_blob = between(section, "Whatsapp", ["Website", "Filter Property"])
    phones = extract_phone_candidates(phone_blob)
    whatsapps = extract_phone_candidates(wa_blob)
    if not phones and not whatsapps:
        # Conservative fallback: only inspect the contact section, never listing descriptions.
        all_nums = extract_phone_candidates(section[:900])
        phones = all_nums
    website = ""
    contact_heading = soup.find(lambda tag: getattr(tag, "name", None) in ["h2", "h3", "h4"] and "contact agent" in tag.get_text(" ", strip=True).lower())
    if contact_heading:
        container = contact_heading.parent
        for a in container.find_all("a", href=True):
            href = a.get("href", "")
            if href.startswith("http") and "nigeriapropertycentre.com" not in href:
                website = href
                break
    return {
        "agent_name": name,
        "market_states": sorted(market_states),
        "office_address": address,
        "phones": phones,
        "whatsapps": whatsapps,
        "website": website,
        "profile_url": url,
        "directory_urls": sorted(directory_urls),
        "error": "",
    }


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    profile_map = {}
    directory_summary = []
    for state_name, slug in STATES:
        try:
            total, found, page_urls = directory_profiles(state_name, slug)
            directory_summary.append({"state": state_name, "advertised_agent_profiles": total, "profile_links_collected": len(found), "directory_url": f"{BASE}/{slug}/agents", "error": ""})
            for url, name in found.items():
                rec = profile_map.setdefault(url, {"name": name, "states": set(), "directories": set()})
                rec["states"].add(state_name)
                rec["directories"].update(page_urls)
        except Exception as exc:
            directory_summary.append({"state": state_name, "advertised_agent_profiles": 0, "profile_links_collected": 0, "directory_url": f"{BASE}/{slug}/agents", "error": str(exc)})

    items = [(url, v["name"], v["states"], v["directories"]) for url, v in profile_map.items()]
    profiles = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = [pool.submit(parse_profile, item) for item in items]
        for i, fut in enumerate(as_completed(futures), 1):
            profiles.append(fut.result())
            if i % 50 == 0:
                print(f"Parsed {i}/{len(items)} profiles", flush=True)

    contacts = {}
    for p in profiles:
        if p.get("error"):
            continue
        phone_set = set(p.get("phones", []))
        wa_set = set(p.get("whatsapps", []))
        for number in sorted(phone_set | wa_set):
            ctype = "Phone + WhatsApp" if number in phone_set and number in wa_set else ("Phone" if number in phone_set else "WhatsApp")
            if number not in contacts:
                contacts[number] = {
                    "phone_e164": number,
                    "phone_local": "0" + number[4:],
                    "contact_type": ctype,
                    "agent_company": p["agent_name"],
                    "market_states": set(p["market_states"]),
                    "office_address": p["office_address"],
                    "website": p["website"],
                    "profile_urls": {p["profile_url"]},
                    "directory_urls": set(p["directory_urls"]),
                }
            else:
                c = contacts[number]
                c["market_states"].update(p["market_states"])
                c["profile_urls"].add(p["profile_url"])
                c["directory_urls"].update(p["directory_urls"])
                if p["agent_name"] not in c["agent_company"]:
                    c["agent_company"] += " | " + p["agent_name"]
                if c["contact_type"] != ctype:
                    c["contact_type"] = "Phone + WhatsApp"

    # Round-robin selection guarantees representation from every requested market before Abuja fills the remainder.
    by_state = defaultdict(list)
    for number, c in contacts.items():
        for state in c["market_states"]:
            by_state[state].append(number)
    for state in by_state:
        by_state[state].sort(key=lambda n: (contacts[n]["agent_company"].lower(), n))
    cursors = defaultdict(int)
    selected = []
    chosen = set()
    while len(selected) < min(TARGET, len(contacts)):
        progress = False
        for state, _slug in STATES:
            arr = by_state.get(state, [])
            while cursors[state] < len(arr) and arr[cursors[state]] in chosen:
                cursors[state] += 1
            if cursors[state] < len(arr):
                n = arr[cursors[state]]
                cursors[state] += 1
                chosen.add(n)
                selected.append(n)
                progress = True
                if len(selected) >= min(TARGET, len(contacts)):
                    break
        if not progress:
            break

    extraction_date = date.today().isoformat()
    contact_rows = []
    for idx, number in enumerate(selected, 1):
        c = contacts[number]
        contact_rows.append({
            "contact_id": f"NPC-{idx:04d}",
            "phone_e164": c["phone_e164"],
            "phone_local": c["phone_local"],
            "contact_type": c["contact_type"],
            "agent_company": c["agent_company"],
            "market_states": ", ".join(sorted(c["market_states"])),
            "office_address": c["office_address"],
            "website": c["website"],
            "npc_profile_url": " | ".join(sorted(c["profile_urls"])),
            "directory_source_urls": " | ".join(sorted(c["directory_urls"])),
            "extraction_date": extraction_date,
            "verification_note": "Public business contact displayed on Nigeria Property Centre agent profile",
        })

    fields = list(contact_rows[0].keys()) if contact_rows else ["contact_id"]
    with open(os.path.join(OUTDIR, "unique_contacts.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(contact_rows)

    profile_fields = ["agent_name", "market_states", "office_address", "phones", "whatsapps", "website", "profile_url", "directory_urls", "error"]
    with open(os.path.join(OUTDIR, "agent_profiles.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=profile_fields)
        w.writeheader()
        for p in sorted(profiles, key=lambda x: x.get("agent_name", "").lower()):
            q = dict(p)
            for k in ["market_states", "phones", "whatsapps", "directory_urls"]:
                if isinstance(q.get(k), list): q[k] = " | ".join(q[k])
            w.writerow({k: q.get(k, "") for k in profile_fields})

    with open(os.path.join(OUTDIR, "state_directory_summary.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=directory_summary[0].keys())
        w.writeheader(); w.writerows(directory_summary)

    status = {
        "target_unique_contacts": TARGET,
        "unique_contacts_available": len(contacts),
        "unique_contacts_written": len(contact_rows),
        "unique_profiles_discovered": len(profile_map),
        "profiles_parsed": sum(1 for p in profiles if not p.get("error")),
        "profiles_failed": sum(1 for p in profiles if p.get("error")),
        "states_requested": [s for s, _ in STATES],
        "extraction_date": extraction_date,
    }
    with open(os.path.join(OUTDIR, "status.json"), "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2)
    print(json.dumps(status, indent=2), flush=True)

if __name__ == "__main__":
    main()
