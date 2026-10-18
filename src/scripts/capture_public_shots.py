# -*- coding: utf-8 -*-
"""采集新版在线应用的公开页面截图（开场动画 / 登录页 / 知识库浏览页）。
登录后的界面由用户自行补充，本脚本只截取无需登录即可访问的页面。"""
import os
import sys

from playwright.sync_api import sync_playwright

BASE = "https://life-planner-agent.app.workbuddy.host"
OUT = r"D:\Desktop\Desktop\大数据应用场景项目实训课程考核项目\04_过程资料\新版应用截图"
os.makedirs(OUT, exist_ok=True)

for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
    os.environ.pop(k, None)

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, channel="msedge")
    ctx = b.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
    pg = ctx.new_page()

    # 1) 开场动画
    pg.goto(BASE + "/", wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(4000)
    pg.screenshot(path=os.path.join(OUT, "01_开场动画.png"))
    print("SHOT 01 开场动画")

    # 2) 跳过开场 -> 登录页
    pg.evaluate("() => { const s = document.getElementById('introSkip'); if (s) s.click(); }")
    pg.wait_for_timeout(1500)
    pg.screenshot(path=os.path.join(OUT, "02_登录页.png"))
    print("SHOT 02 登录页")

    # 3) 注册页（展示邮箱验证码注册）
    try:
        pg.get_by_text("注册", exact=True).first.click(timeout=5000)
        pg.wait_for_timeout(900)
        pg.screenshot(path=os.path.join(OUT, "03_注册页.png"))
        print("SHOT 03 注册页")
    except Exception as e:
        print("SKIP 03:", str(e)[:80])

    # 4) 知识库浏览页
    pg.goto(BASE + "/knowledge.html", wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(2500)
    pg.screenshot(path=os.path.join(OUT, "04_知识库浏览.png"))
    print("SHOT 04 知识库浏览")

    b.close()

print("DONE ->", OUT)
