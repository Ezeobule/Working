#!/usr/bin/env python3
import npc_contact_extract as extractor

extractor.STATES = [
    ("Abia", "abia"),
    ("Adamawa", "adamawa"),
    ("Akwa Ibom", "akwa-ibom"),
    ("Anambra", "anambra"),
    ("Bauchi", "bauchi"),
    ("Bayelsa", "bayelsa"),
    ("Benue", "benue"),
    ("Borno", "borno"),
    ("Cross River", "cross-river"),
    ("Delta", "delta"),
    ("Ebonyi", "ebonyi"),
    ("Edo", "edo"),
    ("Ekiti", "ekiti"),
    ("Enugu", "enugu"),
    ("Gombe", "gombe"),
    ("Imo", "imo"),
    ("Jigawa", "jigawa"),
    ("Kaduna", "kaduna"),
    ("Kano", "kano"),
    ("Katsina", "katsina"),
    ("Kebbi", "kebbi"),
    ("Kogi", "kogi"),
    ("Kwara", "kwara"),
    ("Lagos", "lagos"),
    ("Nasarawa", "nasarawa"),
    ("Niger", "niger"),
    ("Ogun", "ogun"),
    ("Ondo", "ondo"),
    ("Osun", "osun"),
    ("Oyo", "oyo"),
    ("Plateau", "plateau"),
    ("Rivers", "rivers"),
    ("Sokoto", "sokoto"),
    ("Taraba", "taraba"),
    ("Yobe", "yobe"),
    ("Zamfara", "zamfara"),
    ("Abuja", "abuja"),
]
extractor.OUTDIR = "npc_nationwide_output"
extractor.TARGET = 10000

if __name__ == "__main__":
    extractor.main()
