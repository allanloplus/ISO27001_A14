#!/usr/bin/env python3
"""
建置流程：
  1. 以 edge-tts 為每句台詞產生語音（Allan：台灣男聲；阿拉蕾：台灣女聲調高音）
  2. 依語音長度排出時間軸，串接成單一旁白音檔 narration.mp3
  3. 計算音量包絡（嘴型同步用）
  4. 把時間軸與音檔嵌入 src/player.html → output/資訊安全保證_動畫簡報.html

用法：python3 tools/build.py
"""
import asyncio, base64, hashlib, json, os, subprocess, sys, array, math

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "content"))
from scenes import SCENES  # noqa: E402

BUILD = os.path.join(ROOT, "build")
AUDIO = os.path.join(BUILD, "audio")
OUT = os.path.join(ROOT, "output")
os.makedirs(AUDIO, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

VOICES = {
    "A": dict(voice="zh-TW-YunJheNeural", rate="+4%", pitch="+0Hz"),
    "R": dict(voice="zh-TW-HsiaoYuNeural", rate="+10%", pitch="+30Hz"),
}
SR = 24000           # PCM sample rate
ENV_HZ = 25          # mouth envelope frames per second
SCENE_PAD_IN = 0.9   # seconds before first line of a scene
LINE_GAP = 0.45      # seconds between lines
SCENE_PAD_OUT = 1.3  # seconds after last line of a scene


def _patch_ca():
    """edge-tts uses certifi; point it at the environment CA bundle if present."""
    bundle = os.environ.get("SSL_CERT_FILE") or "/root/.ccr/ca-bundle.crt"
    if os.path.exists(bundle):
        import certifi
        certifi.where = lambda: bundle


async def tts_all(jobs):
    import edge_tts
    sem = asyncio.Semaphore(4)

    async def one(text, spk, path):
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return
        v = VOICES[spk]
        async with sem:
            for attempt in range(4):
                try:
                    await edge_tts.Communicate(text, v["voice"], rate=v["rate"], pitch=v["pitch"]).save(path)
                    return
                except Exception as e:  # network hiccup → retry
                    print("  retry", attempt + 1, e)
                    await asyncio.sleep(2 ** attempt)
            raise RuntimeError("TTS failed: " + text)

    await asyncio.gather(*(one(*j) for j in jobs))


def decode_pcm(path):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
        check=True, capture_output=True).stdout
    a = array.array("h")
    a.frombytes(raw)
    return a


def trim_silence(a, thr=300):
    """Trim leading/trailing near-silence so gaps are controlled by the timeline."""
    n = len(a)
    s = 0
    while s < n and abs(a[s]) < thr:
        s += 1
    e = n
    while e > s and abs(a[e - 1]) < thr:
        e -= 1
    s = max(0, s - int(0.03 * SR))
    e = min(n, e + int(0.08 * SR))
    return a[s:e]


def main():
    _patch_ca()
    jobs, line_files = [], []
    for sc in SCENES:
        files = []
        for spk, text in sc["lines"]:
            v = VOICES[spk]
            h = hashlib.sha1(f"{v}|{text}".encode()).hexdigest()[:16]
            p = os.path.join(AUDIO, f"{spk}_{h}.mp3")
            jobs.append((text, spk, p))
            files.append(p)
        line_files.append(files)
    print(f"TTS: {len(jobs)} lines")
    asyncio.run(tts_all(jobs))

    pcm = array.array("h")
    env_spk = []  # (start_sample, end_sample, spk)

    def pad(sec):
        pcm.extend(array.array("h", bytes(2 * int(sec * SR))))

    timeline = []
    for sc, files in zip(SCENES, line_files):
        s_start = len(pcm) / SR
        pad(SCENE_PAD_IN)
        lines = []
        for i, ((spk, text), f) in enumerate(zip(sc["lines"], files)):
            if i:
                pad(LINE_GAP)
            a = trim_silence(decode_pcm(f))
            st = len(pcm) / SR
            pcm.extend(a)
            en = len(pcm) / SR
            lines.append({"spk": spk, "text": text, "t0": round(st, 3), "t1": round(en, 3)})
        pad(SCENE_PAD_OUT)
        s_end = len(pcm) / SR

        def at_time(at):
            if isinstance(at, list):
                idx, frac = at
            else:
                idx, frac = at, 0.0
            ln = lines[idx]
            return round(ln["t0"] + frac * (ln["t1"] - ln["t0"]), 3)

        items = []
        for it in sc.get("items", []):
            it = dict(it)
            it["t"] = at_time(it["at"])
            if "ansAt" in it:
                it["tAns"] = at_time(it["ansAt"])
            del it["at"]
            items.append(it)
        scene = {k: v for k, v in sc.items() if k not in ("lines", "items")}
        scene.update({"t0": round(s_start, 3), "t1": round(s_end, 3), "lines": lines, "items": items})
        timeline.append(scene)

    total = len(pcm) / SR
    print(f"Total duration: {total:.1f}s ({total/60:.1f} min)")

    # mouth envelope: RMS per frame, normalised per speaker, quantised 0..9
    win = SR // ENV_HZ
    nfr = math.ceil(len(pcm) / win)
    rms = []
    for k in range(nfr):
        seg = pcm[k * win:(k + 1) * win]
        if not seg:
            rms.append(0.0)
            continue
        rms.append(math.sqrt(sum(x * x for x in seg) / len(seg)))
    peak = sorted(rms)[int(len(rms) * 0.97)] or 1
    env = "".join(str(min(9, int(9 * min(1.0, (r / peak) ** 0.7)))) for r in rms)

    wav = os.path.join(BUILD, "narration.wav")
    with open(wav, "wb") as fh:
        import wave
        w = wave.open(fh, "wb")
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes()); w.close()
    mp3 = os.path.join(BUILD, "narration.mp3")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-c:a", "libmp3lame", "-b:a", "48k", mp3], check=True)

    data = {"duration": round(total, 3), "envHz": ENV_HZ, "env": env, "scenes": timeline}
    with open(os.path.join(BUILD, "timeline.json"), "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)

    tpl = open(os.path.join(ROOT, "src", "player.html"), encoding="utf-8").read()
    b64 = base64.b64encode(open(mp3, "rb").read()).decode()
    html = (tpl.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False))
               .replace("__AUDIO_SRC__", "data:audio/mpeg;base64," + b64))
    # artifact version: page body only (the host adds the document skeleton)
    open(os.path.join(BUILD, "artifact.html"), "w", encoding="utf-8").write(html)
    # standalone version: open directly in any browser, works offline (fonts fall back)
    head = ('<!doctype html>\n<html lang="zh-Hant">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n</head>\n<body>\n')
    out = os.path.join(ROOT, "index.html")
    open(out, "w", encoding="utf-8").write(head + html + "\n</body>\n</html>\n")
    print("Wrote", out, f"{os.path.getsize(out)/1e6:.1f} MB")


if __name__ == "__main__":
    main()
