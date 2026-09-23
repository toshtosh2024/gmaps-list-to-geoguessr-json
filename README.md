# gmaps-list-to-geoguessr-json

Claude Code スキル。Googleマップの保存リスト（共有リンク）から、各ピンの最寄りストリートビューを1つずつ取得し、
[map-generator](https://map-g3nerator.vercel.app/) / [map-making.app](https://map-making.app/) で読み込める
`{"customCoordinates":[...]}` 形式の JSON を作ります。

## インストール

```bash
git clone https://github.com/toshtosh2024/gmaps-list-to-geoguessr-json ~/.claude/skills/gmaps-list-to-geoguessr-json
```

## スクリプト単体で使う

```bash
python3 scripts/list_to_json.py "https://maps.app.goo.gl/xxxx" -o locations.json [--include-unofficial] [--radii 50,200,1000]
```

詳細は [SKILL.md](SKILL.md) を参照。
