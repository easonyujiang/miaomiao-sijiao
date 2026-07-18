"""生成前端静态降级数据

从后端 seed 数据生成 JSON 文件，供前端 lib/site.ts 降级使用。

解决 P1-4：前后端数据重复维护问题 — 数据源统一到后端，
通过此脚本生成前端 fallback，保证一致性。

使用方式:
    python scripts/generate_fallback.py [--output frontend/public/fallback.json]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fastapi.testclient import TestClient

from ewa.core.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="生成前端静态降级数据")
    parser.add_argument(
        "--output",
        default="frontend/public/fallback.json",
        help="输出 JSON 文件路径（相对于项目根目录）",
    )
    parser.add_argument(
        "--slug",
        default="ashley",
        help="博主 slug",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    output_path = project_root / args.output

    print("Starting backend...")
    app = create_app()

    with TestClient(app) as client:
        print(f"Fetching site data: {args.slug}")
        r = client.get(f"/api/site/{args.slug}")
        if r.status_code != 200:
            print(f"Error: API returned {r.status_code}")
            return
        data = r.json()

    # 写入 JSON
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 统计
    projects = len(data.get("projects", []))
    videos = len(data.get("videos", []))
    faq = len(data.get("faq", []))
    diary = len(data.get("diary", []))
    size_kb = output_path.stat().st_size / 1024

    print(f"[OK] Fallback data generated: {output_path}")
    print(f"   projects: {projects} | videos: {videos} | faq: {faq} | diary: {diary}")
    print(f"   file size: {size_kb:.1f} KB")


if __name__ == "__main__":
    main()
