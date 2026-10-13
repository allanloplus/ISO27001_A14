#!/usr/bin/env python3
"""
從使用者提供的角色設定圖裁出全身立繪，去除白色背景，輸出 assets/*.webp
  - assets/source/allan_sheet.jpg ：Allan Lo 講師角色設定（正面單張）
  - assets/source/arale_sheet.jpg ：阿拉蕾助教角色設定（左下全身揮手）
用法：python3 tools/make_sprites.py
"""
import os
from collections import deque
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "assets")

SPRITES = {
    # name: (source, crop box in source pixels)
    "allan": ("allan_sheet.jpg", (40, 80, 768, 1460)),
    "arale": ("arale_sheet.jpg", (60, 790, 425, 1480)),
}


def is_bg(p, thr):
    r, g, b = p[:3]
    return min(r, g, b) >= thr and max(r, g, b) - min(r, g, b) < 28


def cutout(img):
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()
    bg = bytearray(w * h)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            q.append((x, y))
    # flood fill near-white background from the border
    while q:
        x, y = q.popleft()
        i = y * w + x
        if bg[i] or not is_bg(px[x, y], 228):
            continue
        bg[i] = 1
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not bg[ny * w + nx]:
                q.append((nx, ny))
    # soften the anti-aliased fringe next to the background
    for y in range(h):
        for x in range(w):
            i = y * w + x
            if bg[i]:
                continue
            near = any(0 <= x + dx < w and 0 <= y + dy < h and bg[(y + dy) * w + x + dx]
                       for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if near:
                r, g, b, _ = px[x, y]
                lum = min(r, g, b)
                if lum > 150:
                    px[x, y] = (r, g, b, max(0, min(255, int((255 - lum) * 255 / 105))))
    # keep only the largest connected figure (drops stray bits of neighbouring drawings)
    seen = bytearray(w * h)
    best = []
    for sy in range(h):
        for sx in range(w):
            i = sy * w + sx
            if bg[i] or seen[i]:
                continue
            comp, q = [], deque([(sx, sy)])
            seen[i] = 1
            while q:
                x, y = q.popleft()
                comp.append((x, y))
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < w and 0 <= ny < h:
                        j = ny * w + nx
                        if not bg[j] and not seen[j]:
                            seen[j] = 1
                            q.append((nx, ny))
            if len(comp) > len(best):
                best = comp
    keep = bytearray(w * h)
    for x, y in best:
        keep[y * w + x] = 1
    for y in range(h):
        for x in range(w):
            if bg[y * w + x] or not keep[y * w + x]:
                px[x, y] = (255, 255, 255, 0)
    return img.crop(img.getbbox())


def main():
    for name, (src, box) in SPRITES.items():
        im = Image.open(os.path.join(A, "source", src)).crop(box)
        out = cutout(im)
        path = os.path.join(A, f"{name}.webp")
        out.save(path, "WEBP", quality=90, method=6)
        print(name, out.size, os.path.getsize(path) // 1024, "KB")


if __name__ == "__main__":
    main()
