# -*- coding: utf-8 -*-
"""配置扣子智能体：粘贴人设提示词、设置开场白，并发布。"""
import sys, os, io, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coze_step import OUT
from playwright.sync_api import sync_playwright

PROFILE = os.path.join(OUT, "coze_profile_login")
BOT_URL = "https://www.coze.cn/space/7690812005850611758/bot/7690816126272012326"

PERSONA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "05_扣子智能体", "01_人设与回复逻辑_可直接粘贴.txt")


def dump(page, prefix):
    page.screenshot(path=os.path.join(OUT, prefix + ".png"))
    body = page.evaluate("() => document.body.innerText || ''")
    with io.open(os.path.join(OUT, prefix + "_body.txt"), "w", encoding="utf-8") as f:
        f.write(body)
    return body


def close_welcome(page):
    try:
        btn = page.evaluate("""() => {
          for (const b of document.querySelectorAll('button, div[role=button]')) {
            if ((b.innerText || '').trim() === '了解') {
              const r = b.getBoundingClientRect();
              if (r.width > 0) return {x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)};
            }
          }
          return null;
        }""")
        if btn:
            page.mouse.click(btn["x"] + btn["w"]/2, btn["y"] + btn["h"]/2)
            page.wait_for_timeout(1000)
            print("WELCOME_CLOSED")
    except Exception as e:
        print("NO_WELCOME:", e)


def paste_persona(page):
    persona = io.open(PERSONA_PATH, "r", encoding="utf-8").read()
    print("PERSONA_LEN:", len(persona))

    # 查找人设输入区：找包含 "人设与回复逻辑" 的 textarea/contenteditable
    editor = page.evaluate("""() => {
      // 优先：带 data-text 的 contenteditable 或 placeholder 含 "角色" 的 textarea
      for (const el of document.querySelectorAll('textarea, [contenteditable="true"], [contenteditable="plaintext-only"]')) {
        const r = el.getBoundingClientRect();
        if (r.width < 200 || r.height < 80) continue;
        const ph = (el.getAttribute('placeholder') || '');
        if (ph.includes('角色') || ph.includes('人设') || ph.includes('提示词')) {
          return {tag: el.tagName, editable: el.isContentEditable, x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height), ph: ph};
        }
      }
      // 次优：在页面左侧大 textarea/contenteditable
      let best = null;
      for (const el of document.querySelectorAll('textarea, [contenteditable="true"], [contenteditable="plaintext-only"]')) {
        const r = el.getBoundingClientRect();
        if (r.width > 0 && r.x < 700 && r.width > 300 && r.height > 150) {
          if (!best || r.width * r.height > best.area) best = {tag: el.tagName, editable: el.isContentEditable, x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height), area: r.width*r.height};
        }
      }
      if (best) delete best.area; return best;
    }""")
    print("EDITOR:", editor)
    if not editor:
        return False
    # 点击编辑器并粘贴
    page.mouse.click(editor["x"] + 30, editor["y"] + 30)
    page.wait_for_timeout(500)
    page.keyboard.press("Control+a")
    page.wait_for_timeout(200)
    if editor.get("editable"):
        page.evaluate("""(text) => {
          const el = document.querySelector('[contenteditable="true"], [contenteditable="plaintext-only"]');
          if (el) { el.innerText = text; }
        }""", persona)
    else:
        page.keyboard.type(persona, delay=5)
    page.wait_for_timeout(1000)
    print("PASTED")
    return True


def set_opening(page):
    # 展开「开场白」并设置
    try:
        opener = page.evaluate("""() => {
          for (const b of document.querySelectorAll('*')) {
            const t = (b.innerText || '').trim();
            if (t.includes('开场白')) {
              const r = b.getBoundingClientRect();
              if (r.width > 0) return {tag: b.tagName, text: t, x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)};
            }
          }
          return null;
        }""")
        print("OPENING_LABEL:", opener)
        if opener:
            page.mouse.click(opener["x"] + opener["w"]/2, opener["y"] + opener["h"]/2)
            page.wait_for_timeout(800)
        # 找开场白输入框
        inp = page.evaluate("""() => {
          for (const el of document.querySelectorAll('textarea, [contenteditable="true"]')) {
            const r = el.getBoundingClientRect();
            if (r.width > 200 && r.height > 40 && r.y > 400) {
              return {tag: el.tagName, x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)};
            }
          }
          return null;
        }""")
        print("OPENING_INP:", inp)
        if inp:
            opening = "你好，我是「明途」，你的人生规划助手。我可以帮你：\n1️⃣ 澄清价值观、目标、资源与约束\n2️⃣ 评估不同人生选择的投入产出比\n3️⃣ 生成 0-365 天四阶段可执行计划\n4️⃣ 跟踪执行并复盘调整\n\n先聊聊：你最近在纠结什么选择？"
            page.mouse.click(inp["x"] + 20, inp["y"] + 20)
            page.wait_for_timeout(300)
            page.keyboard.type(opening, delay=5)
            page.wait_for_timeout(500)
            print("OPENING_SET")
    except Exception as e:
        print("OPENING_ERR:", e)


def publish(page):
    # 点右上角发布
    pub = page.evaluate("""() => {
      for (const b of document.querySelectorAll('button, div[role=button]')) {
        const t = (b.innerText || '').trim();
        if (t === '发布') {
          const r = b.getBoundingClientRect();
          if (r.width > 0) return {tag: b.tagName, text: t, x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)};
        }
      }
      return null;
    }""")
    print("PUBLISH:", pub)
    if pub:
        page.mouse.click(pub["x"] + pub["w"]/2, pub["y"] + pub["h"]/2)
        page.wait_for_timeout(4000)
        print("PUBLISH_CLICKED")


def main():
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(PROFILE, headless=False,
            viewport={"width": 1500, "height": 950}, locale="zh-CN")
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(BOT_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)
        print("EDITOR_URL:", page.url)
        dump(page, "cfg_step0_editor")

        close_welcome(page)
        dump(page, "cfg_step1_no_welcome")

        ok = paste_persona(page)
        dump(page, "cfg_step2_prompt")

        set_opening(page)
        dump(page, "cfg_step3_opening")

        publish(page)
        dump(page, "cfg_step4_published")

        ctx.close()


if __name__ == "__main__":
    main()
