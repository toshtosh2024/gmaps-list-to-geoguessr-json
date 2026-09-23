#!/usr/bin/env python3
"""Googleマップの保存リスト（共有リンク）を GeoGuessr 用ロケーションJSONに変換する。

出力形式は map-generator (https://map-g3nerator.vercel.app/) の書き出し形式
  {"customCoordinates": [{lat, lng, panoId, heading, pitch, zoom, imageDate, extra:{tags:[...]}}]}
で、map-making.app の Import JSON でもそのまま読める。

使い方:
  python3 list_to_json.py <共有リンク or リストID> -o out.json [--radii 50,200,1000,5000,20000]
                          [--include-unofficial] [--no-heading] [--workers 8]
"""
import argparse, concurrent.futures as cf, json, math, re, sys, urllib.parse, urllib.request
from collections import Counter

UA = {"User-Agent": "Mozilla/5.0"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=30)


def resolve_list_id(arg):
    """短縮リンク・placelists URL・生IDのいずれからでもリストIDを取り出す。"""
    if not arg.startswith("http"):
        return arg
    url = arg
    if "goo.gl" in url:
        url = get(url).geturl()  # リダイレクトを追う
    url = urllib.parse.unquote(url)
    m = re.search(r"placelists/list/([A-Za-z0-9_-]+)", url) or re.search(r"!2s([A-Za-z0-9_-]{20,})", url)
    if not m:
        sys.exit(f"リストIDを見つけられませんでした: {url}")
    return m.group(1)


def fetch_list(list_id):
    pb = f"!1m4!1s{list_id}!2e1!3m1!1e1!2e2!3e2!4i5000!16b1"
    url = ("https://www.google.com/maps/preview/entitylist/getlist?authuser=0&hl=ja&gl=jp&pb="
           + urllib.parse.quote(pb))
    raw = get(url).read().decode("utf-8")
    d = json.loads(raw[raw.index("\n") + 1:])  # 先頭の )]}' を除去
    head = d[0]
    title, total = head[4], head[12]
    places = []
    for it in head[8] or []:
        try:
            c = it[1][5]
            places.append({"name": it[2] or it[1][4] or "", "lat": c[2], "lng": c[3]})
        except (TypeError, IndexError):
            continue  # 座標を持たない項目（メモだけ等）は飛ばす
    return title, total, places


def sv_url(lat, lng, r, unofficial):
    # 1e2 = 公式ストリートビュー。unofficial のときは 1e3/1e10（ユーザー投稿フォトスフィア）も含める
    types = "!1m3!1e2!2b1!3e2" + ("!1m3!1e3!2b1!3e2!1m3!1e10!2b1!3e2" if unofficial else "")
    n = 4 if not unofficial else 12
    return ("https://maps.googleapis.com/maps/api/js/GeoPhotoService.SingleImageSearch?pb="
            f"!1m5!1sapiv3!5sUS!11m2!1m1!1b0!2m4!1m2!3d{lat}!4d{lng}!2d{r}"
            f"!3m{6 + n}!2m2!1sen!2sUS!9m1!1e2!11m{n}{types}"
            "!4m6!1e1!1e2!1e3!1e4!1e8!1e6&callback=_cb")


def nearest_pano(lat, lng, r, unofficial):
    s = get(sv_url(lat, lng, r, unofficial)).read().decode()
    j = json.loads(s[s.index("(") + 1:s.rindex(")")])
    if j[0][0] != 0:
        return None
    x = j[1]
    c = x[5][0][1][0]
    date = None
    try:
        dt = x[6][7]
        date = f"{dt[0]}-{dt[1]:02d}"
    except (TypeError, IndexError):
        pass
    return x[1][1], c[2], c[3], date


def bearing(lat1, lng1, lat2, lng2):
    a, b, c, d = map(math.radians, (lat1, lng1, lat2, lng2))
    y = math.sin(d - b) * math.cos(c)
    x = math.cos(a) * math.sin(c) - math.sin(a) * math.cos(c) * math.cos(d - b)
    return round((math.degrees(math.atan2(y, x)) + 360) % 360, 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("link")
    ap.add_argument("-o", "--out", default="locations.json")
    ap.add_argument("--radii", default="50,200,1000,5000,20000", help="検索半径(m)。小さい順に試す")
    ap.add_argument("--include-unofficial", action="store_true", help="ユーザー投稿フォトスフィアも許可")
    ap.add_argument("--no-heading", action="store_true", help="heading を地点方向に向けず 0 にする")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    radii = [int(r) for r in a.radii.split(",")]

    list_id = resolve_list_id(a.link)
    title, total, places = fetch_list(list_id)
    print(f"リスト「{title}」: {total}件（座標あり {len(places)}件）", file=sys.stderr)

    def work(p):
        for r in radii:
            try:
                res = nearest_pano(p["lat"], p["lng"], r, a.include_unofficial)
            except Exception:
                res = None
            if res:
                pid, la, ln, date = res
                loc = {"lat": la, "lng": ln, "panoId": pid,
                       "heading": 0 if a.no_heading else bearing(la, ln, p["lat"], p["lng"]),
                       "pitch": 0, "zoom": 0,
                       "extra": {"tags": [p["name"]], "place": {"lat": p["lat"], "lng": p["lng"]},
                                 "searchRadius": r}}
                if date:
                    loc["imageDate"] = date
                return loc
        return {"_miss": p}

    with cf.ThreadPoolExecutor(a.workers) as ex:
        results = list(ex.map(work, places))
    locs = [r for r in results if "_miss" not in r]
    miss = [r["_miss"] for r in results if "_miss" in r]

    with open(a.out, "w", encoding="utf-8") as f:
        json.dump({"customCoordinates": locs}, f, ensure_ascii=False, indent=1)
    miss_path = re.sub(r"(\.json)?$", "_missing.json", a.out, count=1)
    if miss:
        with open(miss_path, "w", encoding="utf-8") as f:
            json.dump(miss, f, ensure_ascii=False, indent=1)

    summary = {"list_title": title, "list_total": total, "places": len(places), "found": len(locs),
               "missing": len(miss), "by_radius": dict(sorted(Counter(l["extra"]["searchRadius"] for l in locs).items())),
               "missing_names": [m["name"] for m in miss], "out": a.out,
               "missing_out": miss_path if miss else None}
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
