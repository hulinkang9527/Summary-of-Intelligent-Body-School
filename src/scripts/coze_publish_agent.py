# -*- coding: utf-8 -*-
"""完成扣子智能体发布：处理发布弹窗，填写开场白并确认发布。"""
import sys, os, io, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coze_step import OUT
from playwright.sync_api import sync_playwright

PROFILE = os.path.join(OUT, "coze_profile_login")
BOT_URL = "https://www.coze.cn/space/7690812005850611758/bot/7690816126272012326"

OPENING = "你好，我是「明途」，你的人生规划助手。我可以帮你：\n1️⃣ 澄清价值观、目标、资源与约束\n2️⃣ 评估不同人生选择的投入产出比\n3️⃣ 生成 0-365 天四阶段可执行计划\n4️⃣ 跟踪执行并复盘调整\n\n先聊聊：你最近在纠结什么选择？"


def dump(page, prefix):
    page.screenshot(path=os.path.join(OUT, prefix + ".png"))
    body = page.evaluate("() => document.body.innerText || ''")
    with io.open(os.path.join(OUT, prefix + "_body.txt"), "w", encoding="utf-8") as f:
        f.write(body)
    return body


def dialog_open(page):
    return page.evaluate("""() => document.body.innerText.includes('简单几步') || document.body.innerText.includes('开场白文案')""")


def main():
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(PROFILE, headless=False,
            viewport={"width": 1500, "height": 950}, locale="zh-CN")
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(BOT_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)
        print("URL:", page.url)
        dump(page, "pub_step0")

        # 如果右上角还是"发布"，先点它
        pub = page.evaluate("""() => {
          for (const b of document.querySelectorAll('button, div[role=button]')) {
            if ((b.innerText || '').trim() === '发布') {
              const r = b.getBoundingClientRect();
              if (r.width > 0) return {x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)};
            }
          }
          return null;
        }""")
        if pub:
            print("CLICK_PUBLISH:", pub)
            page.mouse.click(pub["x"] + pub["w"]/2, pub["y"] + pub["h"]/2)
            page.wait_for_timeout(4000)
            dump(page, "pub_step1_dialog")

        if dialog_open(page):
            # 找 textarea/contenteditable 在弹窗里
            inp = page.evaluate("""() => {
              for (const el of document.querySelectorAll('textarea, [contenteditable="true"]')) {
                const r = el.getBoundingClientRect();
                if (r.width > 200 && r.height > 60 && r.y > 200 && r.y < 700) {
                  return {tag: el.tagName, editable: el.isContentEditable, x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height), ph: el.getAttribute('placeholder')||''};
                }
              }
              return null;
            }""")
            print("OPENING_INP:", inp)
            if inp:
                page.mouse.click(inp["x"] + 20, inp["y"] + 20)
                page.wait_for_timeout(300)
                page.keyboard.press("Control+a")
                page.wait_for_timeout(200)
                page.keyboard.type(OPENING, delay=5)
                page.wait_for_timeout(500)
                print("OPENING_TYPED")

            # 点确认，并轮询等待弹窗消失
            for attempt in range(3):
                confirm = page.evaluate("""() => {
                  for (const b of document.querySelectorAll('button, div[role=button]')) {
                    const t = (b.innerText || '').trim();
                    if (t === '确认') {
                      const r = b.getBoundingClientRect();
                      if (r.width > 0) return {x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)};
                    }
                  }
                  return null;
                }""")
                print("CONFIRM_ATTEMPT", attempt, confirm)
                if not confirm:
                    break
                page.mouse.click(confirm["x"] + confirm["w"]/2, confirm["y"] + confirm["h"]/2)
                page.wait_for_timeout(3000)
                if not dialog_open(page):
                    print("DIALOG_CLOSED")
                    break

        dump(page, "pub_step2_done")

        # 最终检查发布状态
        body = dump(page, "pub_step3_final")
        if "发布成功" in body or "已发布" in body:
            print("PUBLISH_OK")
        else:
            print("PUBLISH_STATUS_UNKNOWN")

        print("FINAL_URL:", page.url)
        ctx.close()


if __name__ == "__main__":
    main()
