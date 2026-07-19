"""抓取 B 站视频官方/CC 字幕，转换为本项目字幕 JSON 格式。

用法:
    python scripts/fetch_subtitle.py <BV号> [--cookie "SESSDATA=xxx"]

产出:
    data/miaomiao/subtitles/{BV号}.json
    格式: {"bvid": ..., "title": ..., "subtitles": [{"start": 秒, "end": 秒, "text": ...}]}

说明:
    - 字幕是 Demo 阶段的"策展资产"：离线抓取、随仓库部署，不做在线流水线。
    - 部分视频的字幕接口需要登录态，403/无字幕时用 --cookie 传入 SESSDATA。
    - 无 CC 字幕的视频会报错退出，此时可改用本地 ASR 预案（见 docs/KNOWN-ISSUES.md）。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 允许直接从 server/ 目录运行（无需先 pip install -e .）
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from ewa.config import SUBTITLE_DIR

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com",
}


def _get(client: httpx.Client, url: str, **params) -> dict:
    resp = client.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"B站接口报错 [{data.get('code')}]: {data.get('message')} ({url})")
    return data["data"]


def fetch_subtitle(bvid: str, cookie: str = "") -> dict:
    headers = dict(_HEADERS)
    if cookie:
        headers["Cookie"] = cookie

    with httpx.Client(headers=headers, timeout=15.0, follow_redirects=True) as client:
        # 1. BV → cid（取第一个分 P）
        pages = _get(client, "https://api.bilibili.com/x/player/pagelist", bvid=bvid)
        cid = pages[0]["cid"]

        # 2. 字幕列表
        player = _get(client, "https://api.bilibili.com/x/player/v2", bvid=bvid, cid=cid)
        title = player.get("title") or bvid
        subtitle_list = (player.get("subtitle") or {}).get("subtitles") or []
        if not subtitle_list:
            raise RuntimeError(
                "该视频没有可用字幕（可能需要登录 cookie，或视频本身无 CC 字幕）"
            )

        # 优先中文字幕
        chosen = next(
            (s for s in subtitle_list if s.get("lan", "").startswith("zh")),
            subtitle_list[0],
        )

        # 3. 下载字幕内容（URL 是协议相对地址）
        subtitle_url = chosen["subtitle_url"]
        if subtitle_url.startswith("//"):
            subtitle_url = "https:" + subtitle_url
        resp = client.get(subtitle_url)
        resp.raise_for_status()
        body = resp.json()

    entries = body.get("body") or []
    subtitles = [
        {"start": round(e["from"], 1), "end": round(e["to"], 1), "text": e["content"].strip()}
        for e in entries
        if e.get("content", "").strip()
    ]
    if not subtitles:
        raise RuntimeError("字幕内容为空")

    return {"bvid": bvid, "title": title, "subtitles": subtitles}


def main() -> int:
    parser = argparse.ArgumentParser(description="抓取 B 站视频字幕到项目字幕目录")
    parser.add_argument("bvid", help="BV 号，如 BV1mJ4m147PG")
    parser.add_argument("--cookie", default="", help="可选：B站登录 cookie（SESSDATA=...）")
    args = parser.parse_args()

    try:
        result = fetch_subtitle(args.bvid, cookie=args.cookie)
    except Exception as e:
        print(f"抓取失败: {e}", file=sys.stderr)
        return 1

    SUBTITLE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SUBTITLE_DIR / f"{args.bvid}.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已保存 {len(result['subtitles'])} 条字幕 → {out_path}")
    print(f"标题: {result['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
