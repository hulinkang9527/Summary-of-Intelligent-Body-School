# -*- coding: utf-8 -*-
"""扣子空间：自动创建「明途-人生规划AI助手」智能体并配置基本信息。"""
import sys, os, io, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coze_step import OUT
from playwright.sync_api import sync_playwright

PROFILE = os.path.join(OUT, "coze_profile_login")

NAME = "明途-人生规划AI助手"
DESC = ("基于《高性价比人生指南》615条结构化建议的个性化人生规划智能体。"
        "帮用户澄清价值观/目标/资源/约束、评估人生选择的投入产出比、生成四阶段计划、跟踪执行并复盘，内置危机/急症/法律安全护栏。")


def dump(page, prefix):
    page.screenshot(path=os.path.join(OUT, prefix + ".png"))
    body = page.evaluate("() => document.body.innerText || ''")
    with io.open(os.path.join(OUT, prefix + "_body.txt"), "w", encoding="utf-8") as f:
        f.write(body)
    return body


def click_create_agent_card(page):
    # 点右上角 + 项目
    candidates = page.evaluate("""() => {
      const out = [];
      for (const b of document.querySelectorAll('button, div[role=button]')) {
        const t = (b.innerText || '').trim();
        const r = b.getBoundingClientRect();
        if (t.includes('项目') && r.width > 0 && r.x > 800) {
          out.push({tag: b.tagName, text: t, x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)});
        }
      }
      return out;
    }""")
    target = next((c for c in candidates if c["x"] > 1000 and c["y"] < 120), None)
    if not target:
        raise RuntimeError("未找到 + 项目 按钮")
    page.mouse.click(target["x"] + target["w"]/2, target["y"] + target["h"]/2)
    page.wait_for_timeout(3000)

    # hover 左侧创建智能体卡片，出现 "+ 创建" 按钮
    card = page.evaluate("""() => {
      let leaf = null;
      for (const b of document.querySelectorAll('*')) {
        if ((b.innerText || '').trim() === '适用于快速搭建对话式智能体') { leaf = b; break; }
      }
      if (!leaf) return null;
      let p = leaf.parentElement, best = leaf;
      for (let i = 0; i < 5 && p; i++) {
        const r = p.getBoundingClientRect();
        if (r.width > 200 && r.height > 200) { best = p; break; }
        p = p.parentElement;
      }
      const r = best.getBoundingClientRect();
      return {x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)};
    }""")
    if not card:
        raise RuntimeError("未找到创建智能体卡片")
    page.mouse.move(card["x"] + card["w"]/2, card["y"] + card["h"]/2)
    page.wait_for_timeout(1000)
    create_btn = page.evaluate("""() => {
      for (const b of document.querySelectorAll('button, div[role=button]')) {
        const t = (b.innerText || '').trim();
        if (t === '创建' || t === '+ 创建') {
          const r = b.getBoundingClientRect();
          if (r.width > 0 && r.x > 400 && r.x < 700 && r.y > 300 && r.y < 700) {
            return {tag: b.tagName, text: t, x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)};
          }
        }
      }
      return null;
    }""")
    if not create_btn:
        raise RuntimeError("未找到卡片上的 创建 按钮")
    page.mouse.click(create_btn["x"] + create_btn["w"]/2, create_btn["y"] + create_btn["h"]/2)
    page.wait_for_timeout(4000)


def fill_basic_info(page):
    # 等待表单出现
    page.wait_for_timeout(2000)
    body = page.evaluate("() => document.body.innerText || ''")
    if '智能体名称' not in body:
        raise RuntimeError("未进入创建表单")

    # 填名称：按 placeholder 找 input
    name_inp = page.evaluate("""() => {
      for (const inp of document.querySelectorAll('input')) {
        const ph = (inp.getAttribute('placeholder') || '');
        if (ph.includes('独一无二')) {
          const r = inp.getBoundingClientRect();
          return {x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height), ph: ph};
        }
      }
      return null;
    }""")
    print("NAME_INP:", name_inp)
    if name_inp:
        page.mouse.click(name_inp["x"] + 30, name_inp["y"] + name_inp["h"]/2)
        page.wait_for_timeout(300)
        page.keyboard.press("Control+a")
        page.keyboard.type(NAME, delay=10)
        page.wait_for_timeout(500)

    # 填功能介绍：按 placeholder 找 textarea
    desc_area = page.evaluate("""() => {
      for (const el of document.querySelectorAll('textarea')) {
        const ph = (el.getAttribute('placeholder') || '');
        if (ph.includes('功能')) {
          const r = el.getBoundingClientRect();
          return {tag: el.tagName, x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height), ph: ph};
        }
      }
      return null;
    }""")
    print("DESC_AREA:", desc_area)
    if desc_area:
        page.mouse.click(desc_area["x"] + 30, desc_area["y"] + 20)
        page.wait_for_timeout(300)
        page.keyboard.press("Control+a")
        page.keyboard.type(DESC, delay=5)
        page.wait_for_timeout(500)
    # 确认
    confirm = page.evaluate("""() => {
      for (const b of document.querySelectorAll('button, div[role=button]')) {
        const t = (b.innerText || '').trim();
        if (t === '确认') {
          const r = b.getBoundingClientRect();
          if (r.width > 0) return {tag: b.tagName, text: t, x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)};
        }
      }
      return null;
    }""")
    print("CONFIRM:", confirm)
    if confirm:
        page.mouse.click(confirm["x"] + confirm["w"]/2, confirm["y"] + confirm["h"]/2)
        page.wait_for_timeout(6000)


def main():
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(PROFILE, headless=False,
            viewport={"width": 1500, "height": 950}, locale="zh-CN")
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://www.coze.cn/space", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)
        print("START_URL:", page.url)
        dump(page, "build_step0")

        click_create_agent_card(page)
        dump(page, "build_step1_form")

        fill_basic_info(page)
        dump(page, "build_step2_editor")

        print("END_URL:", page.url)
        with io.open(os.path.join(OUT, "coze_bot_url.txt"), "w", encoding="utf-8") as f:
            f.write(page.url)
        ctx.close()


if __name__ == "__main__":
    main()
