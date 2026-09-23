#!/usr/bin/env python3
"""OpenStreetMap のタグ条件 → places.json（「日本のスキー場」「ドイツの城」などカテゴリで集めたいとき）

  osm_places.py 'landuse=winter_sports' --country JP -o places.json
  osm_places.py 'historic=castle' --country DE -o places.json --named-only

タグ条件は Overpass の書式（key=value または key）。名前のない要素は --named-only で除外し、
同名の要素は1つにまとめる。Overpass は User-Agent なしだと 406 を返し、本家が落ちていることも多いので
ミラーを順に試す。
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sv

ENDPOINTS = ["https://overpass-api.de/api/interpreter",
             "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
             "https://overpass.kumi.systems/api/interpreter"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tag", help="例: landuse=winter_sports / amenity=university")
    ap.add_argument("--country", required=True, help="ISO 3166-1 alpha-2（例: JP）")
    ap.add_argument("-o", "--out", default="places.json")
    ap.add_argument("--named-only", action="store_true")
    ap.add_argument("--lang", default="ja", help="name:<lang> があれば表示名に使う")
    ap.add_argument("--group")
    a = ap.parse_args()
    k, _, v = a.tag.partition("=")
    cond = f'["{k}"="{v}"]' if v else f'["{k}"]'
    q = (f'[out:json][timeout:240];area["ISO3166-1"="{a.country}"][admin_level=2]->.a;'
         f'(nwr{cond}(area.a););out center tags;')
    d = None
    for ep in ENDPOINTS:
        try:
            d = json.loads(sv.http(ep, data={"data": q}, timeout=280, retries=2))
            break
        except Exception as e:
            print(f"overpass failed at {ep}: {e}", file=sys.stderr)
    if d is None:
        sys.exit("Overpass のすべてのエンドポイントで失敗しました")
    places, seen = [], set()
    for e in d["elements"]:
        t = e.get("tags", {})
        name = t.get(f"name:{a.lang}") or t.get("name")
        if a.named_only and not name:
            continue
        c = e.get("center") or {"lat": e.get("lat"), "lon": e.get("lon")}
        if c.get("lat") is None:
            continue
        key = name or f"{e['type']}/{e['id']}"
        if key in seen:
            continue
        seen.add(key)
        p = {"name": key, "lat": c["lat"], "lng": c["lon"], "osm": f"{e['type']}/{e['id']}"}
        if t.get("name:en"):
            p["name_en"] = t["name:en"]
        if a.group:
            p["group"] = a.group
        places.append(p)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(places, f, ensure_ascii=False, indent=1)
    print(json.dumps({"elements": len(d["elements"]), "places": len(places), "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
