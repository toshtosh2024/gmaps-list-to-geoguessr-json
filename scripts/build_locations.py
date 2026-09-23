#!/usr/bin/env python3
"""地点一覧（places.json）から、各地点の周囲の公式ストリートビューを集めて GeoGuessr 用 JSON を作る。

places.json: [{"name": "東京大学", "name_en": "University of Tokyo", "lat": 35.71, "lng": 139.76,
               "count": 4, "group": "top100"}, ...]   # name_en/count/group は任意
  CSV（name,lat,lng[,name_en,count,group] ヘッダ付き）も可。

出力: {"customCoordinates": [{lat, lng, panoId, heading, pitch, zoom, imageDate,
        extra: {tags: [name, name_en], place: {lat, lng}, distance_m, group}}]}
  → map-generator (https://map-g3nerator.vercel.app/) と map-making.app の Import JSON でそのまま読める。

例:
  # ブックマーク式: 1地点1か所、見つかるまで半径を広げる
  build_locations.py places.json -o out.json
  # 半径500m厳守で1地点3か所、実在確認つき、既存ファイルに追記
  build_locations.py places.json -o out.json --count 3 --radius 500 --strict --verify --merge out.json
  （--merge では同じ name の既存点を目標数に含め、足りない分だけ足す。新しい地点は丸ごと追加）
"""
import argparse, concurrent.futures as cf, csv, json, os, random, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sv


def load_places(path):
    if path.endswith(".csv"):
        with open(path, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        return [{**r, "lat": float(r["lat"]), "lng": float(r["lng"]),
                 **({"count": int(r["count"])} if r.get("count") else {})} for r in rows]
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("places")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--count", type=int, default=1, help="1地点あたりの目標数（places の count が優先）")
    ap.add_argument("--radius", type=int, default=500, help="2か所目以降を探す円の半径 m")
    ap.add_argument("--first-radii", default="50,200,1000,5000,20000",
                    help="1か所目（中心の最寄り）を探す半径。--strict のときは --radius 以下のものだけ使う")
    ap.add_argument("--strict", action="store_true", help="中心から --radius を超える点は一切採用しない")
    ap.add_argument("--spacing", type=int, default=60, help="同じ地点内の点どうしの最小間隔 m")
    ap.add_argument("--verify", action="store_true", help="採用前に再検索で panoId の実在を確認する")
    ap.add_argument("--include-unofficial", action="store_true", help="ユーザー投稿フォトスフィアも許可")
    ap.add_argument("--merge", help="既存の出力JSON。中身を残し、同名地点は目標数まで補充、新しい地点は追加（panoId 重複なし）")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    places = load_places(a.places)
    first_radii = [int(r) for r in a.first_radii.split(",")]
    if a.strict:
        first_radii = [r for r in first_radii if r < a.radius] + [a.radius]
    existing = []
    if a.merge and os.path.exists(a.merge):
        with open(a.merge, encoding="utf-8") as f:
            existing = json.load(f)["customCoordinates"]
    used = {p["panoId"] for p in existing}
    by_name = {}
    for q in existing:  # 既存分は同じ地点名の目標数に含め、足りない分だけ補充する
        by_name.setdefault(q["extra"]["tags"][0], []).append(q)
    uo = a.include_unofficial

    def accept(p, pid, la, ln, pts):
        d = sv.dist(la, ln, p["lat"], p["lng"])
        if pid in used or any(q["panoId"] == pid for q in pts):
            return None
        if a.strict and d > a.radius:
            return None
        if any(sv.dist(la, ln, q["lat"], q["lng"]) < a.spacing for q in pts):
            return None
        if a.verify and not sv.verify(pid, la, ln, uo):
            return None
        return d

    def work(i_p):
        i, p = i_p
        rng = random.Random(a.seed * 100003 + i)
        target = int(p.get("count") or a.count)
        have = by_name.get(p["name"], [])
        pts = [{"panoId": q["panoId"], "lat": q["lat"], "lng": q["lng"], "old": True} for q in have]
        # 1か所目: 中心の最寄り。カメラは地点の方向へ向ける
        for r in (first_radii if not pts else []):
            x = sv.nearest_pano(p["lat"], p["lng"], r, uo)
            if x and (d := accept(p, x[0], x[1], x[2], pts)) is not None:
                pts.append({"panoId": x[0], "lat": x[1], "lng": x[2], "date": x[3], "d": d,
                            "heading": sv.bearing(x[1], x[2], p["lat"], p["lng"]), "r": r})
                break
        # 2か所目以降: 円内のランダム点から最寄りを拾う。カメラはランダム
        tries = 0
        while len(pts) < target and tries < 40 * target:
            tries += 1
            la0, ln0 = sv.random_point(p["lat"], p["lng"], a.radius, rng)
            x = sv.nearest_pano(la0, ln0, 60, uo)
            if x and (d := accept(p, x[0], x[1], x[2], pts)) is not None:
                pts.append({"panoId": x[0], "lat": x[1], "lng": x[2], "date": x[3], "d": d,
                            "heading": round(rng.uniform(0, 360), 2), "r": a.radius})
        return p, target, pts

    with cf.ThreadPoolExecutor(a.workers) as ex:
        results = list(ex.map(work, enumerate(places)))

    new, missing, short = [], [], []
    for p, target, pts in results:
        if not pts:
            missing.append(p)
        elif len(pts) < target:
            short.append((p["name"], len(pts)))
        for q in pts:
            if q.get("old") or q["panoId"] in used:  # 既存分と、別スレッドで拾った重複は出さない
                continue
            used.add(q["panoId"])
            tags = [p["name"]] + ([p["name_en"]] if p.get("name_en") and p["name_en"] != p["name"] else [])
            loc = {"lat": q["lat"], "lng": q["lng"], "panoId": q["panoId"], "heading": q["heading"],
                   "pitch": 0, "zoom": 0}
            if q["date"]:
                loc["imageDate"] = q["date"]
            loc["extra"] = {"tags": tags, "place": {"lat": p["lat"], "lng": p["lng"]},
                            "distance_m": round(q["d"]), "searchRadius": q["r"]}
            if p.get("group"):
                loc["extra"]["group"] = p["group"]
            new.append(loc)

    allp = existing + new
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump({"customCoordinates": allp}, f, ensure_ascii=False, indent=1)
    miss_path = None
    if missing:
        miss_path = a.out[:-5] + "_missing.json" if a.out.endswith(".json") else a.out + "_missing.json"
        with open(miss_path, "w", encoding="utf-8") as f:
            json.dump(missing, f, ensure_ascii=False, indent=1)
    ds = [l["extra"]["distance_m"] for l in new]
    print(json.dumps({
        "places": len(places), "places_with_sv": len(places) - len(missing), "new_locations": len(new),
        "total_locations": len(allp), "existing_kept": len(existing),
        "distance_m": {"max": max(ds) if ds else None,
                       "<=50": sum(d <= 50 for d in ds), "<=200": sum(d <= 200 for d in ds),
                       "<=1000": sum(d <= 1000 for d in ds), ">1000": sum(d > 1000 for d in ds)},
        "per_place_counts": dict(sorted(Counter(len(r[2]) for r in results).items())),
        "short_of_target": short, "missing_names": [m["name"] for m in missing],
        "out": a.out, "missing_out": miss_path}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
