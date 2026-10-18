#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 kb.js 中的 615 条结构化建议整合成 markdown，供上传到 ima 知识库。"""
import os, json, io

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB_JS = os.path.join(BASE, "web", "assets", "js", "kb.js")
OUT_MD = os.path.join(BASE, "knowledge", "人生指南知识库_合并.md")

def main():
    s = io.open(KB_JS, encoding="utf-8").read()
    i, j = s.find("{"), s.rfind("}")
    data = json.loads(s[i:j+1])
    entries = data["entries"]
    chapters = {c["sec"]: c["name"] for c in data["chapters"]}

    out = [f"# 高性价比人生指南 · 结构化知识库\n",
           f"> 来源：https://github.com/eternity4719/HowToLiveBetter (Unlicense)\n",
           f"> 共 {len(entries)} 条结构化建议，覆盖 33 个生活主题。\n",
           "每条建议标注：编号、章节、标题、成本(钱/时间/意志力)、收益级别、口径、性价比档、证据等级、摘要、收益详解、备注、来源。\n\n---\n"]

    by_sec = {}
    for it in entries:
        by_sec.setdefault(it["sec"], []).append(it)

    for sec in sorted(by_sec.keys()):
        name = chapters.get(sec, "")
        items = by_sec[sec]
        out.append(f"\n## 第{sec}章 {name}（{len(items)} 条）\n")
        for it in items:
            cost = it.get("cost", {})
            out.append(f"### [{it['id']}] {it['title']}\n")
            out.append(f"- **章节**：{it['secName']}")
            out.append(f"- **成本**：钱={cost.get('money','?')}，时间={cost.get('time','?')}，意志力={cost.get('will','?')}")
            out.append(f"- **收益级别**：{it.get('level','?')}")
            out.append(f"- **口径**：{it.get('scope','?')}")
            out.append(f"- **性价比档**：{it.get('ratio','?')}")
            out.append(f"- **证据等级**：{it.get('evidence','?')}")
            if it.get("plain"):
                out.append(f"\n**摘要**：{it['plain']}\n")
            if it.get("benefit"):
                out.append(f"\n**收益详解**：{it['benefit']}\n")
            if it.get("costText"):
                out.append(f"\n**成本说明**：{it['costText']}\n")
            if it.get("remark"):
                out.append(f"\n**备注**：{it['remark']}\n")
            if it.get("source"):
                out.append(f"\n*来源：{it['source']}*\n")
            out.append("")

    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    io.open(OUT_MD, "w", encoding="utf-8").write("\n".join(out))
    sz = os.path.getsize(OUT_MD)
    print(f"[OK] {OUT_MD}  | {len(entries)}条 {sz/1024:.1f}KB")

if __name__ == "__main__":
    main()