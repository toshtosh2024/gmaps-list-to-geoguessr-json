---
name: gmaps-list-to-geoguessr-json
description: Googleマップの保存リスト／ブックマーク（maps.app.goo.gl の共有リンクや placelists URL）から、各ピンの最寄りストリートビューを1つずつ取得して GeoGuessr 用のロケーションJSON（map-generator / map-making.app 形式の customCoordinates）を作る。「このブックマークからJSON作って」「保存した場所をGeoGuessrのマップにしたい」「map-making.app に入れるJSON」「map-generator 形式で」「panoId 付きのロケーション」など、Googleマップのリストや地点群を GeoGuessr / map-making.app / map-generator に取り込みたい依頼では、明示的にスキル名が出なくても必ずこのスキルを使う。
---

# Googleマップ保存リスト → GeoGuessr ロケーションJSON

Googleマップの保存リストにある各地点について、最寄りのストリートビュー（panoId）を1つずつ探し、次の2つのツールでそのまま読める JSON を作る。

- map-generator（https://map-g3nerator.vercel.app/）: 書き出し形式が `{"customCoordinates":[...]}`。読み込むときに `panoId`・`lat`・`lng` が必須。
- map-making.app（https://map-making.app/manual/userscript.html）: 「Import JSON」で同じ形式を読める。`extra.tags` はタグとして表示される。

## 手順

1. ユーザーのリンク（短縮リンク `maps.app.goo.gl/...`、`google.com/maps/placelists/list/<ID>`、またはリストID）を確認する。
2. 同梱スクリプトを実行する。ブラウザは不要で、公開・共有されたリストなら認証なしで読める。

   ```bash
   python3 <このスキルのディレクトリ>/scripts/list_to_json.py "<リンク>" -o <作業ディレクトリ>/<リスト名>.json
   ```

   オプション:
   - `--include-unofficial`: 公式ストリートビューがない場所で、ユーザー投稿のフォトスフィアも使う。既定は公式のみ。GeoGuessr では非公式画像が嫌われることが多いので、ユーザーが望んだときだけ付ける。
   - `--radii 50,200,1000,5000,20000`: 検索半径（m）を小さい順に試す。「近くだけ」なら `50,200` のように絞る。
   - `--no-heading`: 既定では heading を元のピンの方向に向ける（地点が画面に入るように）。不要なら付ける。

   数百件で1〜2分かかる。
3. スクリプトが出力する要約（JSON）を読んでユーザーに報告する。

## 出力

- `<名前>.json`: `{"customCoordinates":[{lat, lng, panoId, heading, pitch, zoom, imageDate, extra:{tags:[地点名], place:{元ピン座標}, searchRadius}}]}`
- `<名前>_missing.json`: ストリートビューが見つからなかった地点（ある場合のみ）

## 報告のしかた

ユーザーが知りたいのは「どれだけ取れたか」と「信用できない点はどこか」なので、次を短くまとめる。

- リスト名と総件数、JSONに入った件数、見つからなかった件数
- 見つからなかった地点の傾向（中国・イラン・南極など、公式ストリートビューがない地域がほとんど）と代表的な名前
- 半径 5km 以上で拾った件数。元の地点からかなり離れた道路になっている可能性がある。`extra.searchRadius` で絞り込めることも伝える。
- 必要なら `--include-unofficial` で取り直せること

## うまくいかないとき

- リストIDが取れない、または 0 件になる: リストが非公開のことが多い。Googleマップでリストを「共有」→リンクを知っている全員に公開してもらう。
- 取得件数が総件数より少ない: 1回で読めるのは 5000 件まで。それを超えるリストは想定していない。
- Google の内部エンドポイント（`entitylist/getlist`、`GeoPhotoService.SingleImageSearch`）を使っているので、仕様が変わると壊れることがある。その場合はレスポンスの生データを見て、スクリプト内のインデックス（リスト項目の `it[1][5]` が座標、パノラマの `x[1][1]` が panoId）を直す。
