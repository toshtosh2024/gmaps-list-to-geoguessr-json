# gmaps-list-to-geoguessr-json

GeoGuessr 用のロケーションJSONを作る Claude Code スキルです。
地点一覧（Googleマップの保存リスト、名前のリスト、OpenStreetMap のカテゴリなど）から、各地点の周囲にある公式ストリートビューを集めます。
出力は [map-generator](https://map-g3nerator.vercel.app/) と [map-making.app](https://map-making.app/) でそのまま読める `{"customCoordinates":[...]}` 形式です。

## インストール

```bash
git clone https://github.com/toshtosh2024/gmaps-list-to-geoguessr-json ~/.claude/skills/gmaps-list-to-geoguessr-json
```

## スクリプト単体で使う

```bash
S=~/.claude/skills/gmaps-list-to-geoguessr-json/scripts

# ① 地点一覧を作る（どれか1つ）
python3 $S/gmaps_list.py "https://maps.app.goo.gl/xxxx" -o places.json             # Googleマップの保存リスト
python3 $S/wikidata_places.py names.txt -o places.json                             # 名前のリスト → Wikidata で座標
python3 $S/osm_places.py 'landuse=winter_sports' --country JP -o places.json --named-only   # OSM のカテゴリ

# ② ストリートビューを集める
python3 $S/build_locations.py places.json -o map.json                                # 1地点1か所（見つかるまで半径を広げる）
python3 $S/build_locations.py places.json -o map.json --count 3 --radius 500 --strict --verify   # 半径500m以内で3か所、実在確認つき
python3 $S/build_locations.py more.json -o map.json --merge map.json ...           # 既存のJSONに追記・補充
```

| スクリプト | 役割 |
|---|---|
| `sv.py` | ストリートビュー検索、実在確認、距離・方位の計算、リトライ付きの HTTP |
| `build_locations.py` | places.json から GeoGuessr 用 JSON を作る |
| `gmaps_list.py` / `wikidata_places.py` / `osm_places.py` | 入力の種類ごとに places.json を作る |

詳しくは [SKILL.md](SKILL.md) と [references/recipes.md](references/recipes.md) を参照してください。
