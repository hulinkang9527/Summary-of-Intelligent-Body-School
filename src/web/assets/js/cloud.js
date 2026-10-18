/* cloud.js —— WorkBuddy 云服务接入：认证 / 数据库 / 文件存储（一次初始化，全站共用） */
(function () {
  'use strict';
  // publicConfig 由云服务开通时返回（仅含应用标识，无敏感凭据）
  var PUBLIC_CONFIG = {
    endpoint: 'https://life-planner-agent.app.workbuddy.host',
    publishableKey: 'wbpk_a2c0osMTmVHdPPYU68WHoN_v6qhzPPOWwfV76wkeaYlSMaZ3AOZEKM4',
  };

  if (!window.WorkBuddyCloud) {
    console.error('云服务 SDK 未加载');
    return;
  }

  var cloud = WorkBuddyCloud.createWorkBuddyCloud({
    endpoint: PUBLIC_CONFIG.endpoint,
    publishableKey: PUBLIC_CONFIG.publishableKey,
  });

  window.MTCloud = cloud;
})();
