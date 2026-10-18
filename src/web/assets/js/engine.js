/**
 * engine.js —— 「明途」人生规划 AI 助手 · 检索与推理内核
 *
 * 组成：
 *   1. 中文分词（bigram + 场景词典）
 *   2. BM25 倒排检索（标题加权）
 *   3. 场景路由：把自然语言问题映射到原书章节
 *   4. 意图识别：急症 / 法律 / 待遇 / 第一步 / 决策 / 通用
 *   5. 安全护栏：危机干预、法律红线、隐私边界
 *   6. ROI 评估：照《高性价比人生指南》的三项成本 × 收益量级算法
 *   7. 阶段计划生成
 *   8. 可选 LLM 增强（OpenAI 兼容接口），未配置时全程本地推理
 */
(function (global) {
  'use strict';

  const KB = global.HLTB_KB || { entries: [], chapters: [], stats: {} };
  const E = KB.entries;

  /* ------------------------------------------------------------------ *
   * 1. 分词
   * ------------------------------------------------------------------ */
  const STOP = new Set(('的 了 是 在 我 有 和 就 不 人 都 一 一个 上 也 很 到 说 要 去 你 会 着 没有 看 好 自己 这 那 吗 呢 吧 啊 怎么 什么 如何 哪些 那个 这个 的话 可以 应该 想 让 给 对 从 被 把 与 及 或 等 之 其 为 以 于 而 中 后 前 里 时候 一下 一些 需要 可能 但是 因为 所以 如果 就是 还是 或者 比如 例如 关于 对于 通过 进行 以及 那么 这样 那样的')
    .split(/\s+/));

  /** 中文分词：抽取英文词 + 连续数字 + 2-gram（含少量 3-gram 命中词典时） */
  function tokenize(s) {
    if (!s) return [];
    const out = [];
    const lower = String(s).toLowerCase();
    // 英文/数字
    (lower.match(/[a-z][a-z0-9+#.\-]{1,}|[0-9]+(\.[0-9]+)?/g) || []).forEach((w) => {
      if (w.length > 1) out.push(w);
    });
    // 中文串
    const zh = lower.match(/[\u4e00-\u9fa5]+/g) || [];
    zh.forEach((seg) => {
      const n = seg.length;
      if (n === 1) {
        if (!STOP.has(seg)) out.push(seg);
        return;
      }
      for (let i = 0; i < n - 1; i++) {
        const g = seg.slice(i, i + 2);
        if (!STOP.has(g)) out.push(g);
      }
      // 3-gram 命中场景词典时保留，提升「劳动仲裁」这类长词权重
      if (n >= 3) {
        for (let i = 0; i < n - 2; i++) {
          const g = seg.slice(i, i + 3);
          if (SCENE_TERMS.has(g)) out.push(g);
        }
      }
    });
    return out;
  }

  /* ------------------------------------------------------------------ *
   * 2. 场景词典 & 章节路由
   *    把用户口语 → 原书章节 + 扩展检索词
   * ------------------------------------------------------------------ */
  const SCENES = [
    { id: 'health_risk', name: '健康与早死风险', sec: [1, 2], kw: ['早死', '猝死', '养生', '健康', '体检', '筛查', '疫苗', '抽烟', '吸烟', '戒烟', '喝酒', '饮酒', '喝酒', '熬夜', '久坐', '睡眠', '运动', '糖尿病', '血压', '高血压', '血脂', '减肥', '饮食', '低钠盐', '血糖', '慢性病'],
      ext: ['总死亡率', '风险下降', '筛查', '疫苗', '戒烟', '低钠盐', '久坐', '午睡'] },
    { id: 'energy_time', name: '精力与时间', sec: [3, 4], kw: ['精力', '时间管理', '拖延', '效率', '分心', '打断', '多任务', '通勤', '开会', '专注', '浪费时间', '摸鱼'],
      ext: ['精力', '打断', '拖延', '无收益', '沉没成本', '通勤', '会议'] },
    { id: 'money', name: '花钱与理财', sec: [5, 6], kw: ['理财', '存钱', '省钱', '保险', '基金', '费率', '订阅', '彩票', '个人养老金', '消费', '智商税', '保健品', '买车险', '预付款', '直播带货', '盲盒', '投资'],
      ext: ['费率', '利息', '保险', '订阅', '反面清单', '智商税', '预付款'] },
    { id: 'poverty', name: '没钱的时候怎么活', sec: [7], kw: ['失业', '没钱', '负债', '欠薪', '找工作', '低保', '救助', '补贴', '求助', '断供', '生活费'],
      ext: ['救助', '补贴', '失业', '欠薪', '劳动监察', '临时救助'] },
    { id: 'law', name: '法律与人身自由', sec: [8, 9, 11], kw: ['犯法', '违法', '红线', '被抓', '拘留', '判刑', '起诉', '被告', '报警', '诈骗', '被骗', '担保', '彩礼', '婚前财产', '借条', '诉讼', '失信', '网暴', '造谣', '外挂', '爬虫', '兼职', '洗钱', '赌博', '偷拍', '无人机', '卖器官'],
      ext: ['刑法', '责任', '受案回执', '不立案', '反诈', '担保', '彩礼'] },
    { id: 'relation', name: '恋爱与婚姻', sec: [10], kw: ['恋爱', '结婚', '相亲', '择偶', '异地恋', '分手', '离婚', '婚检', '领证', '彩礼', '对象'],
      ext: ['择偶', '关系质量', '登记', '婚检', '共同债务', '退出成本'] },
    { id: 'startup', name: '创业与做生意', sec: [12], kw: ['创业', '开店', '做生意', '开公司', '注册公司', '个体户', '许可证', '纳税', '发票', '合同', '合伙', '量产', '进货'],
      ext: ['注册登记', '许可证', '纳税申报', '合同', '商标', '版权'] },
    { id: 'emergency', name: '紧急情况处置', sec: [13], kw: ['急救', '心脏骤停', '心肺复苏', 'cpr', 'aed', '溺水', '触电', '火灾', '大出血', '中风', '卒中', '心梗', '昏迷', '窒息', '中毒', '烧伤', '烫伤', '中暑', '迷路', '蛇咬', '过敏', '癫痫', '骨折', '地震', '失温', '高原'],
      ext: ['120', '119', '现场', '急救', '心搏骤停', '卒中', '止血', '不摇晃'] },
    { id: 'account', name: '账号与信息安全', sec: [14], kw: ['账号被盗', '密码', '二次验证', '手机丢了', '盗刷', '信息泄露', '隐私', '人脸识别', 'sim卡', '诈骗短信'],
      ext: ['二次验证', '密码管理器', 'SIM', '盗刷', '权限'] },
    { id: 'housing', name: '租房与买房', sec: [15], kw: ['租房', '买房', '押金', '房东', '中介', '长租公寓', '资金监管', '产权', '隔断房', '退租'],
      ext: ['押金', '腾退', '资金监管', '买卖不破租赁', '产权'] },
    { id: 'chronic', name: '慢性病管理', sec: [16], kw: ['慢性病', '长期吃药', '服药', '门诊慢特病', '复查', '偏方', '家庭医生', '痛风', '肾结石', '高血压'],
      ext: ['依从', '长期处方', '跨省结算', '并发症'] },
    { id: 'elder', name: '家里有老人', sec: [17], kw: ['老人', '父母', '养老', '监护', '遗嘱', '养老诈骗', '以房养老', '压疮', '失能'],
      ext: ['意定监护', '遗嘱', '养老诈骗', '长期护理保险'] },
    { id: 'parenting', name: '养育与教育', sec: [18, 20, 30], kw: ['生孩子', '养孩子', '育儿', '产假', '生育津贴', '奶粉', '辅食', '疫苗', '上学', '孩子', '校园欺凌', '近视', '作业', '儿童'],
      ext: ['育儿补贴', '生育津贴', '安全睡眠', '免疫规划', '欺凌', '户外'] },
    { id: 'career', name: '在职离职与工伤', sec: [19], kw: ['加班费', '加班', '年假', '被裁', '裁员', '辞退', '离职', 'n+1', '2n', '补偿金', '工伤', '试用期', '职业病', '社保', '劳动仲裁', '竞业'],
      ext: ['加班费', '年休假', '经济补偿', '工伤认定', '劳动能力鉴定', '仲裁'] },
    { id: 'abroad', name: '出国与留学', sec: [21, 32], kw: ['出国', '旅行', '签证', '留学', '境外', '领事', '护照', '出国打工', '汇率', '移民'],
      ext: ['12308', '领事保护', '留学认证', '打工时数', 'OSHC'] },
    { id: 'leisure', name: '放松与减压', sec: [22], kw: ['放松', '减压', '压力', '焦虑', '抑郁', 'ktv', '网吧', '剧本杀', '密室', '娱乐'],
      ext: ['正念', '呼吸', '社交', '绿地', '涉毒'] },
    { id: 'skill', name: '学什么技能划算', sec: [23], kw: ['学什么', '技能', '考证', '培训', '学历', '读书', '考研', '自考', '专升本', '职称', '职业规划', '转行'],
      ext: ['教育回报率', '培训补贴', '技能等级', '紧缺职业', '分散练习', '职称'] },
    { id: 'medical', name: '看病与报销', sec: [24], kw: ['看病', '挂号', '医院', '报销', '医保', '异地就医', '急诊', '转诊', '伤残鉴定', '残疾人证', '红包'],
      ext: ['分级诊疗', '起付线', '报销比例', '急诊预检', '应急救助', '伤残鉴定'] },
    { id: 'death', name: '身后事办理', sec: [25], kw: ['去世', '身后事', '死亡证明', '火化', '殡葬', '公积金', '遗产', '注销户口'],
      ext: ['死亡证明', '遗体接运', '殡葬', '公积金余额'] },
    { id: 'platform', name: '做网站与平台', sec: [26], kw: ['做网站', '做平台', 'app', '备案', 'icp', '服务器', '内容治理', '实名', '数据出境', '小程序'],
      ext: ['ICP备案', '许可', '实名', '通知删除', '数安法'] },
    { id: 'pregnancy', name: '怀孕与生产', sec: [27], kw: ['怀孕', '生产', '生孩子', '产检', '叶酸', '剖宫产', '无痛分娩', '出生证明', '坐月子', '备孕'],
      ext: ['叶酸', '建册', '产检', '生育保险', '出生医学证明'] },
    { id: 'body', name: '外形与身体', sec: [28], kw: ['医美', '整容', '减肥药', '节食', '进食障碍', '类固醇', '变好看', '抽脂', '填充'],
      ext: ['医美', '主诊医师', '西布曲明', '合成代谢类固醇'] },
    { id: 'crisis', name: '重大打击与哀伤', sec: [29, 1], kw: ['亲人去世', '丧亲', '被裁', '重病', '诊断', '重大打击', '离婚', '丧偶', '哀伤', '活不下去', '不想活', '自杀', '轻生', '抑郁', '崩溃', '撑不住'],
      ext: ['12356', '头一个月', '第一周', '哀伤', '应激期', '不可逆的决定'] },
    { id: 'youth', name: '十八岁之后的路', sec: [31], kw: ['十八岁', '当兵', '参军', '特岗教师', '消防员', '军队文职', '成人高考', '开放大学', '灵活就业', '骑手', '远程工作'],
      ext: ['兵役登记', '定向考录', '自考', '公费师范生', '灵活就业'] },
    { id: 'disability', name: '残疾之后怎么活', sec: [33], kw: ['残疾', '残疾人', '轮椅', '助听器', '导盲犬', '无障碍', '残疾证', '康复', '精神障碍'],
      ext: ['残疾人证', '无障碍改造', '按比例就业', 'C5驾照', '康复救助'] },
  ];
  const SCENE_TERMS = new Set();
  SCENES.forEach((s) => {
    s.kw.forEach((k) => { if (k.length >= 3) SCENE_TERMS.add(k); });
    s.ext.forEach((k) => { if (k.length >= 3) SCENE_TERMS.add(k); });
    s.kw.forEach((k) => { if (k.length === 2) SCENE_TERMS.add(k); });
  });

  /* ------------------------------------------------------------------ *
   * 3. BM25 倒排索引
   * ------------------------------------------------------------------ */
  const INV = Object.create(null);      // term -> [[docIdx, weight], ...]
  const DOCLEN = new Float64Array(E.length);
  let AVGDL = 0;

  function buildIndex() {
    for (let i = 0; i < E.length; i++) {
      const e = E[i];
      const tf = Object.create(null);
      // 标题权重 ×3，说人话 ×1.5，全文 ×1
      tokenize(e.title).forEach((t) => { tf[t] = (tf[t] || 0) + 3; });
      tokenize(e.plain).forEach((t) => { tf[t] = (tf[t] || 0) + 1.5; });
      tokenize(e.text).forEach((t) => { tf[t] = (tf[t] || 0) + 1; });
      tokenize(e.secName).forEach((t) => { tf[t] = (tf[t] || 0) + 1.5; });
      let len = 0;
      for (const t in tf) {
        len += tf[t];
        (INV[t] || (INV[t] = [])).push([i, tf[t]]);
      }
      DOCLEN[i] = len || 1;
    }
    let s = 0;
    for (let i = 0; i < E.length; i++) s += DOCLEN[i];
    AVGDL = s / (E.length || 1);
  }
  buildIndex();

  const K1 = 1.2, B = 0.75, N = E.length;
  const IDF = Object.create(null);
  function idf(t) {
    if (IDF[t] !== undefined) return IDF[t];
    const d = (INV[t] || []).length;
    return (IDF[t] = Math.log(1 + (N - d + 0.5) / (d + 0.5)));
  }

  /** BM25 检索。filters: {secs, evidence, ratio, scope, cost} */
  function search(query, opt) {
    opt = opt || {};
    const terms = tokenize(query);
    if (!terms.length) return [];
    const tfq = Object.create(null);
    terms.forEach((t) => { tfq[t] = (tfq[t] || 0) + 1; });

    const score = new Float64Array(N);
    for (const t in tfq) {
      const post = INV[t];
      if (!post) continue;
      const w = idf(t) * (1 + Math.log(tfq[t]));
      for (let p = 0; p < post.length; p++) {
        const [d, f] = post[p];
        score[d] += w * ((f * (K1 + 1)) / (f + K1 * (1 - B + B * (DOCLEN[d] / AVGDL))));
      }
    }

    let hits = [];
    for (let i = 0; i < N; i++) if (score[i] > 0) hits.push({ e: E[i], s: score[i] });
    if (opt.secs && opt.secs.length) {
      // 场景命中章节加权 1.8 倍
      const set = new Set(opt.secs);
      hits.forEach((h) => { if (set.has(h.e.sec)) h.s *= 1.8; });
      if (hits.length < 5) {
        // 召回不足时补入该章节性价比最高的条目
        E.filter((e) => set.has(e.sec) && !hits.some((h) => h.e.id === e.id))
          .sort((a, b) => b.cs - a.cs)
          .slice(0, 5)
          .forEach((e) => hits.push({ e, s: 0.01 }));
      }
    }
    // 过滤
    hits = hits.filter((h) => {
      const e = h.e;
      if (opt.evidence && opt.evidence.length && !opt.evidence.includes(e.evidence)) return false;
      if (opt.ratio && opt.ratio.length && !opt.ratio.includes(e.ratio)) return false;
      if (opt.scope && opt.scope.length && !opt.scope.includes(e.scope)) return false;
      return true;
    });
    // 排序：相关度为主，性价比/证据等级做同分微调
    const RANK = { 极高: 3, 高: 2, 一般: 1 };
    const EV = { A: 3, B: 2, C: 1 };
    hits.sort((a, b) => (b.s - a.s) || (RANK[b.e.ratio] - RANK[a.e.ratio]) || (EV[b.e.evidence] - EV[a.e.evidence]));
    return hits.slice(0, opt.limit || 12);
  }

  /* ------------------------------------------------------------------ *
   * 4. 意图识别
   * ------------------------------------------------------------------ */
  const PAT = {
    suicide: /自杀|轻生|不想活|活不下去|结束生命|了结|想死|一了百了|跳楼|割腕|安眠药/,
    emergency: /心脏骤停|没有呼吸|没呼吸|停止呼吸|大出血|大咯血|昏迷|意识不清|溺水|触电|火灾|着火了|煤气中毒|一氧化碳|卒中|中风|嘴歪|心梗|心梗|胸痛|胸口疼|胸口痛|胸闷|呼吸困难|喘不上气|癫痫|抽搐|严重过敏|过敏性休克|窒息|卡喉|中暑|高热惊厥|骨折|蛇咬|被咬|烧烫伤|烫伤|烧伤|地震|失温|迷路|高原|车祸|出车祸|撞了|吐血|便血|尿血|剧烈头痛|霹雳样|冒冷汗|出冷汗|晕倒|昏倒|不省人事|误服|吃错药|被扎|异物/,
    legal: /犯法|违法|犯罪|红线|被抓|拘留|坐牢|判刑|起诉|被告|报警|立案|诈骗|被骗|传唤|取保|赔偿|担责|侵权|合规吗|合法吗|担保|做保|借条|欠条|彩礼|婚前财产|合同|签字|签了|能签|该签|被指控|被举报|报案|追诉|刑责|刑事责任|行政处罚|罚款|连坐/,
    decide: /该不该|值不值|要不要|划不划算|划算|怎么选|帮我决定|帮我选|哪个好|如何选择|值得吗|应不应该|能签吗|该签吗|好不好|行不行/,
    benefit: /能领|领什么|补贴|报销|待遇|赔偿金|补偿|抚恤|津贴|救助|免费|退税|怎么领/,
    first: /先做什么|第一步|怎么办|如何处理|应对|紧急/,
    plan: /规划|计划|路线图|怎么做计划|阶段|目标|多久能|怎么实现/,
  };
  // 危险场景词命中时，无论问法如何都优先按急症/法律处理
  const EMERG_HINT = /胸口|胸痛|呼吸|出血|昏迷|意识|溺水|触电|火灾|着火|中毒|卒中|中风|心梗|抽搐|窒息|卡住|烫伤|烧伤|骨折|被咬|车祸|吐血|便血|尿血|剧痛/;
  const LEGAL_HINT = /担保|保人|借条|欠条|起诉|报警|立案|拘留|传唤|判刑|骗|合同|签字|彩礼|婚前|侵权|赔偿|犯法|违法/;

  function detectIntent(q) {
    const s = String(q);
    if (PAT.suicide.test(s)) return 'suicide';
    if (PAT.emergency.test(s) || EMERG_HINT.test(s)) return 'emergency';
    if (PAT.benefit.test(s)) return 'benefit';
    if (PAT.legal.test(s) || LEGAL_HINT.test(s)) return 'legal';
    if (PAT.decide.test(s)) return 'decide';
    if (PAT.first.test(s)) return 'first';
    if (PAT.plan.test(s)) return 'plan';
    return 'general';
  }

  function routeScenes(q) {
    const s = String(q).toLowerCase();
    const scored = SCENES.map((sc) => {
      let hit = 0;
      sc.kw.forEach((k) => { if (s.indexOf(k.toLowerCase()) >= 0) hit += k.length >= 3 ? 2 : 1; });
      sc.ext.forEach((k) => { if (s.indexOf(k.toLowerCase()) >= 0) hit += 1; });
      return { sc, hit };
    }).filter((x) => x.hit > 0).sort((a, b) => b.hit - a.hit);
    return scored.slice(0, 3);
  }

  /* ------------------------------------------------------------------ *
   * 5. 安全护栏
   * ------------------------------------------------------------------ */
  const GUARD = {
    suicide: {
      level: 'crisis', title: '请先联系专业帮助',
      body: '你提到的内容超出了本工具能处理的范围。请立即拨打全国心理援助热线 <b>12356</b>（24 小时）；如果有立即的行动冲动，请拨打 <b>120</b> 或 <b>110</b>，并联系一位可以马上到你身边的家人或朋友。<br>本助手不做劝导式分析、不评价你的动机，只做一件事：把求助渠道给你。',
      secs: [1, 29],
    },
    emergency: {
      level: 'crisis', title: '这是急症，先按现场处置，不要先做性价比分析',
      body: '先打 <b>120</b>（医疗）/ <b>119</b>（火灾）/ <b>110</b>（治安与危险），再按下面第 13 节的条目做现场第一个动作。',
      secs: [13],
    },
    legal: {
      level: 'warn', title: '可能涉及法律责任，先看这几条红线',
      body: '本助手只给通用口径，不替代律师。如果已经进入传唤、拘留、起诉等程序，请直接找执业律师；下面是知识库中与本问题相关的法律条目。',
      secs: [8, 9, 11],
    },
  };

  /* ------------------------------------------------------------------ *
   * 6. 结构化问答（核心推理）
   * ------------------------------------------------------------------ */
  function answer(query, opt) {
    opt = opt || {};
    const intent = detectIntent(query);
    const scenes = routeScenes(query);

    // 危机优先：不做性价比分析
    if (intent === 'suicide' || intent === 'emergency') {
      const g = GUARD[intent];
      const hits = search(query, { secs: g.secs, limit: 6 });
      return {
        intent, guard: g, scenes,
        conclusion: intent === 'suicide'
          ? '先求助，再谈别的。'
          : '先打急救电话并按现场处置，其他判断都往后放。',
        hits, groups: [],
      };
    }

    const secs = scenes.length ? scenes[0].sc.sec : [];
    let hits = search(query, { secs, limit: opt.limit || 10 });
    if (hits.length < 4) hits = search(query, { limit: opt.limit || 10 });

    // 按口径分组（原书：四种口径不互相折算）
    const gmap = new Map();
    hits.forEach((h) => {
      const k = h.e.scope || '其他';
      if (!gmap.has(k)) gmap.set(k, []);
      gmap.get(k).push(h);
    });
    const groups = [...gmap.entries()].map(([scope, list]) => ({ scope, list }));

    const guard = intent === 'legal' ? GUARD.legal : null;
    return { intent, guard, scenes, conclusion: buildConclusion(query, intent, hits, groups), hits, groups };
  }

  const RANK = { 极高: 3, 高: 2, 一般: 1 };

  function buildConclusion(query, intent, hits, groups) {
    if (!hits.length) {
      return `知识库里没有直接对应「${esc(query)}」的条目。本助手不凭记忆补数字，也不拿常识冒充书里的内容。可以换个说法，或者直接到第 5 步的知识库里按关键词、章节、证据等级自行检索。`;
    }
    const top = hits[0].e;
    const nHigh = hits.filter((h) => h.e.ratio === '极高').length;
    const nA = hits.filter((h) => h.e.evidence === 'A').length;
    const scopeTxt = groups.map((g) => `${g.scope} ${g.list.length} 条`).join('、');
    const head = {
      decide: '这件事的投入产出比，可以拆成下面几步看。',
      first: '先把第一步做了，后面的顺序按性价比排。',
      benefit: '能领什么、怎么领，按下面的顺序办。',
      legal: '先看红线，再谈收益。',
      plan: '按性价比从高到低，分阶段落。',
      general: '下面按性价比从高到低给出可执行的动作。',
    }[intent] || '下面按性价比从高到低给出可执行的动作。';

    return `${head}知识库命中 ${hits.length} 条相关条目（其中性价比「极高」${nHigh} 条、证据等级 A 级 ${nA} 条；口径分布：${scopeTxt}，不同口径不互相折算）。<br>首条建议：<b>${esc(top.title)}</b>——${esc(top.plain || top.benefit).slice(0, 120)}<br><span class="muted">出处：第 ${top.sec} 节第 ${top.no} 条（${esc(top.secName)}）</span>`;
  }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  }

  /* ------------------------------------------------------------------ *
   * 7. ROI 评估：用户自定义选项的投入产出比
   * ------------------------------------------------------------------ */
  const COST_W = { money: { '0': 0, '少': 1, '多': 2 }, time: { '少': 0, '中': 1, '多': 2 }, will: { '否': 0, '些': 1, '是': 2 } };

  function costScore(c) {
    return (COST_W.money[c.money] || 0) + (COST_W.time[c.time] || 0) + (COST_W.will[c.will] || 0);
  }
  function ratioOf(level, cs) {
    if (level === '大') return cs === 0 ? '极高' : (cs <= 2 ? '高' : '一般');
    if (level === '中') return cs === 0 ? '高' : '一般';
    return '一般';
  }

  /**
   * 评估一个选项的投入产出比。
   * option: {name, money, time, will, level, scope, horizon}
   * 返回：{cs, ratio, benchmark, advice[], refs[]}
   */
  function evaluateOption(opt) {
    const cs = costScore(opt);
    const ratio = ratioOf(opt.level, cs);
    // 同口径分布对标
    const same = E.filter((e) => e.scope === opt.scope);
    const dist = { 极高: 0, 高: 0, 一般: 0 };
    same.forEach((e) => dist[e.ratio]++);
    const total = same.length || 1;
    const pct = Math.round(((dist['极高'] + dist['高']) / total) * 100);
    const rank = ratio === '极高' ? 1 : ratio === '高' ? 2 : 3;

    const advice = [];
    if (cs === 0) advice.push('三项成本都是零：不花钱、不额外占时间、不需要毅力。按原书口径，这类事只要收益落在「大」就是性价比「极高」，应当直接做，不需要再权衡。');
    else {
      if (opt.money === '多') advice.push('现金成本偏高。原书的做法是把它拆开：能不能先做「花钱少、收益一样落在同一档」的替代项（知识库里同口径下性价比更高的条目）。');
      if (opt.time === '多') advice.push('时间成本偏高。注意原书算「时间」时算的是持续占用的时间，不是一次性的；如果是一次性的，实际负担要小得多。');
      if (opt.will === '是') advice.push('依赖毅力。原书对「意志力会用完」这个说法持保留态度（第 6 节），建议不要靠硬扛，改成改环境、加承诺装置。');
    }
    if (opt.level === '小') advice.push('收益量级判为「小」时，按原书的界线通常只量到中间指标、没量到最终结果。如果这件事对你个人很重要，可以照做，但要清楚它是「一般」档，不属于高性价比。');
    if (rank === 3) advice.push('落在「一般」档不等于不该做——全书 615 条都是建议做的，只是这一档那笔花销得你自己掂量。');
    advice.push(`同口径（换${opt.scope}）下，知识库共 ${total} 条，其中性价比「极高/高」占 ${pct}%。你的选项处在第 ${rank} 档。`);

    const refs = search([opt.name, opt.scope].join(' '), { scope: [opt.scope], limit: 5 });
    return { cs, ratio, dist, total, pct, rank, advice, refs };
  }

  /* ------------------------------------------------------------------ *
   * 8. 阶段计划生成
   * ------------------------------------------------------------------ */
  const PHASES = [
    { key: 'D30', name: '第 1 阶段 · 0–30 天', theme: '清障与启动', days: 30 },
    { key: 'D90', name: '第 2 阶段 · 31–90 天', theme: '建立可重复的系统', days: 90 },
    { key: 'D180', name: '第 3 阶段 · 91–180 天', theme: '扩大到瓶颈', days: 180 },
    { key: 'D365', name: '第 4 阶段 · 181–365 天', theme: '固化与复盘', days: 365 },
  ];

  /**
   * 生成阶段计划。
   * goal: {title, metric, deadline, scope}
   * options: 已选定的方案名
   * 依据：知识库中与该目标相关的「极高/高」档条目，按阶段摊派
   */
  function buildPlan(goal, scope) {
    const q = [goal.title, goal.metric, (scope || '')].filter(Boolean).join(' ');
    let hits = search(q, { limit: 20 });
    hits = hits.filter((h) => h.e.ratio !== '一般');
    if (hits.length < 6) hits = search(goal.title || '', { limit: 20 });

    const plan = PHASES.map((p, i) => ({ ...p, items: [], milestone: '' }));
    // 低成本、高收益的先做；成本高的后置
    hits.sort((a, b) => a.e.cs - b.e.cs || RANK[b.e.ratio] - RANK[a.e.ratio]);
    hits.forEach((h, idx) => {
      const slot = h.e.cs === 0 ? 0 : (h.e.cs <= 2 ? (idx % 2 ? 1 : 2) : 3);
      plan[slot].items.push(h.e);
    });
    plan.forEach((p, i) => {
      p.items = p.items.slice(0, 6);
      p.milestone = i === 0
        ? `把「${goal.title || '目标'}」拆成可勾选的清单，至少完成 3 项零成本动作`
        : i === 1 ? '形成稳定的周节奏：连续 4 周完成率 ≥ 70%'
          : i === 2 ? `关键指标出现可测变化：${goal.metric || '自定指标'}`
            : `达成「${goal.title || '目标'}」并完成一次完整复盘`;
    });
    return plan;
  }

  /* ------------------------------------------------------------------ *
   * 9. 复盘分析
   * ------------------------------------------------------------------ */
  function review(data) {
    // data: {planned, done, obstacles:[], rating}
    const rate = data.planned ? Math.round((data.done / data.planned) * 100) : 0;
    const out = { rate, level: '', diagnosis: [], adjust: [] };
    if (rate >= 85) { out.level = '优'; out.diagnosis.push('执行率健康，计划颗粒度与你的实际产能匹配。'); out.adjust.push('下一阶段把难度上调 10–20%，只加一条新动作，避免一次性加压过多。'); }
    else if (rate >= 60) { out.level = '良'; out.diagnosis.push('执行率处于正常波动区间，通常不是意志力问题，而是计划排得太满或环境没改。'); out.adjust.push('把每条动作改写成「几点、在哪、遇到什么就做什么」（第 4 节做法），可执行性比重新立目标有效。'); }
    else if (rate >= 30) { out.level = '待改进'; out.diagnosis.push('计划明显超出实际产能。原书第 3、4 节指出，这类差距多半来自打断、多任务和沉没成本，而不是不够努力。'); out.adjust.push('本周只保留 2 条动作，其余移入「以后再说」；先拿到一次完成体验。'); }
    else { out.level = '需重启'; out.diagnosis.push('执行率过低，先不要加新目标。'); out.adjust.push('回到第 1 阶段，只做三项零成本动作（知识库里性价比「极高」那一档），先把节奏拿回来。'); }

    const obs = data.obstacles || [];
    if (obs.indexOf('时间不够') >= 0) out.adjust.push('时间不够：核对时间账（第 4 节）——把「不产生收益但占用时间」的项目列出来砍掉，而不是压缩睡眠。');
    if (obs.indexOf('坚持不下来') >= 0) out.adjust.push('坚持不下来：改用承诺装置改环境（第 4 节），别指望意志力（第 6 节）。');
    if (obs.indexOf('不知道从哪下手') >= 0) out.adjust.push('不知道从哪下手：把动作缩到「2 分钟内能开始」的大小，先做再优化。');
    if (obs.indexOf('被打断太多') >= 0) out.adjust.push('被打断太多：按第 3 节的打断治理条目处理，先解决通知和环境，不是先解决效率工具。');
    if (obs.indexOf('钱不够') >= 0) out.adjust.push('钱不够：优先取用第 7 节的救助、补贴与维权路径，以及第 5 节里「不花钱也能省下钱」的条目。');
    return out;
  }

  /* ------------------------------------------------------------------ *
   * 10. 可选 LLM 增强
   * ------------------------------------------------------------------ */
  function llmConfig() {
    try { return JSON.parse(localStorage.getItem('mt_llm') || 'null'); } catch (e) { return null; }
  }
  function saveLlmConfig(cfg) { localStorage.setItem('mt_llm', JSON.stringify(cfg || null)); }

  /** 用检索到的条目作为上下文，调用 OpenAI 兼容接口 */
  async function askLLM(query, hits, cfg) {
    const ctx = hits.slice(0, 8).map((h) => {
      const e = h.e;
      return `【第${e.sec}节第${e.no}条 · ${e.title}】成本：${e.costText}｜收益：${e.benefit}｜证据等级：${e.evidence}｜备注：${e.remark}`;
    }).join('\n');
    const sys = '你是「明途」人生规划助手。严格依据给定的知识库条目回答，每条结论都要注明「第X节第Y条」。'
      + '知识库里没有的内容就说没写，不要凭记忆补数字、补法条。四种口径（寿命/时间精力/金钱/人身自由）不互相折算。'
      + '不给个性化投资建议，不替代医生和律师。语气克制，简体中文，不用感叹号。';
    const body = {
      model: cfg.model || 'gpt-4o-mini',
      messages: [
        { role: 'system', content: sys },
        { role: 'user', content: `知识库条目：\n${ctx}\n\n用户问题：${query}` },
      ],
      temperature: 0.3,
    };
    const res = await fetch((cfg.baseUrl || 'https://api.openai.com/v1').replace(/\/$/, '') + '/chat/completions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + cfg.apiKey },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error('LLM 接口返回 ' + res.status);
    const j = await res.json();
    return j.choices && j.choices[0] && j.choices[0].message.content;
  }

  /* ------------------------------------------------------------------ *
   * 导出
   * ------------------------------------------------------------------ */
  global.MTEngine = {
    KB, ENTRIES: E, SCENES, tokenize, search, detectIntent, routeScenes,
    answer, evaluateOption, buildPlan, review, costScore, ratioOf,
    llmConfig, saveLlmConfig, askLLM, esc,
    stats: KB.stats, chapters: KB.chapters,
  };
})(typeof window !== 'undefined' ? window : globalThis);
