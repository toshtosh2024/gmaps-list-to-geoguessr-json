#!/usr/bin/env python3
"""名前の一覧 → Wikidata で座標を引いて places.json（大学・観光地・都市など固有名詞のリスト向け）

入力: 1行1件のテキスト、または CSV（--column で列指定）。"日本語名 / English name" 形式の行は
      "/" の右側（英語）で検索し、左側を表示名に使う。
  wikidata_places.py names.txt -o places.json
  wikidata_places.py 協定校.csv --column 大学名 -o places.json

検索は英語ラベルで wbsearchentities（上位7件）→ 座標(P625)を持つ最初の候補を採用。
同名の別物を拾うことがあるので、出力の review 行（採用候補の説明文と他候補）を必ず目で確認し、
間違っていれば places.json の lat/lng を直す（--pick で QID 指定も可）。
"""
import argparse, csv, json, os, re, sys, time, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sv

API = "https://www.wikidata.org/w/api.php?format=json&"
SPARQL = "https://query.wikidata.org/sparql"


def read_names(path, column):
    if path.endswith(".csv"):
        with open(path, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        col = column or list(rows[0].keys())[0]
        vals = [r[col].strip() for r in rows if r.get(col, "").strip()]
    else:
        with open(path, encoding="utf-8") as f:
            vals = [l.strip() for l in f if l.strip()]
    out, seen = [], set()
    for v in vals:
        parts = [p.strip() for p in v.split("/")]
        disp, query = parts[0], parts[-1]
        query = re.sub(r"[（(].*?[)）]", "", query).strip()  # "(UBC)" などの略称を落とす
        if query in seen:
            continue
        seen.add(query)
        out.append({"display": disp, "query": query})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("-o", "--out", default="places.json")
    ap.add_argument("--column")
    ap.add_argument("--lang", default="en", help="検索言語")
    ap.add_argument("--pick", action="append", default=[], help="'検索語=QID' で候補を強制指定")
    ap.add_argument("--group")
    a = ap.parse_args()
    picks = dict(p.split("=", 1) for p in a.pick)
    names = read_names(a.input, a.column)

    cands = {}
    for n in names:  # 検索は逐次＋間隔を空ける（並列にすると 429/503 になる）
        q = n["query"]
        if q in picks:
            cands[q] = [{"id": picks[q]}]
            continue
        r = json.loads(sv.http(API + "action=wbsearchentities&limit=7&language=" + a.lang
                               + "&search=" + urllib.parse.quote(q)))
        cands[q] = r.get("search", [])
        time.sleep(1.2)

    # 座標・ラベルは SPARQL で一括取得（wbgetentities は DB エラーで落ちることがあった）
    ids = sorted({c["id"] for v in cands.values() for c in v if c["id"].startswith("Q")})
    ents = {}
    for i in range(0, len(ids), 150):
        query = """SELECT ?item ?coord ?en ?ja ?desc WHERE { VALUES ?item { %s } ?item wdt:P625 ?coord .
          OPTIONAL{?item rdfs:label ?en FILTER(lang(?en)="en")} OPTIONAL{?item rdfs:label ?ja FILTER(lang(?ja)="ja")}
          OPTIONAL{?item schema:description ?desc FILTER(lang(?desc)="en")} }""" % " ".join("wd:" + x for x in ids[i:i + 150])
        d = json.loads(sv.http(SPARQL, data={"query": query}, headers={"Accept": "application/sparql-results+json"},
                               timeout=120, backoff=15))
        for b in d["results"]["bindings"]:
            qid = b["item"]["value"].rsplit("/", 1)[1]
            if qid in ents:
                continue
            lng, lat = map(float, b["coord"]["value"][6:-1].split())
            ents[qid] = {"lat": lat, "lng": lng, "en": b.get("en", {}).get("value"),
                         "ja": b.get("ja", {}).get("value"), "desc": b.get("desc", {}).get("value")}

    places, missing = [], []
    for n in names:
        hit = [c["id"] for c in cands[n["query"]] if c["id"] in ents]
        if not hit:
            missing.append(n["query"])
            continue
        e = ents[hit[0]]
        disp = n["display"] if n["display"] != n["query"] else (e["ja"] or e["en"] or n["query"])
        p = {"name": disp, "name_en": e["en"] or n["query"], "lat": e["lat"], "lng": e["lng"], "qid": hit[0]}
        if a.group:
            p["group"] = a.group
        places.append(p)
        others = "; ".join(f"{q}:{ents[q]['en']}" for q in hit[1:4])
        print(f"review | {n['query']} -> {hit[0]} {e['en']} | {e['desc']} | ({e['lat']:.4f},{e['lng']:.4f})"
              + (f" | 他候補: {others}" if others else ""))
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(places, f, ensure_ascii=False, indent=1)
    print(json.dumps({"names": len(names), "places": len(places), "not_found": missing, "out": a.out},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
