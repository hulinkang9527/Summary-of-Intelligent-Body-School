# -*- coding: utf-8 -*-
"""smoke_test.py —— 原型冒烟测试：启动本地服务、加载页面、检查 JS 错误、跑核心功能。"""
import json
import os
import subprocess
import sys
import time
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # 02_项目源码
WEB = os.path.join(ROOT, "web")
OUT = os.path.join(os.path.dirname(ROOT), "04_过程资料", "测试记录")
os.makedirs(OUT, exist_ok=True)
PORT = 8788

srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"],
                       cwd=WEB, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2.0)
report = {"console_errors": [], "page_errors": [], "checks": []}


def check(name, cond, detail=""):
    report["checks"].append({"name": name, "pass": bool(cond), "detail": str(detail)[:400]})
    print(("  [PASS] " if cond else "  [FAIL] ") + name + (f"  -> {detail}" if detail else ""))


try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.on("console", lambda m: report["console_errors"].append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: report["page_errors"].append(str(e)))
        # 结构化界面在改版后由 index.html 更名为 knowledge.html，
        # 本脚本的断言（#kpi-total、MTEngine 等）均属该页面，故指向 knowledge.html。
        pg.goto(f"http://127.0.0.1:{PORT}/knowledge.html", wait_until="load")
        pg.wait_for_timeout(1500)

        print("== 1. 基础加载 ==")
        check("页面标题正确", pg.title().startswith("明途"), pg.title())
        n = pg.evaluate("window.MTEngine.ENTRIES.length")
        check("知识库条目 = 615", n == 615, n)
        st = pg.evaluate("window.MTEngine.stats")
        check("证据等级分布与原书一致", st["byEvidence"] == {"A": 415, "B": 151, "C": 49}, st["byEvidence"])
        check("性价比分布与原书一致", st["byRatio"] == {"极高": 104, "高": 279, "一般": 232}, st["byRatio"])
        tot = pg.inner_text("#kpi-total")
        check("总览 KPI 渲染", tot == "615", tot)

        print("== 2. 检索与推理 ==")
        r1 = pg.evaluate("""() => { const r = window.MTEngine.answer('房东不退我押金，第一步做什么？');
            return {intent:r.intent, n:r.hits.length, top:r.hits[0]?r.hits[0].e.title:'', secs:r.scenes.map(s=>s.sc.name)}; }""")
        check("押金问题路由到租房场景", "租房" in "".join(r1["secs"]), r1["secs"])
        check("押金问题有命中条目", r1["n"] > 0, r1["n"])

        r2 = pg.evaluate("""() => { const r = window.MTEngine.answer('家人胸口疼还出汗，现在怎么办？'); return {intent:r.intent, guard:!!r.guard}; }""")
        check("急症识别为 emergency", r2["intent"] == "emergency", r2["intent"])
        check("急症触发安全护栏", r2["guard"] is True, r2["guard"])

        r3 = pg.evaluate("""() => { const r = window.MTEngine.answer('我不想活了，撑不住'); return {intent:r.intent, guard:!!r.guard}; }""")
        check("危机信号识别", r3["intent"] == "suicide", r3["intent"])
        check("危机触发护栏", r3["guard"] is True, r3["guard"])

        r4 = pg.evaluate("""() => { const r = window.MTEngine.answer('朋友让我帮他做贷款担保，能签吗？'); return {intent:r.intent, guard:!!r.guard, n:r.hits.length}; }""")
        check("法律类问题触发法律护栏", r4["guard"] is True and r4["intent"] == "legal", r4)

        r5 = pg.evaluate("""() => { const r = window.MTEngine.answer('失业三个月了，能领哪些钱？'); return {intent:r.intent, n:r.hits.length, secs:r.scenes.map(s=>s.sc.name)}; }""")
        check("失业问题路由正确", "没钱" in "".join(r5["secs"]), r5)

        print("== 3. ROI 算法 ==")
        e1 = pg.evaluate("""() => window.MTEngine.evaluateOption({name:'每天走8000步',money:'0',time:'少',will:'否',level:'大',scope:'死亡率'})""")
        check("零成本+大收益 => 极高", e1["ratio"] == "极高", e1["ratio"])
        e2 = pg.evaluate("""() => window.MTEngine.evaluateOption({name:'报3万元培训班',money:'多',time:'多',will:'是',level:'大',scope:'金钱'})""")
        check("高成本+大收益 => 一般", e2["ratio"] == "一般", e2["ratio"])
        e3 = pg.evaluate("""() => window.MTEngine.evaluateOption({name:'中等方案',money:'少',time:'少',will:'否',level:'大',scope:'时间'})""")
        check("低成本+大收益 => 高", e3["ratio"] == "高", e3["ratio"])
        check("ROI 推荐出同口径参考条目", len(e2["refs"]) > 0, len(e2["refs"]))

        print("== 4. 计划与复盘 ==")
        pl = pg.evaluate("""() => window.MTEngine.buildPlan({title:'体重降到75公斤',metric:'腰围90cm'},'死亡率')""")
        check("生成 4 个阶段", len(pl) == 4, len(pl))
        check("阶段含里程碑", all(p["milestone"] for p in pl), [p["milestone"][:10] for p in pl])
        rv = pg.evaluate("""() => window.MTEngine.review({planned:10,done:3,obstacles:['时间不够','坚持不下来']})""")
        check("复盘给出调整建议", len(rv["adjust"]) >= 3, len(rv["adjust"]))

        print("== 5. 端到端交互 ==")
        # 自我盘点
        pg.click('button[data-go="profile"]'); pg.wait_for_timeout(300)
        for i in range(4):
            pg.click(f"#v-grid .vcard:nth-child({i+1})")
        pg.fill("#pf-goal", "2027年6月前体重降到75公斤并保持3个月")
        pg.fill("#pf-metric", "连续3个月体重≤75kg")
        pg.fill("#pf-deadline", "2027-06-30")
        pg.dispatch_event("#pf-goal", "input")
        pg.click('#form-profile button[type="submit"]'); pg.wait_for_timeout(400)
        check("盘点已保存", pg.evaluate("localStorage.getItem('mingtu_state_v1').includes('75公斤')") is True)

        # 智能咨询
        pg.click('button[data-go="consult"]'); pg.wait_for_timeout(300)
        pg.fill("#q-input", "每天通勤两小时值不值？")
        pg.click('#form-ask button[type="submit"]'); pg.wait_for_timeout(1200)
        ans = pg.inner_text("#answer")
        check("咨询输出结论卡片", "结论" in ans, ans[:60])
        check("咨询输出带出处条目", "节" in ans and "条" in ans, ans[-160:])

        # 决策罗盘
        pg.click('button[data-go="decide"]'); pg.wait_for_timeout(300)
        pg.fill('#opt-rows input[data-oi="0"][data-k="name"]', "每天走8000步")
        pg.fill("#opt-rows input[data-oi='0'][data-k='name']", "每天走8000步")
        pg.click("#btn-eval"); pg.wait_for_timeout(600)
        dec = pg.inner_text("#opt-result")
        check("决策表输出性价比", "极高" in dec or "高" in dec, dec[:80])

        # 路线图
        pg.click('button[data-go="plan"]'); pg.wait_for_timeout(300)
        pg.click("#btn-genplan"); pg.wait_for_timeout(600)
        plan_txt = pg.inner_text("#plan-out")
        check("路线图渲染阶段", "第 1 阶段" in plan_txt, plan_txt[:60])

        # 执行看板
        pg.click('button[data-go="track"]'); pg.wait_for_timeout(400)
        ntask = pg.evaluate("document.querySelectorAll('#tr-list input[type=checkbox]').length")
        check("任务清单已同步", ntask > 0, ntask)
        if ntask:
            pg.check("#tr-list input[type=checkbox]")
            pg.wait_for_timeout(300)
            check("打卡后进度更新", pg.inner_text("#tr-done") == "1", pg.inner_text("#tr-done"))
        pg.click("#rv-obst .chip")
        pg.click('#form-review button[type="submit"]'); pg.wait_for_timeout(500)
        check("复盘报告生成", "执行率" in pg.inner_text("#rv-out"), pg.inner_text("#rv-out")[:60])

        # 知识库
        pg.click('button[data-go="library"]'); pg.wait_for_timeout(400)
        pg.fill("#lib-q", "安全带"); pg.wait_for_timeout(400)
        lib = pg.inner_text("#lib-out")
        check("知识库检索命中安全带", "安全带" in lib, pg.inner_text("#lib-count"))
        pg.click('[data-fev="A"]'); pg.wait_for_timeout(300)
        check("证据等级筛选生效", pg.inner_text("#lib-count") != "", pg.inner_text("#lib-count"))

        # 边界
        pg.click('button[data-go="boundary"]'); pg.wait_for_timeout(300)
        check("边界页渲染", "安全护栏" in pg.inner_text("#page-boundary"))

        # 截图
        shots = [("01_总览", "dashboard"), ("02_自我盘点", "profile"), ("03_智能咨询", "consult"),
                 ("04_决策罗盘", "decide"), ("05_路线图", "plan"), ("06_执行看板", "track"),
                 ("07_知识库", "library"), ("08_边界与设置", "boundary")]
        for name, pid in shots:
            pg.click(f'button[data-go="{pid}"]')
            pg.wait_for_timeout(700)
            pg.screenshot(path=os.path.join(OUT, f"{name}.png"), full_page=True)
        print(f"  截图已保存到 {OUT}")

        report["console_errors"] = report["console_errors"]
        b.close()
finally:
    srv.terminate()

passed = sum(1 for c in report["checks"] if c["pass"])
total = len(report["checks"])
print(f"\n===== 结果：{passed}/{total} 通过 =====")
if report["page_errors"]:
    print("页面异常：", report["page_errors"])
if report["console_errors"]:
    print("控制台错误：", report["console_errors"][:10])
with open(os.path.join(OUT, "smoke_test_report.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
sys.exit(0 if passed == total and not report["page_errors"] else 1)
