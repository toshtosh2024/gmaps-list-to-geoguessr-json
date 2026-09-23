#!/usr/bin/env python3
"""Googleマップの保存リスト（共有リンク / placelists URL / リストID）→ places.json

  gmaps_list.py "https://maps.app.goo.gl/xxxx" -o places.json
"""
import argparse, json, os, re, sys, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sv


def resolve_list_id(arg):
    if not arg.startswith("http"):
        return arg
    url = arg
    if "goo.gl" in url:
        url = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).geturl()
    url = urllib.parse.unquote(url)
    m = re.search(r"placelists/list/([A-Za-z0-9_-]+)", url) or re.search(r"!2s([A-Za-z0-9_-]{20,})", url)
    if not m:
        sys.exit(f"リストIDを見つけられませんでした: {url}")
    return m.group(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("link")
    ap.add_argument("-o", "--out", default="places.json")
    a = ap.parse_args()
    list_id = resolve_list_id(a.link)
    pb = f"!1m4!1s{list_id}!2e1!3m1!1e1!2e2!3e2!4i5000!16b1"  # 4i5000 = 最大取得件数
    raw = sv.http("https://www.google.com/maps/preview/entitylist/getlist?authuser=0&hl=ja&gl=jp&pb="
                  + urllib.parse.quote(pb)).decode("utf-8")
    head = json.loads(raw[raw.index("\n") + 1:])[0]  # 先頭の )]}' を除去
    places = []
    for it in head[8] or []:
        try:
            c = it[1][5]
            places.append({"name": it[2] or it[1][4] or "", "lat": c[2], "lng": c[3]})
        except (TypeError, IndexError):
            continue  # 座標のない項目（メモだけ等）
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(places, f, ensure_ascii=False, indent=1)
    print(json.dumps({"list_title": head[4], "list_total": head[12], "places": len(places), "out": a.out},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
