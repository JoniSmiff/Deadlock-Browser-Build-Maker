#!/usr/bin/env python3
"""Refresh the hero, item and tag data baked into index.html.

Run this after a Deadlock patch adds, renames or removes heroes or items:

    python3 tools/update_data.py

It downloads the current game data files from the public
SteamDatabase/GameTracking-Deadlock repository, rebuilds the data table and
rewrites the `var DATA=...;` line in index.html. No third-party packages needed.
"""
import json
import os
import re
import sys
import urllib.request

BASE = "https://raw.githubusercontent.com/SteamDatabase/GameTracking-Deadlock/master/game/citadel/"
FILES = {
    "abilities": "pak01_dir/scripts/abilities.vdata",
    "heroes": "pak01_dir/scripts/heroes.vdata",
    "item_names": "resource/localization/citadel_gc_mod_names/citadel_gc_mod_names_english.txt",
    "hero_names": "resource/localization/citadel_gc_hero_names/citadel_gc_hero_names_english.txt",
    "ability_names": "resource/localization/citadel_heroes/citadel_heroes_english.txt",
    "main": "resource/localization/citadel_main/citadel_main_english.txt",
}
SEED = 0x31415926
SKIP_HEROES = {"hero_base", "hero_targetdummy", "hero_genericperson", "hero_testhero"}
SLOTS = {"EItemSlotType_WeaponMod": "w", "EItemSlotType_Armor": "v", "EItemSlotType_Tech": "s"}


def murmur2(data, seed=SEED):
    """MurmurHash2 (32-bit). The game derives every item, ability and tag ID this way."""
    m = 0x5BD1E995
    h = (seed ^ len(data)) & 0xFFFFFFFF
    i = 0
    while len(data) - i >= 4:
        k = int.from_bytes(data[i:i + 4], "little")
        k = (k * m) & 0xFFFFFFFF
        k ^= k >> 24
        k = (k * m) & 0xFFFFFFFF
        h = ((h * m) & 0xFFFFFFFF) ^ k
        i += 4
    rest = len(data) - i
    if rest == 3:
        h ^= data[i + 2] << 16
    if rest >= 2:
        h ^= data[i + 1] << 8
    if rest >= 1:
        h ^= data[i]
        h = (h * m) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * m) & 0xFFFFFFFF
    h ^= h >> 15
    return h


def hid(name):
    return murmur2(name.encode())


def fetch(path):
    with urllib.request.urlopen(BASE + path, timeout=120) as r:
        return r.read().decode("utf-8", errors="replace")


def blocks(text):
    """Top-level `name = { ... }` blocks of a KV3 text file."""
    return {m.group(1): m.group(2)
            for m in re.finditer(r"^\t(\w+) = *\n\t\{\n(.*?)\n\t\}", text, re.M | re.S)}


def top(block, key):
    m = re.search(r"^\t\t" + key + r" = (.*)$", block, re.M)
    return m.group(1).strip().strip('"') if m else None


def loc(text):
    return dict(re.findall(r'^\s*"([^"]+)"\s+"((?:[^"\\]|\\.)*)"', text, re.M))


def main():
    src = {k: fetch(p) for k, p in FILES.items()}
    A, H = blocks(src["abilities"]), blocks(src["heroes"])
    item_names, hero_names, ability_names = loc(src["item_names"]), loc(src["hero_names"]), loc(src["ability_names"])

    all_hero_ids = {k: int(top(b, "m_HeroID")) for k, b in H.items() if top(b, "m_HeroID")}

    heroes = []
    for key, b in H.items():
        if key in SKIP_HEROES or top(b, "m_bDisabled") == "true" or top(b, "m_bInDevelopment") == "true":
            continue
        name = hero_names.get(key + ":n") or hero_names.get(key)
        if not name:
            continue
        abilities = []
        for slot in range(1, 5):
            m = re.search(r'ESlot_Signature_%d = "(\w+)"' % slot, b)
            if m:
                a = m.group(1)
                abilities.append([hid(a), ability_names.get(a) or item_names.get(a) or a])
        heroes.append({"id": all_hero_ids[key], "n": name, "a": abilities})
    heroes.sort(key=lambda h: h["n"])

    def can_imbue(key, depth=0):
        b = A.get(key)
        if b is None or depth > 6:
            return False
        if re.search(r"^\t\tm_TargetAbilityEffectsToApply =", b, re.M):
            return True
        bases = []
        mb = re.search(r"^\t\t_multibase =\s*\[(.*?)\]", b, re.M | re.S)
        if mb:
            bases += re.findall(r'"(\w+)"', mb.group(1))
        sb = re.search(r'^\t\t_base = "(\w+)"', b, re.M)
        if sb:
            bases.append(sb.group(1))
        return any(can_imbue(x, depth + 1) for x in bases)

    items = []
    for key, b in A.items():
        if top(b, "m_eAbilityType") != "EAbilityType_Item" or top(b, "m_bDisabled") in ("true", "1"):
            continue
        slot, tier = top(b, "m_eItemSlotType"), top(b, "m_iItemTier")
        if key not in item_names or slot not in SLOTS or not tier:
            continue
        item = {"id": hid(key), "n": item_names[key], "s": SLOTS[slot], "t": int(tier[-1])}
        if can_imbue(key) or re.search(r"imbue", b, re.I):
            item["i"] = 1
        m = re.search(r"m_vecDisabledOnHeroes =\s*\[(.*?)\]", b, re.S)
        if m:
            blocked = [all_hero_ids[h] for h in re.findall(r'"(\w+)"', m.group(1)) if h in all_hero_ids]
            if blocked:
                item["x"] = blocked
        alias = item_names.get(key + "_search", "").replace(item_names[key], "").strip()
        if alias:
            item["k"] = alias
        items.append(item)
    items.sort(key=lambda i: (i["s"], i["t"], i["n"]))

    tags = [[hid(k), v] for k, v in re.findall(r'"(citadel_build_tag_\w+)"\s+"([^"]*)"', src["main"])
            if not k.endswith("_label")]

    data = json.dumps({"heroes": heroes, "items": items, "tags": tags}, separators=(",", ":"), ensure_ascii=False)
    if "</script" in data.lower():
        sys.exit("Refusing to write: data contains a script tag.")

    page = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "index.html")
    html = open(page, encoding="utf-8").read()
    new, n = re.subn(r"^var DATA=.*;$", lambda _: "var DATA=" + data + ";", html, count=1, flags=re.M)
    if n != 1:
        sys.exit("Could not find the `var DATA=...;` line in index.html.")
    open(page, "w", encoding="utf-8").write(new)
    print("Updated index.html: %d heroes, %d items, %d tags." % (len(heroes), len(items), len(tags)))


if __name__ == "__main__":
    main()
