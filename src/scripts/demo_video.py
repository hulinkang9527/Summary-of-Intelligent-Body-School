# -*- coding: utf-8 -*-
"""
demo_video.py —— 生成 3~5 分钟项目演示视频

流程：
1. 用 Playwright 在本地启动原型并截取关键界面帧；
2. 用 edge-tts（或 Windows SAPI 备用）生成中文旁白；
3. 用 imageio_ffmpeg 提供的 ffmpeg 把帧序列 + 音频合并为 MP4。
"""
import io
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import edge_tts
import asyncio
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 02_项目源码
WEB = os.path.join(ROOT, "web")
OUT = os.path.join(os.path.dirname(ROOT), "03_演示视频", "项目演示视频.mp4")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
PORT = 8790

NARRATOR = """\
大家好，这是「明途」，一个基于 WorkBuddy Agent 平台开发的个性化人生规划 AI 助手。
它不是替你做重大人生决定，而是帮你把价值观、目标、资源和约束先理清楚，再把不同选择的投入产出比摆到台面上。

整个智能体由四部分组成：
一是智能体人设与工作流，定义在 WorkBuddy 的 Skill 里，包含五步工作流和安全护栏；
二是知识库，来自《高性价比人生指南》六百一十五条结构化建议，每条都带成本、收益、证据等级和来源；
三是长期记忆，用记忆文件保存用户档案、阶段计划和执行记录；
四是前端对话原型，让智能体的推理过程可视化、可演示。

先看智能体对话。
用户说想规划职业方向，明途启动第一步，先澄清价值观、目标和资源约束，而不是直接给答案。

接着评估投入产出比。
用户问：每天通勤两小时值不值？
智能体先做意图识别和知识库检索，把相关条目按口径分组、按性价比和证据等级排序，每条都注明出处，再给出动态成本档评估。

它也会识别危险信号。
比如「家人胸口疼还出汗」，智能体立刻触发安全护栏，先打 120，再给出四条现场处置条目，每条都带编号和证据等级。

除了对话界面，还有一个结构化的 Web 原型，展示智能体的完整能力。

首页总览显示知识库规模与覆盖主题。
所有推理在本地完成，不上传任何个人数据。

「自我盘点」页录入价值观排序、SMART 目标、资源与约束，这是后续一切判断的前提。

「智能咨询」输入真实问题，系统用 BM25 检索知识库，按口径分组、按性价比排序。

「决策罗盘」同时对比几个方案的成本、收益和口径，复用原书算法算出性价比档。

「路线图」把高性价比条目摊到 0 到 30、31 到 90、91 到 180、181 到 365 天四个阶段。

「执行看板」打卡并做周复盘，系统按完成率给评级，调整建议直接引用原书条目。

「知识库检索」支持按关键词、章节、证据等级、性价比自由筛选。

「边界与设置」页说明安全护栏、伦理边界和隐私策略。

这就是「明途」——一个基于 WorkBuddy Agent 平台、带知识库、带记忆、有安全护栏的个性化人生规划 AI 助手。谢谢观看。\
"""

SCENES = [
    ("00_agent_hello", 15, ""),
    ("01_agent_profile", 14, ""),
    ("02_agent_roi", 17, ""),
    ("03_agent_guard", 15, ""),
    ("04_dashboard", 14, ""),
    ("05_profile", 18, ""),
    ("06_consult_result", 26, ""),
    ("07_decide", 22, ""),
    ("08_plan", 20, ""),
    ("09_track", 17, ""),
    ("10_library", 13, ""),
    ("11_boundary", 13, ""),
]


def run_server():
    return subprocess.Popen(
        [sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"],
        cwd=WEB, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


def ensure_ffmpeg():
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg._utils.get_ffmpeg_exe()
        return exe
    except Exception:
        return None


async def gen_audio(path):
    # 尝试 edge-tts（Microsoft Xiaoxiao 中文女声），放慢语速以适配演示画面
    try:
        communicate = edge_tts.Communicate(NARRATOR, "zh-CN-XiaoxiaoNeural", rate="-25%")
        await communicate.save(path)
        if os.path.getsize(path) > 50000:
            print("[OK] 使用 edge-tts 生成旁白")
            return
    except Exception as e:
        print("[WARN] edge-tts 失败，转用 Windows SAPI:", e)

    # 备用：Windows SAPI
    ps = Path(path).with_suffix(".wav")
    script = f"""
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SelectVoice('Microsoft Huihui Desktop')
$synth.SetOutputToWaveFile('{ps}')
$synth.Speak([IO.File]::ReadAllText('{Path(path).with_suffix('.txt')}', [Text.Encoding]::UTF8))
$synth.Dispose()
"""
    txt = Path(path).with_suffix(".txt")
    txt.write_text(NARRATOR, encoding="utf-8")
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script], check=True)
    os.replace(ps, path)
    print("[OK] 使用 Windows SAPI 生成旁白")


def record_frames(tmpdir):
    srv = run_server()
    time.sleep(2)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            ctx = browser.new_context(viewport={"width": 1440, "height": 900}, record_video_dir=None)
            page = ctx.new_page()
            page.goto(f"http://127.0.0.1:{PORT}/index.html", wait_until="load")
            page.wait_for_timeout(800)

            def shot(name):
                pth = os.path.join(tmpdir, f"{name}.png")
                page.screenshot(path=pth, full_page=False)
                return pth

            # ===== 00-03 智能体对话（agent.html）=====
            page.goto(f"http://127.0.0.1:{PORT}/agent.html", wait_until="load")
            page.wait_for_timeout(1500)
            shot("00_agent_hello")

            page.click(".quick button:nth-child(1)")   # 职业规划 → 第1步
            page.wait_for_timeout(1400)
            shot("01_agent_profile")

            page.click(".quick button:nth-child(2)")   # ROI评估 → 第2步
            page.wait_for_timeout(2000)
            shot("02_agent_roi")

            page.click(".quick button:nth-child(5)")   # 安全护栏 → 第5步
            page.wait_for_timeout(1500)
            shot("03_agent_guard")

            # ===== 04-11 结构化原型（index.html）=====
            page.goto(f"http://127.0.0.1:{PORT}/index.html", wait_until="load")
            page.wait_for_timeout(800)

            # 04 总览
            page.click('button[data-go="dashboard"]'); page.wait_for_timeout(600)
            shot("04_dashboard")

            # 02 自我盘点 — 填点东西
            page.click('button[data-go="profile"]'); page.wait_for_timeout(500)
            for i in range(4):
                page.click(f"#v-grid .vcard:nth-child({i + 1})")
            page.fill("#pf-goal", "2027年6月前体重降到75公斤并保持3个月")
            page.fill("#pf-metric", "连续3个月体重≤75kg")
            page.fill("#pf-deadline", "2027-06-30")
            page.fill("#pf-skills", "Python, Excel")
            page.fill("#pf-money", "每月可支配1500元")
            page.fill("#pf-timePerWeek", "工作日1.5小时/天")
            page.fill("#pf-energy", "睡眠6.5小时，下午易困")
            page.fill("#pf-constraints", "不能离开上海；周末需休息半天")
            page.fill("#pf-support", "家人可提供临时住所")
            shot("05_profile")

            # 03 智能咨询
            page.click('button[data-go="consult"]'); page.wait_for_timeout(400)
            pass  # shot
            page.fill("#q-input", "每天通勤两小时值不值？")
            page.click('#form-ask button[type="submit"]'); page.wait_for_timeout(1400)
            shot("06_consult_result")

            # 05 危机
            page.fill("#q-input", "家人胸口疼还出汗，现在怎么办？")
            page.click('#form-ask button[type="submit"]'); page.wait_for_timeout(1000)
            pass  # shot

            # 06 决策罗盘
            page.click('button[data-go="decide"]'); page.wait_for_timeout(400)
            page.fill("[data-oi='0'][data-k='name']", "每天走8000步")
            page.click("#btn-addopt"); page.wait_for_timeout(300)
            page.fill("[data-oi='1'][data-k='name']", "买一张三年期健身房年卡")
            page.select_option("[data-oi='1'][data-k='money']", "多")
            page.select_option("[data-oi='1'][data-k='time']", "中")
            page.select_option("[data-oi='1'][data-k='will']", "是")
            page.click("#btn-eval"); page.wait_for_timeout(700)
            shot("07_decide")

            # 07 路线图
            page.click('button[data-go="plan"]'); page.wait_for_timeout(400)
            page.click("#btn-genplan"); page.wait_for_timeout(700)
            shot("08_plan")

            # 08 执行看板
            page.click('button[data-go="track"]'); page.wait_for_timeout(500)
            # 勾选前两个任务
            page.check("#tr-list .task:nth-of-type(1) input[type=checkbox]")
            page.wait_for_timeout(300)
            page.check("#tr-list .task:nth-of-type(2) input[type=checkbox]")
            page.wait_for_timeout(300)
            page.fill("#rv-planned", "10")
            page.fill("#rv-done", "7")
            page.click("#rv-obst .chip:nth-of-type(1)")
            page.click("#form-review button[type='submit']"); page.wait_for_timeout(600)
            shot("09_track")

            # 09 知识库
            page.click('button[data-go="library"]'); page.wait_for_timeout(400)
            page.fill("#lib-q", "安全带")
            page.wait_for_timeout(600)
            page.click('[data-fev="A"]'); page.wait_for_timeout(500)
            shot("10_library")

            # 10 边界
            page.click('button[data-go="boundary"]'); page.wait_for_timeout(400)
            shot("11_boundary")

            browser.close()
    finally:
        srv.terminate()


def make_video(tmpdir, audio_path, out_path, durations):
    ffmpeg = ensure_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("找不到 ffmpeg")

    # 获取音频时长
    dur_cmd = [ffmpeg, "-i", audio_path]
    try:
        import re
        probe = subprocess.run(dur_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", probe.stderr)
        if m:
            h, mi, se = float(m.group(1)), float(m.group(2)), float(m.group(3))
            audio_dur = h * 3600 + mi * 60 + se
        else:
            audio_dur = 240
    except Exception:
        audio_dur = 240

    # 按音频长度等比缩放帧停留时间
    total = sum(d for (_, d, _) in SCENES)
    scaled = [(n, round(d * audio_dur / total, 2), t) for (n, d, t) in SCENES]

    concat = os.path.join(tmpdir, "concat.txt")
    with io.open(concat, "w", encoding="utf-8") as f:
        for (name, dur, _) in scaled:
            img = os.path.join(tmpdir, f"{name}.png")
            if os.path.exists(img):
                f.write(f"file '{img}'\nduration {dur}\n")
        if scaled:
            f.write(f"file '{os.path.join(tmpdir, SCENES[-1][0] + '.png')}'\n")

    target = sum(d for (_, d, _) in scaled)
    cmd = [
        ffmpeg, "-y",
        "-f", "concat", "-safe", "0", "-i", concat,
        "-i", audio_path,
        "-vf", "format=yuv420p,scale=1440:900:force_original_aspect_ratio=decrease,pad=1440:900:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-t", str(target),
        out_path,
    ]
    print("  ffmpeg:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print(f"[OK] 演示视频已生成：{out_path}")


def main():
    tmpdir = tempfile.mkdtemp(prefix="mingtu_demo_")
    audio_path = os.path.join(tmpdir, "audio.mp3")
    print("== 1. 录制界面帧 ==")
    record_frames(tmpdir)
    print("== 2. 生成旁白 ==")
    asyncio.run(gen_audio(audio_path))
    print("== 3. 合成视频 ==")
    make_video(tmpdir, audio_path, OUT, SCENES)


if __name__ == "__main__":
    main()
