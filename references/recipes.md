# レシピ

## 「有名な〇〇」を数百件集める（Wikidata の記事言語数順）

有名度の目安として、ウィキペディアの記事がある言語数（`wikibase:sitelinks`）で並べる。
下は大学の例。`?cls` を差し替えれば他のジャンルにも使える（城 Q23413、灯台 Q39715、スキー場 Q130003 など）。
クエリ サービスは 502/503 を返すことがあるので、数回リトライする。

```sparql
SELECT ?item ?sl ?coord ?en ?ja ?cc WHERE {
  VALUES ?cls { wd:Q3918 wd:Q875538 wd:Q902104 wd:Q15936437 wd:Q1371037 wd:Q23002054 wd:Q62078547 }
  ?item wdt:P31 ?cls ; wdt:P625 ?coord ; wikibase:sitelinks ?sl .
  FILTER NOT EXISTS { ?item wdt:P576 [] }            # 廃止済みを除く
  OPTIONAL { ?item wdt:P17 ?c . ?c wdt:P297 ?cc }    # 国コード（CN を除外するなどに使う）
  OPTIONAL { ?item rdfs:label ?en FILTER(lang(?en)="en") }
  OPTIONAL { ?item rdfs:label ?ja FILTER(lang(?ja)="ja") }
  FILTER(?sl > 40)
} ORDER BY DESC(?sl) LIMIT 800
```

POST 先は `https://query.wikidata.org/sparql`、ヘッダは `Accept: application/sparql-results+json` と User-Agent。
結果には、遺跡（Nalanda Mahavihara）、博物館、同名で判別できない項目（"Trinity College"）などが混ざるので、目で見て除く。
地域の偏りも出る（ブラジルの州立大学が上位に来るなど）。ユーザーが想定している「有名」とずれそうなら、ランキング上位や知名度の高いものを手で補う。
結果の lat/lng/ja/en から places.json を直接組み立てればよい。

## ランキング上位などを手で選ぶとき

名前を英語で1行ずつ書いて `wikidata_places.py` に渡す。
中国本土の大学のように公式ストリートビューがない地域の候補は、先に除くか、見つからなかったら代わりを足すと伝える。
ユーザーが「香港・台湾で埋めて」のように指定したら、それに従う。

## 1地点1か所のファイルを、多地点のファイルに広げる

既存の出力JSONから places.json を作り直す（`extra.tags[0]` を name、`extra.place` を中心にする）。
そのうえで、次のように実行すると、既存の点を残したまま目標数まで足せる。

```bash
build_locations.py places.json -o out.json --count 4 --radius 500 --strict --verify --merge 既存.json
```

中心から R m を超える既存の点があるときは、先に取り除いてから merge する。
