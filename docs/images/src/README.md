# 図のソース

`docs/images/` のPNGは、このディレクトリのHTMLをヘッドレスChromeで描画して生成しています。
図を修正するときはHTMLを編集し、次の手順で再生成します。

## 前提

- ヘッドレス描画できるChrome / Chromium
  コマンド名は環境によって異なります（`google-chrome`、`chromium`、Windowsでは`chrome.exe`のフルパスなど）。以下では`chrome`として記載します。
- Python と Pillow（`pip install pillow`）

## 再生成の手順

このディレクトリ（`docs/images/src`）をカレントディレクトリにして実行します。

```bash
# 生成したい図を選ぶ（three-user-layers または system-architecture）
NAME=three-user-layers

# 1. HTMLを2倍解像度でスクリーンショット
#    --window-size の高さは、描画される図の高さより大きくする
#    （足りないと図の下部が切れる）
chrome --headless=new --disable-gpu --hide-scrollbars \
  --force-device-scale-factor=2 --window-size=1120,1200 \
  --screenshot=raw.png "file://$(pwd)/${NAME}.html"

# 2. 余白を切り詰めてPNGとして保存
NAME="$NAME" python - <<'PY'
import os
from PIL import Image, ImageChops
name = os.environ["NAME"]
im = Image.open("raw.png").convert("RGB")
bg = Image.new("RGB", im.size, (255, 255, 255))
l, t, r, b = ImageChops.difference(im, bg).getbbox()
pad = 72
im.crop((l - pad, t - pad, r + pad, b + pad)).save(
    f"../{name}.png", "PNG", optimize=True)
PY

# 3. 中間ファイルを削除
rm raw.png
```

出力先は`NAME`から決まるため、図を取り違えて上書きすることはありません。

## ファイル一覧

| ファイル | 出力先 | 掲載場所 |
| --- | --- | --- |
| `three-user-layers.html` | `../three-user-layers.png` | [01. 基本概念とユーザーの3層](../../01_overview_and_roles.md) |
| `system-architecture.html` | `../system-architecture.png` | [01. 基本概念とユーザーの3層](../../01_overview_and_roles.md) |
