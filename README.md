# ISO/IEC 27001:2022 資訊安全保證｜動畫教學簡報

控制屬性「運作能力：Information security assurance（資訊安全保證）」三個控制措施的動畫課程，
以 **ISMS作業重點／稽核查核重點／常見的缺失** 三個面向講解，並搭配管理實務案例。

| 控制 | 名稱 |
|---|---|
| 5.35 | 資訊安全之獨立審查（合宜性・適切性・有效性） |
| 5.36 | 資訊安全政策、規則及標準之遵循性 |
| 8.29 | 開發及驗收中之安全測試 |

- 講師：Q版 Allan Lo（台灣男聲 `zh-TW-YunJheNeural`）
- 助教：阿拉蕾（台灣女聲 `zh-TW-HsiaoYuNeural` 調高音）
- 角色造型取自 `assets/source/` 的角色設定圖，由 `tools/make_sprites.py` 裁切去背成 `assets/*.webp`，
  播放器在立繪上疊加眨眼與依旁白音量開合的嘴型
- 長度：約 11.5 分鐘，16 個段落（開場、全景圖、各控制的作業／稽核／案例／缺失、總整理、隨堂測驗、結語）

## 成品

| 檔案 | 用途 |
|---|---|
| `output/資訊安全保證_動畫簡報.mp4` | 1080p 影片，可直接上課播放或上傳平台 |
| `index.html` | 互動播放器（單一檔案，含旁白），可跳段落、調速度；開啟 GitHub Pages 即可線上播放 |

## 修改內容

所有台詞與畫面文字都在 `content/scenes.py`。每個畫面元素的 `at` 指定它在第幾句台詞出現，
改完重新建置即可，語音與動畫會自動對齊。

```bash
pip install edge-tts
python3 tools/make_sprites.py                # 更換角色設定圖後重新裁切立繪
python3 tools/build.py                       # 產生語音、時間軸、index.html 播放器
NODE_PATH=/opt/node-tools/node_modules \
  node tools/render_video.mjs 20 3 1920      # 渲染 MP4（fps、平行數、寬度）
node tools/snap.mjs <資料夾> end              # 擷取每段結尾畫面檢查版面
```

> 旁白為 AI 語音合成；案例為教學改編情境，非指特定組織。
