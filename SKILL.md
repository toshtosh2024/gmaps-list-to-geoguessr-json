---
name: gmaps-list-to-geoguessr-json
description: GeoGuessr 用のロケーションJSON（map-generator / map-making.app で読める customCoordinates 形式、panoId 付き）を作る。入力は Googleマップの保存リスト（maps.app.goo.gl の共有リンク）、大学名・観光地名などの名前リストやCSV、「日本のスキー場」「世界の有名大学」のようなテーマ指定のどれでもよい。各地点の周囲にある公式ストリートビューを1か所または複数か所ずつ取り、実在確認や半径制限もできる。「〜でマップ作って」「GeoGuessr のマップにしたい」「map-making.app に入れるJSON」「このブックマークからJSON」「地点を増やして」など、地点群を GeoGuessr / map-making.app / map-generator 用にしたい依頼では、スキル名が出なくても必ずこのスキルを使う。
---

# GeoGuessr ロケーションJSON作成

どこからでも「地点一覧」を作り、各地点の周囲にある公式ストリートビュー（panoId）を集めて JSON にする。
出力は次の2つのツールでそのまま読める。

- map-generator（https://map-g3nerator.vercel.app/）: 読み込むときに `customCoordinates[].panoId/lat/lng` が必須。
- map-making.app（https://map-making.app/manual/userscript.html）: 「Import JSON」で読める。`extra.tags` はタグとして表示される。

作業は **① 地点一覧（places.json）を作る → ② ストリートビューを集める → ③ 報告** の3段階。
①は入力の種類ごとにやり方を変え、②は共通の `build_locations.py` を使う。
スクリプトは `<このスキル>/scripts/` にあり、出力ファイルはユーザーの作業ディレクトリに置く。
途中のファイルはスクラッチパッドに置く。

## ① 地点一覧を作る

places.json の形式: `[{"name": 表示名, "name_en": 任意, "lat": .., "lng": .., "count": 任意, "group": 任意}]`
（`name,lat,lng` 列を持つ CSV でもよい）

| 入力 | 方法 |
|---|---|
| Googleマップの保存リスト | `gmaps_list.py "<リンク>" -o places.json` |
| 名前のリスト（大学名、観光地、都市など）、テキストやCSV | `wikidata_places.py names.txt -o places.json`（CSV なら `--column 列名`。`日本語 / English` 形式の行は英語で検索し、日本語を表示名にする） |
| カテゴリ（スキー場、城、灯台など）、国単位 | `osm_places.py 'landuse=winter_sports' --country JP -o places.json --named-only` |
| 「世界の有名な〇〇」などテーマだけ | 自分で名前リストを作り（ランキングや知識から）、`wikidata_places.py` で座標を引く。数が要るときは Wikidata の記事言語数で並べる方法がある → `references/recipes.md` |
| 座標が既にある | places.json を直接書く |

**名前検索の結果は必ず目で確認する。** `wikidata_places.py` は採用した候補の説明文と、ほかの候補を `review |` 行に出す。
同名の別物（例: Northeastern University は米国ボストンと中国瀋陽）、旧組織（KU Leuven が 1834–1968 年の旧大学）、附属病院などを拾うことがある。
説明文や国がおかしければ `--pick "検索語=QID"` で指定し直すか、座標を直す。
直した座標が Wikidata 由来でないとき（自分の知識で直したとき）は、報告でそう伝える。

ユーザーの手元にあるリスト（CSVなど）と照合するときは、表記揺れ（The の有無、略称、`/` 区切りの日英併記、Sciences Po = Paris Institute of Political Studies のような別名）を考えて突き合わせる。
あいまい一致の結果は信用せず、1件ずつ確認する（Victoria と Virginia、Northeastern と Northwestern が一致判定になった例がある）。

## ② ストリートビューを集める

```bash
python3 <スキル>/scripts/build_locations.py places.json -o <出力>.json [オプション]
```

依頼の内容に合わせてオプションを選ぶ。

- **ブックマーク式（1地点1か所、なるべく漏らさない）**: オプションなし。中心の最寄りを 50m → 200m → 1km → 5km → 20km と広げて探す。
- **「半径◯m以内なら何でもいい」「地点を増やして」**: `--count N --radius R --strict`。1か所目は中心の最寄り（カメラは地点の方向）、2か所目以降は半径R内のランダムな点から拾う（カメラはランダム）。`--strict` を付けると、中心からR mを超える点は1つも入らない。
  - 全体の数を指定されたら、`count` を地点ごとに割り振る（例: 1000か所 ÷ 300地点 → 上位は4か所、残りは3か所、を places.json の `count` に入れる）。
- **「ストリートビューが確実にあるように」**: `--verify` を付ける。取った座標で再検索し、同じ panoId が返るものだけを採用する。報告に「実在確認済み」と書くなら必ず付ける。
- **既存のJSONに足す、または一部を取り直す**: `--merge 既存.json`。同じ名前の地点は目標数に足りない分だけ補充し、新しい地点は丸ごと追加する。panoId は重複しない。
- **非公式のフォトスフィアも使う**: `--include-unofficial`。GeoGuessr では嫌われることが多いので、ユーザーが望んだときだけ付ける。

`--strict` 使用時に中心付近で見つからない地点は `_missing.json` に出る。
広いキャンパスや山の中など、中心点が道路から遠いだけのこともある。
その場合は、同じ施設内の別の座標（学部棟、ゲート、駅など、Wikidata などで確かめられるもの）を中心にして取り直すとよい。

実行時間の目安: 1地点1か所なら数百地点で1〜2分。`--verify` と複数か所を付けると 300地点×3か所で数分。

## ③ 報告

ユーザーが知りたいのは「何か所取れたか」と「信用できない点はどこか」。スクリプトが出す要約をもとに、次を短くまとめる。

- 地点数、出力件数、1地点あたりの件数の内訳、距離の分布（最大距離、1km超の件数）
- 見つからなかった地点と、その理由の傾向。中国本土・イラン・キューバ・北朝鮮・南極などは公式ストリートビューがほぼない。
- 人の判断が入ったところ。自分で選んだ大学や名前、手で直した座標、同名の別物を除いたことなど。
- `extra` のどのフィールドで絞り込めるか（`group`、`distance_m`、`searchRadius`、`tags`）

## うまくいかないとき

- **Googleマップのリストが 0 件になる**: 非公開のリストのことが多い。共有リンクを「リンクを知っている全員」にしてもらう。1回で読めるのは 5000 件まで。
- **Wikidata が 429 / 503 / DBConnectionError を返す**: 混雑。スクリプトは逐次実行とリトライで対処している。座標は SPARQL でまとめて取る（wbgetentities が落ちていても SPARQL は動くことが多い）。SPARQL が 504 になるときは、ラベルの文字列一致のような重いクエリを避け、QID の VALUES で引く。
- **Overpass が 406 または runtime error を返す**: User-Agent を付けていないか、本家サーバーの障害。`osm_places.py` はミラー（maps.mail.ru など）を順に試す。
- **ストリートビュー検索の半径指定が守られない**: 指定した半径より数km遠い点が返ることがある。`--strict` を付ければ距離を必ず再チェックする。
- **Google の内部エンドポイントの仕様変更**: `entitylist/getlist` と `GeoPhotoService.SingleImageSearch` を使っているので、仕様が変わると壊れる。レスポンスの生データを見て、`sv.py` / `gmaps_list.py` の配列インデックスを直す。
