# -*- coding: utf-8 -*-
"""
11 GitHub 上传助手（绕过被墙的 git 协议，走 api.github.com Contents API）
========================================================================
用法：
    1. 在浏览器创建空仓库（Public，不勾选 README/.gitignore/License）
    2. 确保 fine-grained Token 对该仓库有 Contents: Read and write 权限
    3. 运行：
       set GH_TOKEN=github_pat_xxx
       python scripts/11_github_upload.py --repo PainterAnkry/ecom-user-analysis
说明：
    * 上传内容 = git 已跟踪文件（git ls-files），与本地提交树一致；
    * 幂等：文件已存在则覆盖更新；中断后重跑即可续传；
    * Token 只从环境变量读取，不会写入任何文件。
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def api(url: str, method: str, token: str, payload: dict | None = None) -> dict:
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "ecom-uploader")
    data = json.dumps(payload).encode() if payload is not None else None
    try:
        with urllib.request.urlopen(req, data=data, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:500]
        raise RuntimeError(f"{method} {url} -> {e.code}: {body}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="owner/repo")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    token = os.environ.get("GH_TOKEN", "").strip()
    if not token:
        sys.exit("请先设置环境变量 GH_TOKEN（set GH_TOKEN=github_pat_...）")

    # 仓库可达性检查
    try:
        info = api(f"https://api.github.com/repos/{args.repo}", "GET", token)
    except RuntimeError as e:
        sys.exit(f"仓库不可访问：{e}\n请确认：1) 已在浏览器创建空仓库 {args.repo} "
                 f"2) Token 的 Repository access 包含该仓库且 Contents 权限为 Read and write")
    print(f"仓库 OK: {info['full_name']} (默认分支 {info.get('default_branch')}, "
          f"{'public' if info.get('visibility') == 'public' else info.get('visibility')})")

    files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True,
                           check=True).stdout.splitlines()
    base = f"https://api.github.com/repos/{args.repo}/contents/"
    ok = fail = 0
    for i, rel in enumerate(files, 1):
        rel = rel.replace("\\", "/")
        p = ROOT / rel
        content = base64.b64encode(p.read_bytes()).decode()
        payload = {"message": f"upload {rel}", "content": content}
        if args.dry_run:
            print(f"[dry] {rel} ({len(content) // 1024}KB)"); continue
        for attempt in range(3):
            try:
                api(base + rel, "PUT", token, payload)
                ok += 1
                break
            except RuntimeError as e:
                if "409" in str(e) and attempt < 2:      # 仓库刚建/临时冲突，稍等重试
                    time.sleep(5)
                    continue
                fail += 1
                print(f"[FAIL] {rel}: {e}")
                break
        if i % 10 == 0:
            print(f"  进度 {i}/{len(files)}（成功 {ok} 失败 {fail}）")
        time.sleep(0.3)
    print(f"\n完成：成功 {ok} / 失败 {fail} / 共 {len(files)} 个文件")
    print(f"仓库地址: https://github.com/{args.repo}")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
