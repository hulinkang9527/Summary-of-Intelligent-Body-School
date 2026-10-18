/* agent.js —— 明途：登录认证 + LLM 流式对话（知识库检索增强）+ 多会话 + 云端档案/计划/打卡 + 统计 + 头像 */
(function () {
  'use strict';
  const cloud = window.MTCloud;
  const $ = (id) => document.getElementById(id);

  /* ================= 通用 ================= */
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  }
  // 简易 Markdown（转义后渲染：标题/加粗/列表/段落）
  function md(s) {
    let t = esc(s);
    t = t.replace(/^### (.+)$/gm, '<h4>$1</h4>')
         .replace(/^## (.+)$/gm, '<h4>$1</h4>')
         .replace(/\*\*([^*\n]+)\*\*/g, '<b>$1</b>')
         .replace(/^\s*[-*] (.+)$/gm, '<li>$1</li>')
         .replace(/^\s*\d+[.、] (.+)$/gm, '<li>$1</li>');
    t = t.replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>');
    t = t.split(/\n{2,}/).map((seg) => {
      const s2 = seg.trim();
      if (!s2) return '';
      if (/^<(h4|ul|div)/.test(s2)) return s2;
      return '<p>' + s2.replace(/\n/g, '<br>') + '</p>';
    }).join('');
    return t;
  }
  function todayStr() {
    const d = new Date();
    const p = (n) => String(n).padStart(2, '0');
    return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate());
  }
  function uid() { return 'c' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7); }

  /* ================= 视图切换（登录门控） ================= */
  const authView = $('authView'), appView = $('appView');
  function showAuth() { authView.style.display = ''; appView.hidden = true; }
  function showApp(email) {
    authView.style.display = 'none';
    appView.hidden = false;
    $('userEmail').textContent = email || '';
    bootUserData();
  }

  /* ================= 登录 / 注册（逻辑同前） ================= */
  const authMsg = $('authMsg');
  function amsg(t, ok) { authMsg.textContent = t || ''; authMsg.className = 'auth-msg' + (ok ? ' ok' : ''); }
  const emailOk = (v) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);

  document.querySelectorAll('.atab').forEach((b) => {
    b.addEventListener('click', () => {
      document.querySelectorAll('.atab').forEach((x) => x.classList.remove('on'));
      document.querySelectorAll('.apanel').forEach((x) => x.classList.remove('on'));
      b.classList.add('on');
      $('panel-' + b.dataset.atab).classList.add('on');
      amsg('');
    });
  });
  function gotoPanel(name) {
    document.querySelectorAll('.atab').forEach((x) => x.classList.toggle('on', x.dataset.atab === name));
    document.querySelectorAll('.apanel').forEach((x) => x.classList.toggle('on', x.id === 'panel-' + name));
    amsg('');
  }
  $('goReset').onclick = () => gotoPanel('reset');
  $('backLogin').onclick = () => gotoPanel('login');

  // 发送验证码句柄缓存：提交时复用第一次发送的结果，绝不重复发送（平台限每邮箱每分钟 1 条）
  const otpHandles = { su: null, ot: null, rs: null };
  function cooldown(btn, sec) {
    if (!btn) return;
    const orig = '发送验证码';
    btn.disabled = true;
    let left = sec;
    btn.textContent = left + 's';
    const t = setInterval(() => {
      left -= 1;
      if (left <= 0) { clearInterval(t); btn.disabled = false; btn.textContent = orig; }
      else btn.textContent = left + 's';
    }, 1000);
  }

  // 注册：发送并缓存 verificationId
  $('su-send').addEventListener('click', async () => {
    const email = $('su-email').value.trim();
    if (!emailOk(email)) return amsg('请输入正确的邮箱地址');
    const btn = $('su-send');
    btn.disabled = true;
    const sent = await cloud.auth.sendOtp({ email });
    if (sent.error) {
      btn.disabled = false;
      return amsg('验证码发送失败：' + ((sent.error && sent.error.message) || '请稍后再试'));
    }
    otpHandles.su = {
      email: email,
      verificationId: sent.data && sent.data.verificationId,
      isExistingUser: !!(sent.data && sent.data.isExistingUser),
    };
    if (otpHandles.su.isExistingUser) amsg('该邮箱已注册过，验证码可用于直接登录', true);
    else amsg('验证码已发送到邮箱，请查收（注意垃圾邮件箱）', true);
    cooldown(btn, 60);
  });
  // 重置密码：发送并缓存句柄
  $('rs-send').addEventListener('click', async () => {
    const email = $('rs-email').value.trim();
    if (!emailOk(email)) return amsg('请输入正确的邮箱地址');
    const btn = $('rs-send');
    btn.disabled = true;
    const started = await cloud.auth.resetPasswordForEmail(email);
    if (started.error) { btn.disabled = false; return amsg('验证码发送失败：' + started.error.message); }
    otpHandles.rs = { email: email, data: started.data };
    amsg('验证码已发送到邮箱，请查收', true);
    cooldown(btn, 60);
  });
  // 验证码登录：signInWithOtp 即发送，缓存 verify 句柄
  $('ot-send').addEventListener('click', async () => {
    const email = $('ot-email').value.trim();
    if (!emailOk(email)) return amsg('请输入正确的邮箱地址');
    const btn = $('ot-send');
    btn.disabled = true;
    const started = await cloud.auth.signInWithOtp({ email });
    if (started.error) { btn.disabled = false; return amsg('验证码发送失败：' + started.error.message); }
    otpHandles.ot = { email: email, data: started.data };
    amsg('验证码已发送到邮箱，请查收', true);
    cooldown(btn, 60);
  });
  $('panel-login').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = $('li-email').value.trim(), password = $('li-pwd').value;
    if (!emailOk(email) || !password) return amsg('请填写邮箱和密码');
    amsg('登录中…');
    const { error } = await cloud.auth.signInWithPassword({ email, password });
    if (error) return amsg('登录失败：账号或密码不正确（若从未设过密码，请用「验证码登录」或「忘记密码」）');
    amsg('');
  });
  $('panel-otp').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = $('ot-email').value.trim(), code = $('ot-code').value.trim();
    if (!emailOk(email) || !code) return amsg('请填写邮箱和验证码');
    const h = otpHandles.ot;
    if (!h || h.email !== email) return amsg('请先点击「发送验证码」');
    amsg('登录中…');
    const completed = await h.data.verify({ token: code });
    if (completed.error) {
      const m = (completed.error && completed.error.message) || '';
      return amsg('登录失败：' + (m || '验证码不正确或已过期'));
    }
    otpHandles.ot = null;
    amsg('');
  });
  $('panel-signup').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = $('su-email').value.trim(), code = $('su-code').value.trim(), password = $('su-pwd').value;
    if (!emailOk(email) || !code) return amsg('请填写邮箱和验证码');
    if (!password || password.length < 6) return amsg('密码至少 6 位');
    const h = otpHandles.su;
    if (!h || h.email !== email || !h.verificationId) return amsg('请先点击「发送验证码」');
    amsg('注册中…');
    const completed = await cloud.auth.verifyOtp({
      verificationId: h.verificationId,
      token: code,
      email,
      isExistingUser: !!h.isExistingUser,
      password: h.isExistingUser ? undefined : password,
    });
    if (completed.error) {
      const m = (completed.error && completed.error.message) || '';
      // 已注册邮箱：引导去登录（不暴露账号细节，按平台规范用中性文案）
      if (h.isExistingUser) { otpHandles.su = null; gotoPanel('login'); return amsg('该邮箱已注册过，请直接登录', true); }
      return amsg('注册失败：' + (m || '验证码不正确或已过期，请重新获取'));
    }
    otpHandles.su = null;
    amsg('');
  });
  $('panel-reset').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = $('rs-email').value.trim(), code = $('rs-code').value.trim(), password = $('rs-pwd').value;
    if (!emailOk(email) || !code) return amsg('请填写邮箱和验证码');
    if (!password || password.length < 6) return amsg('密码至少 6 位');
    const h = otpHandles.rs;
    if (!h || h.email !== email) return amsg('请先点击「发送验证码」');
    amsg('重置中…');
    const completed = await h.data.updateUser({ nonce: code, password });
    if (completed.error) {
      const m = (completed.error && completed.error.message) || '';
      return amsg('重置失败：' + (m || '验证码不正确或已过期'));
    }
    otpHandles.rs = null;
    amsg('密码已重置', true);
  });
  $('logoutBtn').addEventListener('click', () => cloud.auth.signOut());

  /* ================= 模型选择 ================= */
  let models = [], currentModel = null;
  function fmtSpeed(m) {
    if (/auto/i.test(m.id || m.name || '')) return '自动（可能慢）';
    if (m.reasoning && m.reasoning.supportedEfforts && m.reasoning.supportedEfforts.length) return '深度思考';
    return '快速';
  }
  // 兜底：无论列表里有没有 Auto，实际发送都避免用它，防止路由到长思考模型
  function safeModel() {
    if (!currentModel || /auto/i.test(currentModel.id || currentModel.name || '')) {
      currentModel = models.find((m) => m.id === 'deepseek-v4-flash')
        || models.find((m) => m.id === 'kimi-k2.6')
        || models.find((m) => !(/auto/i.test(m.id || m.name || '')) && !isDeepThink(m))
        || models[0];
    }
    return currentModel;
  }
  function isDeepThink(m) {
    return !!(m && m.reasoning && m.reasoning.supportedEfforts && m.reasoning.supportedEfforts.length);
  }
  async function loadModels() {
    try {
      models = (await cloud.llm.models.list()).filter((m) => m.disabled !== true);
    } catch (e) { models = []; }
    // Auto 模型会由平台动态路由，经常出现长思考甚至超时，作业演示不可控，因此从列表中移除
    models = models.filter((m) => !/auto/i.test(m.id || m.name || ''));
    const menu = $('modelMenu');
    if (!models.length) {
      $('modelName').textContent = '模型不可用';
      $('modelState').textContent = '暂无可用模型';
      return;
    }
    // 默认选实测最快的非推理模型
    currentModel = models.find((m) => m.id === 'deepseek-v4-flash')
      || models.find((m) => m.id === 'kimi-k2.6')
      || models.find((m) => !isDeepThink(m))
      || models[0];
    menu.innerHTML = models.map((m, i) =>
      '<button class="model-opt' + (m.id === currentModel.id ? ' on' : '') + '" data-i="' + i + '">' +
      '<span>' + esc(m.name || m.id) + '</span><small>' + fmtSpeed(m) + (m.credits ? ' · ' + esc(m.credits) : '') + '</small></button>'
    ).join('');
    $('modelName').textContent = (currentModel.name || currentModel.id) + ' · ' + fmtSpeed(currentModel);
    menu.querySelectorAll('.model-opt').forEach((b) => {
      b.addEventListener('click', () => {
        currentModel = models[Number(b.dataset.i)];
        $('modelName').textContent = (currentModel.name || currentModel.id) + ' · ' + fmtSpeed(currentModel);
        menu.querySelectorAll('.model-opt').forEach((x) => x.classList.toggle('on', x === b));
        $('modelMenu').hidden = true;
      });
    });
  }
  $('modelBtn').addEventListener('click', () => { $('modelMenu').hidden = !$('modelMenu').hidden; });
  document.addEventListener('click', (e) => {
    if (!$('modelBox').contains(e.target)) $('modelMenu').hidden = true;
  });

  /* ================= 多会话管理（localStorage） ================= */
  const STORE = 'mt_convs_v1';
  let convs = [];       // [{id,title,messages:[{role,content}],createdAt}]
  let curId = null;
  try { convs = JSON.parse(localStorage.getItem(STORE) || '[]'); } catch (e) { convs = []; }
  function persist() {
    try { localStorage.setItem(STORE, JSON.stringify(convs.slice(0, 50))); } catch (e) {}
  }
  function curConv() { return convs.find((c) => c.id === curId) || null; }
  function renderConvList() {
    const list = $('convList');
    list.innerHTML = convs.map((c) =>
      '<div class="conv-item' + (c.id === curId ? ' on' : '') + '" data-id="' + c.id + '">' +
      '<span>' + esc(c.title || '新对话') + '</span><button class="conv-del" data-id="' + c.id + '">✕</button></div>'
    ).join('');
    list.querySelectorAll('.conv-item').forEach((el) => {
      el.addEventListener('click', (e) => {
        if (e.target.classList.contains('conv-del')) return;
        switchConv(el.dataset.id);
      });
    });
    list.querySelectorAll('.conv-del').forEach((b) => {
      b.addEventListener('click', (e) => {
        e.stopPropagation();
        convs = convs.filter((c) => c.id !== b.dataset.id);
        persist();
        if (curId === b.dataset.id) newChat();
        else renderConvList();
      });
    });
  }
  function newChat() {
    const c = { id: uid(), title: '新对话', messages: [], createdAt: Date.now() };
    convs.unshift(c); curId = c.id; persist();
    renderConvList(); renderChat();
    $('welcome').hidden = false; $('chat').hidden = true;
    if (window.innerWidth <= 820) toggleSidebar(false);
  }
  function switchConv(id) {
    curId = id; persist(); renderConvList(); renderChat();
    const c = curConv();
    $('welcome').hidden = !!(c && c.messages.length);
    $('chat').hidden = !(c && c.messages.length);
    if (window.innerWidth <= 820) toggleSidebar(false);
  }
  function renderChat() {
    const c = curConv();
    const chat = $('chat');
    chat.innerHTML = '';
    if (!c) return;
    c.messages.forEach((m) => {
      if (m.role === 'user') renderMsg('user', esc(m.content));
      else renderMsg('bot', md(m.content));
    });
    chat.scrollTop = chat.scrollHeight;
  }

  /* ================= 侧栏 / 视图导航 ================= */
  function toggleSidebar(open) {
    $('sidebar').classList.toggle('open', open);
    $('sbMask').classList.toggle('on', open);
  }
  $('sbOpen').addEventListener('click', () => toggleSidebar(true));
  $('sbClose').addEventListener('click', () => toggleSidebar(false));
  $('sbMask').addEventListener('click', () => toggleSidebar(false));
  $('newChatBtn').addEventListener('click', () => { switchView('chat'); newChat(); });
  document.querySelectorAll('.sb-item').forEach((b) => {
    b.addEventListener('click', () => switchView(b.dataset.view));
  });
  function switchView(name) {
    document.querySelectorAll('.view').forEach((v) => v.classList.remove('on'));
    $('view-' + name).classList.add('on');
    if (name === 'stats') loadStats();
    if (window.innerWidth <= 820) toggleSidebar(false);
  }

  /* ================= 知识库检索 + 人设 ================= */
  const CRISIS_RE = /(自杀|轻生|不想活|了结|结束生命|自残|伤害自己)/;
  const GUARD_HTML =
    '<div class="guard"><h4>⚠ 请先照顾好自己</h4>' +
    '<p style="font-size:13px">你并不孤单。全国心理援助热线 <b>400-161-9995</b>（24小时），北京心理危机研究与干预中心 <b>010-82951332</b>。如果此刻有紧急危险，请拨打 <b>120</b> 或告诉身边能立刻赶到你身边的人。</p></div>';

  function retrieve(q) {
    try {
      const ans = window.MTEngine.answer(q);
      return (ans && ans.hits) ? ans.hits.slice(0, 4).map((h) => h.e) : [];
    } catch (e) { return []; }
  }
  function hitsHtml(hits) {
    if (!hits.length) return '';
    return '<div class="kb-hits"><b style="font-size:12px">📚 依据的知识库条目</b>' +
      hits.map((e) =>
        '<div class="kh"><b>' + esc(e.title) + '</b>' +
        '<span class="pill ' + (e.ratio === '极高' ? 'hi' : (e.ratio === '高' ? 'mid' : 'lo')) + '">性价比' + esc(e.ratio) + '</span>' +
        '<span class="pill ' + (e.evidence === 'A' ? 'hi' : (e.evidence === 'B' ? 'mid' : 'lo')) + '">证据' + esc(e.evidence) + '级</span>' +
        '<div class="kb-src">' + esc(e.secName || e.sec || '') + (e.scope ? ' · ' + esc(e.scope) : '') + '</div></div>'
      ).join('') + '</div>';
  }
  function systemPrompt(hits) {
    let p =
      '你是「明途」，一个个性化人生规划 AI 助手，来自《大数据应用场景项目实训》课程项目。' +
      '你的方法论：① 先澄清对方的价值观、目标、资源、约束（信息不足时先追问，一次最多问 2-3 个问题）；' +
      '② 用投入产出比（成本/收益/证据等级）帮他把选择摆上台面；③ 把结论拆成 0-30 天 / 31-90 天 / 91-180 天 / 181-365 天的阶段计划；' +
      '④ 提醒跟踪复盘；⑤ 守住安全边界：医疗、法律、投资等重大事项必须建议咨询持证专业人士，不做确定性承诺。\n' +
      '要求：中文回答，语气务实、接地气、不说教；用短段落和列表，重点加粗；单次回答控制在 400 字以内，除非用户要求展开计划。';
    if (hits && hits.length) {
      p += '\n\n以下是与用户问题最相关的知识库条目（来自《高性价比人生指南》，已标注性价比与证据等级），回答时优先参考、注明依据，不要编造数据：\n';
      hits.forEach((e) => {
        p += '【' + e.id + '】' + e.title + '（性价比:' + e.ratio + ' 证据:' + e.evidence + '级 ' + (e.secName || '') + '）' +
          '：' + String(e.plain || '').slice(0, 200) + '\n';
      });
    }
    return p;
  }

  /* ================= 对话核心（LLM 流式） ================= */
  const chat = $('chat'), input = $('msg'), sendBtn = $('sendBtn');
  let generating = false, controller = null;

  function renderMsg(who, html) {
    const div = document.createElement('div');
    div.className = 'msg ' + who;
    div.innerHTML = '<div class="avatar">' + (who === 'user' ? '我' : '明') + '</div>' +
      '<div class="bubble">' + html + '</div>';
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
    return div;
  }
  function showKbBanner(q) {
    const sc = $('chatScroll');
    const b = document.createElement('div');
    b.className = 'kb-banner';
    b.innerHTML = '📚 <b>知识库检索</b>　查询：' + esc(q).slice(0, 40);
    chat.parentNode.insertBefore(b, chat);
    setTimeout(() => b.remove(), 6000);
  }
  function setBusy(busy) {
    generating = busy;
    sendBtn.classList.toggle('stop', busy);
    sendBtn.textContent = busy ? '■' : '➤';
    $('modelState').textContent = busy ? '生成中' : '已就绪';
    $('modelState').previousElementSibling.classList.toggle('busy', busy);
    $('modelState').previousElementSibling.classList.toggle('ok', !busy);
  }

  function logChat(scene, question) {
    if (!currentUser) return;
    cloud.database.from('chat_logs').insert({ scene: scene, question: String(question).slice(0, 300) })
      .then((r) => { if (r.error) console.warn('logChat', r.error.message); });
  }

  async function send(q) {
    q = (q || input.value).trim();
    if (!q || generating) return;
    input.value = ''; autoGrow();
    let c = curConv();
    if (!c) { newChat(); c = curConv(); }
    if (c.title === '新对话') { c.title = q.slice(0, 18); renderConvList(); }

    $('welcome').hidden = true; $('chat').hidden = false;
    renderMsg('user', esc(q));
    c.messages.push({ role: 'user', content: q });
    persist();

    showKbBanner(q);
    const crisis = CRISIS_RE.test(q);
    const hits = retrieve(q);
    logChat(crisis ? '危机干预' : (hits.length ? '知识库咨询' : '自由对话'), q);

    // 护栏先行
    if (crisis) renderMsg('bot', GUARD_HTML);

    // AI 气泡（流式）
    const div = renderMsg('bot', '<div class="think"><span class="think-tag">🤔 俺正在努力的思考中…中中........</span></div><span class="cursor"></span>');
    const bubble = div.querySelector('.bubble');
    setBusy(true);
    controller = new AbortController();

    const history = c.messages.slice(-9).map((m) => ({ role: m.role, content: m.content }));
    const messages = [{ role: 'system', content: systemPrompt(hits) }, ...history];

    let full = '';
    let think = '';
    try {
      const modelToCall = safeModel();
      $('modelName').textContent = (currentModel.name || currentModel.id) + ' · ' + fmtSpeed(currentModel);
      for await (const chunk of cloud.llm.chat.completions.create({
        model: modelToCall.id,
        messages: messages,
        stream: true,
        temperature: 0.8,
        conversationId: c.id,
        signal: controller.signal,
      })) {
        const d = chunk.choices && chunk.choices[0] && chunk.choices[0].delta;
        if (!d) continue;
        // 推理模型：思考过程走 reasoning_content，实时显示避免长时间空白
        if (d.reasoning_content) {
          think += d.reasoning_content;
          const tail = esc(think.length > 260 ? think.slice(-260) : think);
          bubble.innerHTML = '<div class="think"><span class="think-tag">🤔 俺正在努力的思考中…中中........</span><div class="think-body">' + tail + '</div></div><span class="cursor"></span>';
          chat.scrollTop = chat.scrollHeight;
        }
        if (d.content) {
          full += d.content;
          bubble.innerHTML = md(full) + '<span class="cursor"></span>';
          chat.scrollTop = chat.scrollHeight;
        }
      }
    } catch (err) {
      if (err && err.name === 'AbortError') {
        full = full || '（已停止生成）';
      } else {
        const code = err && err.error && err.error.code || '';
        full = full || ('⚠ 生成失败' + (String(code).indexOf('quota') === 0 ? '：额度不足，请稍后再试' : '：服务暂时不可用，请点击重试'));
      }
    }
    setBusy(false); controller = null;
    // 收尾：正文 + 可折叠思考过程 + 命中条目
    const thinkDone = think
      ? '<details class="think done"><summary>💡 思考过程（点击展开）</summary><div class="think-body">' + esc(think) + '</div></details>'
      : '';
    if (!full && think) full = '⚠ 这次模型只输出了思考过程没有给出结论，点击下方「重新生成」或换一个模型再试。';
    bubble.innerHTML = (full ? md(full) : '') + thinkDone + hitsHtml(hits);

    // 操作按钮：保存计划 / 重新生成
    const acts = document.createElement('div');
    acts.className = 'msg-actions';
    acts.innerHTML = '<button class="act-save">💾 保存到我的规划</button><button class="act-re">↻ 重新生成</button>';
    bubble.appendChild(acts);
    chat.scrollTop = chat.scrollHeight;

    c.messages.push({ role: 'assistant', content: full });
    persist();

    acts.querySelector('.act-save').addEventListener('click', function () {
      savePlan({ title: c.title, horizon: '对话生成', content: full }, this);
    });
    acts.querySelector('.act-re').addEventListener('click', function () {
      if (generating) return;
      c.messages.pop(); persist();
      div.remove(); acts.remove();
      send(c.messages.length ? c.messages[c.messages.length - 1].content : q);
    });
  }

  function autoGrow() {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
  }
  input.addEventListener('input', autoGrow);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  });
  sendBtn.addEventListener('click', () => { if (generating && controller) controller.abort(); else send(); });
  document.querySelectorAll('#wQuick button').forEach((b) => {
    b.addEventListener('click', () => send(b.dataset.q));
  });

  /* ================= 我的规划：档案 / 计划 / 打卡 ================= */
  let currentUser = null, profileRow = null;

  function savePlan(plan, btn) {
    if (!plan || !currentUser) return;
    if (btn) { btn.disabled = true; btn.textContent = '保存中…'; }
    cloud.database.from('plans').insert({ title: plan.title, horizon: plan.horizon, content: plan.content }).select()
      .then((r) => {
        if (r.error) { if (btn) { btn.disabled = false; btn.textContent = '💾 保存到我的规划'; } return; }
        if (btn) btn.textContent = '✅ 已保存';
        loadPlans();
      });
  }
  function loadPlans() {
    cloud.database.from('plans').select('*').order('created_at', { ascending: false }).limit(50)
      .then((r) => {
        const list = $('planList');
        if (r.error) { list.innerHTML = '<p class="hint">加载失败</p>'; return; }
        const rows = r.data || [];
        if (!rows.length) { list.innerHTML = '<p class="hint">还没有计划。去「对话」页生成一个吧。</p>'; return; }
        list.innerHTML = rows.map((p) =>
          '<div class="plan-item"><div class="pi-head"><b>' + esc(p.title) + '</b>' +
          '<span class="tagp">' + esc(p.horizon || '') + '</span>' +
          '<button class="linklike del-plan" data-id="' + p.id + '">删除</button></div>' +
          '<pre class="pi-body">' + esc(p.content || '') + '</pre></div>'
        ).join('');
        list.querySelectorAll('.del-plan').forEach((b) => {
          b.addEventListener('click', () => {
            cloud.database.from('plans').delete().eq('id', Number(b.dataset.id)).select().then((rr) => {
              if (!rr.error) loadPlans();
            });
          });
        });
      });
  }
  function loadProfile() {
    cloud.database.from('user_profiles').select('*').limit(1).then((r) => {
      if (r.error || !r.data || !r.data.length) return;
      profileRow = r.data[0];
      $('pf-nickname').value = profileRow.nickname || '';
      $('pf-values').value = profileRow.values_top3 || '';
      $('pf-goal').value = profileRow.goal || '';
      $('pf-resources').value = profileRow.resources || '';
      $('pf-constraints').value = profileRow.constraints || '';
    });
  }
  $('pfSave').addEventListener('click', () => {
    const body = {
      nickname: $('pf-nickname').value.trim().slice(0, 50),
      values_top3: $('pf-values').value.trim().slice(0, 200),
      goal: $('pf-goal').value.trim().slice(0, 300),
      resources: $('pf-resources').value.trim().slice(0, 300),
      constraints: $('pf-constraints').value.trim().slice(0, 300),
    };
    const btn = $('pfSave');
    btn.disabled = true; btn.textContent = '保存中…';
    const req = profileRow
      ? cloud.database.from('user_profiles').update(body).eq('id', profileRow.id).select()
      : cloud.database.from('user_profiles').insert(body).select();
    req.then((r) => {
      btn.disabled = false;
      if (r.error || !r.data || !r.data.length) { btn.textContent = '保存档案'; return; }
      profileRow = r.data[0];
      btn.textContent = '✅ 已保存';
      setTimeout(() => { btn.textContent = '保存档案'; }, 2000);
    });
  });

  let todayCheckins = [];
  function renderCheckins() {
    const list = $('ciList');
    if (!todayCheckins.length) { list.innerHTML = '<p class="hint">今天还没有打卡项。</p>'; return; }
    list.innerHTML = todayCheckins.map((c) =>
      '<label class="ci-item"><input type="checkbox" data-id="' + c.id + '"' + (c.done ? ' checked' : '') + '>' +
      '<span class="' + (c.done ? 'done' : '') + '">' + esc(c.item) + '</span>' +
      '<button class="linklike del-ci" data-id="' + c.id + '">删</button></label>'
    ).join('');
    list.querySelectorAll('input[type=checkbox]').forEach((cb) => {
      cb.addEventListener('change', () => {
        cloud.database.from('checkins').update({ done: cb.checked }).eq('id', Number(cb.dataset.id)).select()
          .then((r) => {
            const affected = Array.isArray(r.data) ? r.data : [];
            if (r.error || affected.length === 0) { cb.checked = !cb.checked; return; }
            const row = todayCheckins.find((x) => String(x.id) === cb.dataset.id);
            if (row) row.done = cb.checked;
            cb.nextElementSibling.className = cb.checked ? 'done' : '';
          });
      });
    });
    list.querySelectorAll('.del-ci').forEach((b) => {
      b.addEventListener('click', () => {
        cloud.database.from('checkins').delete().eq('id', Number(b.dataset.id)).select()
          .then(() => { todayCheckins = todayCheckins.filter((x) => String(x.id) !== b.dataset.id); renderCheckins(); });
      });
    });
  }
  function loadCheckins() {
    cloud.database.from('checkins').select('*').eq('check_date', todayStr()).order('id', { ascending: true })
      .then((r) => { if (!r.error) { todayCheckins = r.data || []; renderCheckins(); } });
  }
  $('ciAdd').addEventListener('click', () => {
    const v = $('ciItem').value.trim();
    if (!v) return;
    $('ciItem').value = '';
    cloud.database.from('checkins').insert({ item: v.slice(0, 100), check_date: todayStr() }).select()
      .then((r) => { if (!r.error && r.data && r.data[0]) { todayCheckins.push(r.data[0]); renderCheckins(); } });
  });
  $('ciItem').addEventListener('keydown', (e) => { if (e.key === 'Enter') $('ciAdd').click(); });

  /* ================= 数据统计 ================= */
  function loadStats() {
    if (!currentUser) return;
    const db = cloud.database;
    db.from('chat_logs').select('*', { count: 'exact', head: true }).then((r) => { if (!r.error) $('stChats').textContent = r.count; });
    db.from('plans').select('*', { count: 'exact', head: true }).then((r) => { if (!r.error) $('stPlans').textContent = r.count; });
    db.from('checkins').select('done').eq('check_date', todayStr()).then((r) => {
      if (r.error) return;
      const rows = r.data || [];
      const done = rows.filter((x) => x.done).length;
      $('stDone').textContent = rows.length ? done + '/' + rows.length : '0';
    });
    const weekAgo = new Date(Date.now() - 6 * 86400000);
    const wp = (n) => String(n).padStart(2, '0');
    const weekAgoStr = weekAgo.getFullYear() + '-' + wp(weekAgo.getMonth() + 1) + '-' + wp(weekAgo.getDate());
    db.from('chat_logs').select('created_at, scene').gte('created_at', weekAgoStr).order('created_at')
      .then((r) => {
        if (r.error) return;
        const rows = r.data || [];
        const days = [];
        for (let i = 6; i >= 0; i--) {
          const d = new Date(Date.now() - i * 86400000);
          days.push(d.getFullYear() + '-' + wp(d.getMonth() + 1) + '-' + wp(d.getDate()));
        }
        const perDay = days.map((d) => rows.filter((x) => String(x.created_at).slice(0, 10) === d).length);
        const max = Math.max(1, ...perDay);
        const labels = ['日', '一', '二', '三', '四', '五', '六'];
        $('stWeek').innerHTML = days.map((d, i) => {
          const wd = new Date(d + 'T00:00:00').getDay();
          return '<div class="bar-col"><div class="bar" style="height:' + Math.round(perDay[i] / max * 90 + 4) + 'px"></div>' +
            '<span>' + perDay[i] + '</span><i>周' + labels[wd] + '</i></div>';
        }).join('');
        const byScene = {};
        rows.forEach((x) => { byScene[x.scene || '自由对话'] = (byScene[x.scene || '自由对话'] || 0) + 1; });
        const entries = Object.entries(byScene).sort((a, b) => b[1] - a[1]);
        const sMax = Math.max(1, ...entries.map((e) => e[1]));
        $('stScenes').innerHTML = entries.length
          ? entries.map((e) => '<div class="scene-row"><span>' + esc(e[0]) + '</span><div class="sbar" style="width:' + Math.round(e[1] / sMax * 100) + '%"></div><b>' + e[1] + '</b></div>').join('')
          : '<p class="hint">还没有对话记录。</p>';
        db.from('chat_logs').select('created_at').order('created_at', { ascending: true }).limit(1).then((rr) => {
          if (!rr.error && rr.data && rr.data.length) {
            const first = new Date(rr.data[0].created_at);
            $('stDays').textContent = Math.max(1, Math.ceil((Date.now() - first.getTime()) / 86400000));
          } else {
            $('stDays').textContent = '1';
          }
        });
      });
  }

  /* ================= 头像（文件存储） ================= */
  let avatarPath = null;
  function extOf(type) {
    if (type === 'image/png') return '.png';
    if (type === 'image/jpeg') return '.jpg';
    if (type === 'image/webp') return '.webp';
    return '.png';
  }
  async function showAvatar() {
    if (!avatarPath) return;
    const r = await cloud.storage.createSignedUrl(avatarPath, 3600);
    if (r.error) return;
    const url = r.data && (r.data.signedUrl || r.data.url || (typeof r.data === 'string' ? r.data : null));
    if (url) {
      $('userAvatar').src = url;
      $('userAvatar').hidden = false;
      $('avatarFallback').hidden = true;
    }
  }
  $('userAvatar').addEventListener('click', () => $('avatarInput').click());
  $('avatarFallback').addEventListener('click', () => $('avatarInput').click());
  $('avatarInput').addEventListener('change', async () => {
    const f = $('avatarInput').files[0];
    $('avatarInput').value = '';
    if (!f || !currentUser) return;
    if (!/^image\//.test(f.type)) return;
    if (f.size > 2 * 1024 * 1024) return;
    avatarPath = cloud.storage.userPath(currentUser.id, 'avatar' + extOf(f.type));
    const up = await cloud.storage.upload(avatarPath, f, { contentType: f.type, upsert: true });
    if (up.error) return;
    showAvatar();
  });

  /* ================= 登录后初始化 ================= */
  function bootUserData() {
    loadProfile();
    loadPlans();
    loadCheckins();
    showAvatar();
    loadModels();
    if (!curId) newChat();
  }

  /* ================= 启动：会话门控 ================= */
  async function boot() {
    const { data: session, error } = await cloud.auth.getSession();
    if (error || !session || !session.user) { showAuth(); return; }
    currentUser = session.user;
    showApp(session.user.email);
  }
  cloud.auth.onAuthStateChange((event, session) => {
    if (event === 'SIGNED_OUT') {
      currentUser = null; profileRow = null; avatarPath = null;
      showAuth();
      return;
    }
    if (session && session.user && (!currentUser || currentUser.id !== session.user.id)) {
      currentUser = session.user;
      showApp(session.user.email);
    }
  });
  /* ================= 开场动画（视频） ================= */
  (function intro() {
    const iv = $('introView');
    if (!iv) return;
    const v = $('introVideo');
    let closed = false;
    const done = () => {
      if (closed) return;
      closed = true;
      iv.classList.add('hide');
      setTimeout(() => iv.remove(), 700);
    };
    $('introSkip').addEventListener('click', done);
    if (v) {
      v.addEventListener('ended', done);
      v.addEventListener('error', done);
      // 触摸/点击视频时尝试播放（部分内置浏览器禁止 autoplay）
      iv.addEventListener('touchstart', () => { const p = v.play(); if (p && p.catch) p.catch(() => {}); }, { passive: true });
      iv.addEventListener('click', () => { const p = v.play(); if (p && p.catch) p.catch(() => {}); });
      const p = v.play();
      if (p && p.catch) p.catch(() => {});
      // 看门狗：2.5 秒后仍未真正开播（如编码不支持/禁止自动播放）→ 自动退出，绝不黑屏卡死
      setTimeout(() => { if (!closed && (v.paused || v.currentTime < 0.1)) done(); }, 2500);
      // 兜底：视频异常时 15 秒后强制关闭
      setTimeout(done, 15000);
    } else {
      setTimeout(done, 2000);
    }
  })();

  boot();
})();
