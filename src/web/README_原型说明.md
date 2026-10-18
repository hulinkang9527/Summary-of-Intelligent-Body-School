# 「明途」人生规划 AI 助手 · 原型运行说明

## 快速启动

1. 直接用浏览器打开 `index.html`（推荐，双击即可）。
2. 或启动本地服务器：
   ```bash
   python -m http.server 8000
   ```
   然后访问 `http://localhost:8000/`。

## 文件说明

| 文件 | 作用 |
|------|------|
| `index.html` | 单页应用入口 |
| `assets/css/app.css` | 样式表 |
| `assets/js/kb.js` | 知识库（615 条，由 `scripts/build_kb.py` 生成） |
| `assets/js/engine.js` | 检索、推理、ROI、计划、复盘内核 |
| `assets/js/app.js` | 页面路由与 UI 状态管理 |

## 重新构建

```bash
cd ..
python scripts/build_kb.py
```

## 测试

```bash
cd ..
python scripts/smoke_test.py
```

测试通过后会自动截取各模块界面图，保存到 `../04_过程资料/测试记录/`。
