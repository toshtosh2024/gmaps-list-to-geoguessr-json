"""ストリートビュー検索・幾何計算・HTTP の共通処理。"""
import json, math, time, urllib.parse, urllib.request

UA = "geoguessr-map-builder/1.0 (personal use)"


def http(url, data=None, headers=None, timeout=60, retries=4, backoff=10):
    """GET/POST。失敗したら backoff 秒ずつ延ばしながらリトライする（Wikidata/Overpass は頻繁に 429/5xx を返す）。"""
    h = {"User-Agent": UA, **(headers or {})}
    body = urllib.parse.urlencode(data).encode() if isinstance(data, dict) else data
    last = None
    for i in range(retries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, data=body, headers=h), timeout=timeout).read()
        except Exception as e:
            last = e
            time.sleep(backoff * (i + 1))
    raise RuntimeError(f"request failed: {url[:120]} ({last})")


def _sv_url(lat, lng, r, unofficial):
    # 1e2 = 公式ストリートビュー。unofficial なら 1e3/1e10（ユーザー投稿フォトスフィア）も含める
    types = "!1m3!1e2!2b1!3e2" + ("!1m3!1e3!2b1!3e2!1m3!1e10!2b1!3e2" if unofficial else "")
    n = 12 if unofficial else 4
    return ("https://maps.googleapis.com/maps/api/js/GeoPhotoService.SingleImageSearch?pb="
            f"!1m5!1sapiv3!5sUS!11m2!1m1!1b0!2m4!1m2!3d{lat}!4d{lng}!2d{r}"
            f"!3m{6 + n}!2m2!1sen!2sUS!9m1!1e2!11m{n}{types}"
            "!4m6!1e1!1e2!1e3!1e4!1e8!1e6&callback=_cb")


def nearest_pano(lat, lng, r, unofficial=False):
    """(lat,lng) から半径 r m 以内で最寄りのパノラマ。(panoId, lat, lng, 'YYYY-MM'|None) か None。
    注意: 返る点が r を超えることがある（実測で数km）ので、距離は呼び出し側で必ず再チェックする。"""
    for _ in range(3):
        try:
            s = http(_sv_url(lat, lng, r, unofficial), timeout=20, retries=1).decode()
            break
        except Exception:
            time.sleep(1)
    else:
        return None
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


def verify(pano_id, lat, lng, unofficial=False):
    """パノラマ座標で再検索して同じ panoId が返るか。返らないものは実在が怪しいので捨てる。"""
    return any((x := nearest_pano(lat, lng, r, unofficial)) and x[0] == pano_id for r in (5, 15, 30))


def dist(lat1, lng1, lat2, lng2):
    """近距離用の平面近似（m）。"""
    return math.hypot(lat2 - lat1, (lng2 - lng1) * math.cos(math.radians((lat1 + lat2) / 2))) * 111320


def bearing(lat1, lng1, lat2, lng2):
    a, b, c, d = map(math.radians, (lat1, lng1, lat2, lng2))
    y = math.sin(d - b) * math.cos(c)
    x = math.cos(a) * math.sin(c) - math.sin(a) * math.cos(c) * math.cos(d - b)
    return round((math.degrees(math.atan2(y, x)) + 360) % 360, 2)


def random_point(lat, lng, radius, rng):
    """中心から半径 radius m の円内に一様分布する点。"""
    rr = radius * math.sqrt(rng.random())
    t = rng.uniform(0, 2 * math.pi)
    return lat + rr * math.cos(t) / 111320, lng + rr * math.sin(t) / (111320 * math.cos(math.radians(lat)))
