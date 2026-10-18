# -*- coding: utf-8 -*-
"""
build_kb.py —— 知识库构建脚本

把《高性价比人生指南》(HowToLiveBetter) book/*.md 正文解析成结构化知识库，
输出到 web/assets/js/kb.js，供前端「明途·人生规划 AI 助手」做检索增强(RAG)。

解析产物字段：
  id         条目标识，形如 "8-17"
  sec        节号（整数）
  secName    节名，如 "别把自己搭进去：法律与财产安全"
  no         条号（节内序号，整数）
  title      条目标题（动词开头的动作句）
  cost        {"money":"0|少|多","time":"少|中|多","will":"否|些|是"}
  level      收益量级 大/中/小
  scope      口径 死亡率/金钱/时间/自由
  cs         成本分 = money+time+will 权重和
  ratio      性价比档：极高/高/一般
  costText   成本栏原文
  plain      「说人话」栏原文
  benefit    收益栏原文
  evidence   证据等级 A/B/C
  source     来源栏原文
  remark     备注栏原文
  controversial 是否标注「争议」
  todo       是否标注「TODO 待核实」
  text       用于检索的全文字段（标题+说人话+收益+备注）
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                       # 02_项目源码
RAW = os.path.join(ROOT, "knowledge", "raw")
OUT = os.path.join(ROOT, "web", "assets", "js", "kb.js")

# ---- 与 HowToLiveBetter/index.html 保持一致的性价比算法（此处为唯一权威实现） ----
COST_W = {
    "money": {"0": 0, "少": 1, "多": 2},
    "time": {"少": 0, "中": 1, "多": 2},
    "will": {"否": 0, "些": 1, "是": 2},
}


def cost_score(cost):
    """三项成本相加得到成本分。缺失项按 0 计。"""
    total = 0
    for key, table in COST_W.items():
        total += table.get(str(cost.get(key, "")).strip(), 0)
    return total


def ratio_of(level, cs):
    """收益量级 + 成本分 -> 性价比档（照搬原书 index.html 的算法）。"""
    if level == "大":
        if cs == 0:
            return "极高"
        if cs <= 2:
            return "高"
        return "一般"
    if level == "中":
        return "高" if cs == 0 else "一般"
    return "一般"


TAG_RE = re.compile(r"<!--\s*成本标签\s*:(.*?)-->")
FIELD_RE = re.compile(r"^-\s*([^：:]+)[：:]\s*(.*)$")


def parse_tag(body):
    cost = {"money": "", "time": "", "will": ""}
    level, scope = "", ""
    for part in body.split():
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        k, v = k.strip(), v.strip()
        if k == "钱":
            cost["money"] = v
        elif k == "时间":
            cost["time"] = v
        elif k == "毅力":
            cost["will"] = v
        elif k == "收益":
            level = v
        elif k == "口径":
            scope = v
    return cost, level, scope


def parse_entry(sec_no, sec_name, block):
    """解析一条 ### 条目。"""
    lines = block.split("\n")
    head = lines[0]
    m = re.match(r"^###\s*(\d+)\.\s*(.+?)\s*$", head)
    if not m:
        return None
    no = int(m.group(1))
    title = m.group(2).strip()

    tag = ""
    tm = TAG_RE.search(block)
    if tm:
        tag = tm.group(1)
    cost, level, scope = parse_tag(tag)

    fields = {"成本": [], "说人话": [], "收益": [], "证据等级": [],
              "来源": [], "备注": []}
    cur = None
    for ln in lines[1:]:
        fm = FIELD_RE.match(ln.strip())
        if fm and fm.group(1).strip() in fields:
            cur = fm.group(1).strip()
            fields[cur].append(fm.group(2).strip())
        elif cur and ln.strip():
            fields[cur].append(ln.strip())
    get = lambda k: " ".join(fields[k]).strip()

    remark = get("备注")
    cs = cost_score(cost)
    return {
        "id": f"{sec_no}-{no}",
        "sec": sec_no,
        "secName": sec_name,
        "no": no,
        "title": title,
        "cost": cost,
        "level": level,
        "scope": scope,
        "cs": cs,
        "ratio": ratio_of(level, cs),
        "costText": get("成本"),
        "plain": get("说人话"),
        "benefit": get("收益"),
        "evidence": (get("证据等级") or "C")[:1],
        "source": get("来源"),
        "remark": remark,
        "controversial": "争议" in remark,
        "todo": "TODO" in remark or "待核实" in remark,
        "text": " ".join([title, get("说人话"), get("收益"), remark]).strip(),
    }


def build():
    files = sorted(f for f in os.listdir(RAW) if re.match(r"^\d\d-.*\.md$", f))
    entries, chapters = [], []
    for fn in files:
        path = os.path.join(RAW, fn)
        with open(path, encoding="utf-8") as fh:
            md = fh.read()
        sec_no = int(fn[:2])
        # 节标题取一级标题 "# N. 节名"
        hm = re.search(r"^#\s*(\d+)\.\s*(.+)$", md, re.M)
        sec_name = hm.group(2).strip() if hm else fn[:-3]
        chapters.append({"sec": sec_no, "name": sec_name, "file": fn})

        # 按 ### 切块
        parts = re.split(r"(?=^###\s*\d+\.\s)", md, flags=re.M)
        for p in parts:
            if not p.startswith("###"):
                continue
            e = parse_entry(sec_no, sec_name, p)
            if e:
                entries.append(e)

    stats = {
        "total": len(entries),
        "byEvidence": {g: sum(1 for e in entries if e["evidence"] == g) for g in "ABC"},
        "byRatio": {g: sum(1 for e in entries if e["ratio"] == g) for g in ("极高", "高", "一般")},
        "byScope": {},
        "controversial": sum(1 for e in entries if e["controversial"]),
        "todo": sum(1 for e in entries if e["todo"]),
    }
    for e in entries:
        stats["byScope"][e["scope"]] = stats["byScope"].get(e["scope"], 0) + 1

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    payload = {"chapters": chapters, "entries": entries, "stats": stats}
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("// 由 scripts/build_kb.py 自动生成，请勿手工修改。\n")
        fh.write("// 数据来源：《高性价比人生指南》 https://github.com/eternity4719/HowToLiveBetter (Unlicense)\n")
        fh.write("window.HLTB_KB = ")
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write(";\n")

    print(f"[OK] 条目 {stats['total']} 条 / 章节 {len(chapters)} 节")
    print(f"     证据等级 {stats['byEvidence']}")
    print(f"     性价比   {stats['byRatio']}")
    print(f"     口径     {stats['byScope']}")
    print(f"     争议 {stats['controversial']} 条 / 待核实 {stats['todo']} 条")
    print(f"[OUT] {OUT}")
    return stats


if __name__ == "__main__":
    s = build()
    if s["total"] < 500:
        print("[WARN] 条目数偏少，请检查解析逻辑", file=sys.stderr)
        sys.exit(1)
