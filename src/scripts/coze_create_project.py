# -*- coding: utf-8 -*-
"""探索扣子空间：点击"+ 项目"，记录项目创建流程。"""
import sys, os, io, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coze_step import OUT
from playwright.sync_api import sync_playwright

PROFILE = os.path.join(OUT, "coze_profile_login")


def dump(page, prefix):
    page.screenshot(path=os.path.join(OUT, prefix + ".png"))
    body = page.evaluate("() => document.body.innerText || ''")
    with io.open(os.path.join(OUT, prefix + "_body.txt"), "w", encoding="utf-8") as f:
        f.write(body)


def main():
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(PROFILE, headless=False,
            viewport={"width": 1500, "height": 950}, locale="zh-CN")
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://www.coze.cn/space", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)
        print("URL:", page.url)
        dump(page, "proj_step0")

        # 找 "+ 项目" 按钮（右上角紫色按钮）
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
        print("PROJECT_BTNS:", candidates)
        target = None
        for c in candidates:
            if c["x"] > 1000 and c["y"] < 120:
                target = c
                break
        if target:
            print("CLICK:", target)
            page.mouse.click(target["x"] + target["w"]/2, target["y"] + target["h"]/2)
            page.wait_for_timeout(3000)
            print("AFTER_URL:", page.url)
            dump(page, "proj_step1")

            # 点击左侧"创建智能体"卡片：找包含该卡片描述文字的容器，再取最大父级
            card_info = page.evaluate("""() => {
              let leaf = null;
              for (const b of document.querySelectorAll('*')) {
                const t = (b.innerText || '').trim();
                if (t === '适用于快速搭建对话式智能体') {
                  leaf = b; break;
                }
              }
              if (!leaf) return null;
              let p = leaf.parentElement;
              let best = leaf;
              // 向上找 3 层或面积最大的直接容器
              for (let i = 0; i < 5 && p; i++) {
                const r = p.getBoundingClientRect();
                if (r.width > 200 && r.height > 200) { best = p; break; }
                p = p.parentElement;
              }
              const r = best.getBoundingClientRect();
              return {tag: best.tagName, cls: (best.className||'').toString().slice(0,60), x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)};
            }""")
            print("CARD_INFO:", card_info)
            if card_info:
                page.mouse.move(card_info["x"] + card_info["w"]/2, card_info["y"] + card_info["h"]/2)
                page.wait_for_timeout(800)
                # hover 后应该出现 "+ 创建" 按钮
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
                print("CREATE_BTN:", create_btn)
                if create_btn:
                    page.mouse.click(create_btn["x"] + create_btn["w"]/2, create_btn["y"] + create_btn["h"]/2)
                else:
                    page.mouse.click(card_info["x"] + card_info["w"]/2, card_info["y"] + card_info["h"]/2)
                page.wait_for_timeout(6000)
                print("AFTER_AGENT_URL:", page.url)
                dump(page, "proj_step2")
        else:
            print("NO_PROJECT_BTN")

        ctx.close()


if __name__ == "__main__":
    main()
