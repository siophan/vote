/* 龄花里运营后台 — vanilla SPA over /api/v1/admin (X-Admin-Token). */
(() => {
  "use strict";

  const API = "/api/v1";
  const TOKEN_KEY = "lhl_admin_token";
  const PAGE_SIZE = 20;
  const REJECT_REASONS = ["视频链接打不开", "非本人作品", "内容与赛事不符", "重复投稿", "画面或声音不清晰"];
  const $ = (sel, root = document) => root.querySelector(sel);
  const main = $("#main");

  // ---------- utils ----------

  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmtTime = (iso) => (iso ? new Date(iso).toLocaleString("zh-CN", { hour12: false }) : "");
  const safeUrl = (u) => (/^https?:\/\//i.test(u || "") ? u : "");
  const addressText = (a) => (a ? `${a.name} ${a.phone}　${a.province}${a.city}${a.district}${a.detail}` : "");

  function storage(fn) {
    try { return fn(window.localStorage); } catch { return null; }
  }
  let token = storage((s) => s.getItem(TOKEN_KEY)) || "";

  let toastTimer;
  function toast(msg, isErr = false) {
    const el = $("#toast");
    el.textContent = msg;
    el.className = "toast" + (isErr ? " err" : "");
    el.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.hidden = true; }, isErr ? 4000 : 2200);
  }

  async function copy(text) {
    try {
      await navigator.clipboard.writeText(text);
      toast("已复制");
    } catch {
      window.prompt("复制下面的内容：", text);
    }
  }

  class ApiError extends Error {}

  async function api(path, { method = "GET", body, params } = {}) {
    const url = new URL(API + path, location.origin);
    Object.entries(params || {}).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v);
    });
    const res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json", "X-Admin-Token": token },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const data = await res.json().catch(() => null);
    if (res.status === 403 && path.startsWith("/admin")) {
      logout("令牌无效或已更换，请重新输入");
      throw new ApiError("管理员令牌无效");
    }
    if (!res.ok) throw new ApiError((data && data.detail) || `请求失败（${res.status}）`);
    return data;
  }

  /** Run an async action with the button disabled; show the error inline (or as a toast). */
  async function busy(btn, errEl, fn) {
    if (btn) btn.disabled = true;
    if (errEl) errEl.hidden = true;
    try {
      return await fn();
    } catch (e) {
      if (errEl) { errEl.textContent = e.message; errEl.hidden = false; } else toast(e.message, true);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  function pager(page, total, onGo) {
    const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    const el = document.createElement("div");
    el.className = "pager";
    el.innerHTML = `<button class="btn small" data-go="-1" ${page <= 1 ? "disabled" : ""}>上一页</button>
      <span>第 ${page} / ${pages} 页 · 共 ${total} 条</span>
      <button class="btn small" data-go="1" ${page >= pages ? "disabled" : ""}>下一页</button>`;
    el.addEventListener("click", (e) => {
      const b = e.target.closest("[data-go]");
      if (b) onGo(page + Number(b.dataset.go));
    });
    return el;
  }

  function seg(options, current, onPick) {
    const el = document.createElement("div");
    el.className = "seg";
    el.innerHTML = options.map(([v, label]) => `<button type="button" data-v="${esc(v)}" class="${v === current ? "on" : ""}">${esc(label)}</button>`).join("");
    el.addEventListener("click", (e) => {
      const b = e.target.closest("button");
      if (b) onPick(b.dataset.v);
    });
    return el;
  }

  // ---------- auth & routing ----------

  function showLogin(msg) {
    $("#shell").hidden = true;
    $("#login").hidden = false;
    const err = $("#login-error");
    err.textContent = msg || "";
    err.hidden = !msg;
    $("#login-token").focus();
  }

  function logout(msg) {
    token = "";
    storage((s) => s.removeItem(TOKEN_KEY));
    showLogin(msg);
  }

  $("#login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    token = $("#login-token").value.trim();
    const btn = e.submitter;
    btn.disabled = true;
    try {
      await api("/admin/stats");
      storage((s) => s.setItem(TOKEN_KEY, token));
      $("#login-token").value = "";
      enter();
    } catch (err) {
      showLogin(err.message);
    } finally {
      btn.disabled = false;
    }
  });
  $("#logout").addEventListener("click", () => logout());

  const TABS = { overview: renderOverview, submissions: renderSubmissions, orders: renderOrders, events: renderEvents, users: renderUsers };

  function route() {
    const tab = location.hash.slice(1) in TABS ? location.hash.slice(1) : "overview";
    document.querySelectorAll("#nav a").forEach((a) => a.classList.toggle("active", a.dataset.tab === tab));
    main.innerHTML = "";
    TABS[tab]();
    refreshCounts();
  }

  async function refreshCounts() {
    try {
      const s = await api("/admin/stats");
      document.querySelectorAll("[data-count]").forEach((el) => {
        const n = s[el.dataset.count];
        el.textContent = n ? String(n) : "";
      });
      return s;
    } catch { return null; }
  }

  function enter() {
    $("#login").hidden = true;
    $("#shell").hidden = false;
    route();
  }

  window.addEventListener("hashchange", () => { if (token) route(); });

  // ---------- overview ----------

  async function renderOverview() {
    main.innerHTML = `<div class="page-head"><div><h1>概览</h1><p class="hint">“今日”按北京时间 0 点起算</p></div>
      <button class="btn small" id="reload">刷新</button></div><div class="stats" id="stats"></div>`;
    const box = $("#stats");
    const load = async () => {
      const s = await refreshCounts();
      if (!s) return;
      box.innerHTML = [
        ["pending_submissions", "待审核投稿", "submissions", s.pending_submissions > 0],
        ["pending_shipments", "待发货订单", "orders", s.pending_shipments > 0],
        ["users_today", "今日新用户", "users", false],
        ["flowers_today", "今日送出小红花", "", false],
      ].map(([k, label, tab, alert]) => `<button class="stat ${alert ? "alert" : ""}" data-tab="${tab}"><b>${s[k]}</b><span>${label}</span></button>`).join("");
    };
    box.addEventListener("click", (e) => {
      const b = e.target.closest("[data-tab]");
      if (b && b.dataset.tab) location.hash = b.dataset.tab;
    });
    $("#reload").addEventListener("click", load);
    load();
  }

  // ---------- submissions ----------

  const subState = { status: "pending", q: "", page: 1 };

  function renderSubmissions() {
    main.innerHTML = `<div class="page-head"><div><h1>投稿审核</h1>
      <p class="hint">通过前必须补视频号信息：优先填「视频 token」（小程序内直接播放），或填「视频号 ID + feed_id」（跳转视频号）。</p></div></div>
      <div class="toolbar" id="sub-bar"></div><div class="list" id="sub-list"></div><div id="sub-pager"></div>`;
    const bar = $("#sub-bar");
    bar.append(seg([["pending", "待审核"], ["approved", "已通过"], ["rejected", "已驳回"], ["all", "全部"]], subState.status, (v) => {
      subState.status = v; subState.page = 1; renderSubmissions();
    }));
    const form = document.createElement("form");
    form.className = "toolbar";
    form.style.margin = "0";
    form.innerHTML = `<input type="search" name="q" placeholder="搜索标题或作者昵称" value="${esc(subState.q)}"><button class="btn small">搜索</button>`;
    form.addEventListener("submit", (e) => { e.preventDefault(); subState.q = form.q.value.trim(); subState.page = 1; loadSubmissions(); });
    bar.append(form);
    loadSubmissions();
  }

  async function loadSubmissions() {
    const list = $("#sub-list");
    list.innerHTML = `<p class="empty">加载中…</p>`;
    const data = await busy(null, null, () => api("/admin/submissions", {
      params: { status: subState.status, q: subState.q, page: subState.page, page_size: PAGE_SIZE },
    }));
    if (!data) { list.innerHTML = `<p class="empty">加载失败</p>`; return; }
    if (!data.items.length && subState.page > 1) { subState.page -= 1; loadSubmissions(); return; }
    list.innerHTML = data.items.length ? "" : `<p class="empty">${subState.status === "pending" ? "没有待审核的投稿 🎉" : "没有记录"}</p>`;
    data.items.forEach((s) => list.append(submissionCard(s)));
    $("#sub-pager").replaceChildren(data.total > PAGE_SIZE ? pager(subState.page, data.total, (p) => { subState.page = p; loadSubmissions(); }) : "");
  }

  const STATUS_TEXT = { pending: "待审核", approved: "已通过", rejected: "已驳回" };

  function feedSummary(s) {
    const parts = [];
    if (s.feed_token) parts.push(`视频 token：<b>${esc(s.feed_token)}</b>`);
    if (s.finder_user_name || s.feed_id) parts.push(`视频号 ID：<b>${esc(s.finder_user_name || "—")}</b>　feed_id：<b>${esc(s.feed_id || "—")}</b>`);
    return parts.length ? parts.join("<br>") : "尚未填写视频号信息";
  }

  function feedFields(s) {
    const useFinder = !s.feed_token && (s.finder_user_name || s.feed_id);
    return `<label>视频 token <span class="hint">（必填，二选一）</span>
        <input name="feed_token" value="${esc(s.feed_token || "")}" placeholder="从视频号助手复制的 feed-token"></label>
      <details ${useFinder ? "open" : ""}><summary>没有 token？改填视频号 ID + feed_id</summary>
        <div class="row">
          <label>视频号 ID（finder_user_name）<input name="finder_user_name" value="${esc(s.finder_user_name || "")}" placeholder="sph..."></label>
          <label>feed_id<input name="feed_id" value="${esc(s.feed_id || "")}" placeholder="export/..."></label>
        </div></details>`;
  }

  /** Client-side mirror of the server rule, so operators get told before the round trip. */
  function readFeed(form) {
    const v = (n) => form.elements[n].value.trim();
    const body = { feed_token: v("feed_token"), finder_user_name: v("finder_user_name"), feed_id: v("feed_id") };
    const ok = body.feed_token || (body.finder_user_name && body.feed_id);
    return { body, ok };
  }

  function submissionCard(s) {
    const card = document.createElement("article");
    card.className = "card";
    const link = safeUrl(s.video_url);
    card.innerHTML = `<div class="card-head"><div>
        <h2>#${s.id} ${esc(s.title)}</h2>
        <div class="meta"><span>赛事：${esc(s.event_title)}</span><span>作者：${esc(s.author.nickname)}（ID ${s.author.id}${s.author.city ? " · " + esc(s.author.city) : ""}）</span>
          <span>投稿于 ${fmtTime(s.created_at)}</span>${s.status === "approved" ? `<span>收到 ${s.flower_count} 朵</span>` : ""}</div>
      </div><span class="badge ${s.status}">${STATUS_TEXT[s.status] || s.status}</span></div>
      ${s.description ? `<p class="desc">${esc(s.description)}</p>` : ""}
      <div class="link-row">${link ? `<a href="${esc(link)}" target="_blank" rel="noopener noreferrer">${esc(s.video_url)}</a>` : `<span>${esc(s.video_url)}</span>`}
        <button class="btn small" type="button" data-copy>复制链接</button></div>
      ${s.status === "rejected" ? `<p class="feed-info">驳回原因：<b>${esc(s.reject_reason || "")}</b></p>` : ""}
      ${s.status !== "pending" ? `<p class="feed-info">${feedSummary(s)}</p>` : ""}
      <div class="review-slot"></div>`;
    card.querySelector("[data-copy]").addEventListener("click", () => copy(s.video_url));
    const slot = card.querySelector(".review-slot");

    if (s.status === "pending") {
      slot.append(reviewForm(s));
    } else {
      const acts = document.createElement("div");
      acts.className = "actions";
      acts.style.marginTop = "10px";
      if (s.status === "approved") {
        acts.innerHTML = `<button class="btn small" data-act="edit">修改视频号信息</button><button class="btn small danger" data-act="reject">撤回为驳回</button>`;
      } else {
        acts.innerHTML = `<button class="btn small" data-act="reopen">重新审核</button>`;
      }
      acts.addEventListener("click", (e) => {
        const act = e.target.closest("[data-act]")?.dataset.act;
        if (!act) return;
        acts.remove();
        slot.append(act === "edit" ? feedEditForm(s) : reviewForm(s, act === "reject" ? "reject" : null));
      });
      slot.append(acts);
    }
    return card;
  }

  function reviewForm(s, only) {
    const form = document.createElement("form");
    form.className = "review";
    form.innerHTML = `${only === "reject" ? "" : `${feedFields(s)}
      <div class="actions"><button class="btn primary" data-do="approve">通过（作者 +50 朵）</button></div>`}
      <div class="actions"><input class="grow" name="reason" placeholder="驳回原因（必填，作者可见）" maxlength="200">
        <button class="btn danger" data-do="reject">驳回</button></div>
      <div class="chips">${REJECT_REASONS.map((r) => `<button type="button" class="chip">${esc(r)}</button>`).join("")}</div>
      <p class="error" hidden></p>`;
    const err = form.querySelector(".error");
    form.querySelector(".chips").addEventListener("click", (e) => {
      if (e.target.classList.contains("chip")) form.reason.value = e.target.textContent;
    });
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const btn = e.submitter;
      const action = btn?.dataset.do;
      if (!action) return;
      let body;
      if (action === "approve") {
        const feed = readFeed(form);
        if (!feed.ok) { err.textContent = "请填写视频 token，或视频号 ID 与 feed_id"; err.hidden = false; form.feed_token.focus(); return; }
        body = { action, ...feed.body };
      } else {
        const reason = form.reason.value.trim();
        if (!reason) { err.textContent = "请填写驳回原因"; err.hidden = false; form.reason.focus(); return; }
        if (s.status === "approved" && !confirm("撤回后作品从榜单下架，已发放的 50 朵投稿奖励不会扣回。确定驳回？")) return;
        body = { action, reason };
      }
      const res = await busy(btn, err, () => api(`/admin/submissions/${s.id}/review`, { method: "POST", body }));
      if (res) {
        toast(action === "approve" ? `#${s.id} 已通过` : `#${s.id} 已驳回`);
        loadSubmissions();
        refreshCounts();
      }
    });
    return form;
  }

  function feedEditForm(s) {
    const form = document.createElement("form");
    form.className = "review";
    form.innerHTML = `${feedFields(s)}<div class="actions"><button class="btn primary">保存</button><button class="btn ghost" type="button" data-cancel>取消</button></div><p class="error" hidden></p>`;
    const err = form.querySelector(".error");
    form.querySelector("[data-cancel]").addEventListener("click", () => loadSubmissions());
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const feed = readFeed(form);
      if (!feed.ok) { err.textContent = "请填写视频 token，或视频号 ID 与 feed_id"; err.hidden = false; return; }
      const res = await busy(e.submitter, err, () => api(`/admin/submissions/${s.id}`, { method: "PATCH", body: feed.body }));
      if (res) { toast("已保存"); loadSubmissions(); }
    });
    return form;
  }

  // ---------- orders ----------

  const orderState = { status: "pending_shipment", page: 1 };

  function renderOrders() {
    main.innerHTML = `<div class="page-head"><h1>订单发货</h1></div><div class="toolbar" id="ord-bar"></div><div class="list" id="ord-list"></div><div id="ord-pager"></div>`;
    $("#ord-bar").append(seg([["pending_shipment", "待发货"], ["shipped", "已发货"], ["completed", "已完成"], ["cancelled", "已取消"], ["all", "全部"]], orderState.status, (v) => {
      orderState.status = v; orderState.page = 1; renderOrders();
    }));
    loadOrders();
  }

  async function loadOrders() {
    const list = $("#ord-list");
    list.innerHTML = `<p class="empty">加载中…</p>`;
    const data = await busy(null, null, () => api("/admin/orders", { params: { status: orderState.status, page: orderState.page, page_size: PAGE_SIZE } }));
    if (!data) { list.innerHTML = `<p class="empty">加载失败</p>`; return; }
    if (!data.items.length && orderState.page > 1) { orderState.page -= 1; loadOrders(); return; }
    list.innerHTML = data.items.length ? "" : `<p class="empty">${orderState.status === "pending_shipment" ? "没有待发货的订单" : "没有记录"}</p>`;
    data.items.forEach((o) => list.append(orderCard(o)));
    $("#ord-pager").replaceChildren(data.total > PAGE_SIZE ? pager(orderState.page, data.total, (p) => { orderState.page = p; loadOrders(); }) : "");
  }

  function orderCard(o) {
    const card = document.createElement("article");
    card.className = "card";
    const addr = addressText(o.address);
    card.innerHTML = `<div class="card-head"><div>
        <h2>#${o.id} ${esc(o.product.name)} × ${o.quantity}</h2>
        <div class="meta"><span>${o.total_price} 朵</span><span>用户：${esc(o.user_nickname)}（ID ${o.user_id}）</span><span>下单于 ${fmtTime(o.created_at)}</span>
          ${o.tracking_no ? `<span>快递单号：${esc(o.tracking_no)}</span>` : ""}</div>
      </div><span class="badge ${o.status}">${esc(o.status_text)}</span></div>
      ${addr ? `<div class="link-row"><span style="flex:1">${esc(addr)}</span><button class="btn small" type="button" data-copy>复制地址</button></div>` : `<p class="feed-info">公益项目，无需发货</p>`}`;
    card.querySelector("[data-copy]")?.addEventListener("click", () => copy(addr));
    if (o.status === "pending_shipment") {
      const form = document.createElement("form");
      form.className = "review";
      form.innerHTML = `<div class="actions"><input class="grow" name="tracking_no" placeholder="快递单号（选填，用户可见）" maxlength="64">
        <button class="btn primary">确认发货</button></div><p class="error" hidden></p>`;
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const no = form.tracking_no.value.trim();
        const res = await busy(e.submitter, form.querySelector(".error"), () => api(`/admin/orders/${o.id}/ship`, { method: "POST", body: { tracking_no: no || null } }));
        if (res) { toast(`#${o.id} 已发货`); loadOrders(); refreshCounts(); }
      });
      card.append(form);
    }
    return card;
  }

  // ---------- events ----------

  const evState = { q: "", category: "", featured: false, page: 1 };
  let categories = null;

  async function renderEvents() {
    main.innerHTML = `<div class="page-head"><div><h1>赛事运营</h1><p class="hint">精选赛事出现在小程序首页瀑布流；封面可填完整 URL，或图片目录下的文件名。</p></div></div>
      <form class="toolbar" id="ev-bar">
        <input type="search" name="q" placeholder="搜索赛事名称" value="${esc(evState.q)}">
        <select name="category"><option value="">全部分类</option></select>
        <label class="check"><input type="checkbox" name="featured" ${evState.featured ? "checked" : ""}> 只看精选</label>
        <button class="btn small">筛选</button>
      </form>
      <div class="table-wrap"><table><thead><tr><th>ID</th><th>封面</th><th>赛事</th><th>分类</th><th class="num">热度</th><th class="num">参与</th><th class="num">小红花</th><th>精选</th><th></th></tr></thead>
      <tbody id="ev-body"></tbody></table></div><div id="ev-pager"></div>`;
    const bar = $("#ev-bar");
    bar.addEventListener("submit", (e) => {
      e.preventDefault();
      Object.assign(evState, { q: bar.q.value.trim(), category: bar.category.value, featured: bar.featured.checked, page: 1 });
      loadEvents();
    });
    bar.featured.addEventListener("change", () => bar.requestSubmit());
    bar.category.addEventListener("change", () => bar.requestSubmit());
    loadEvents();
    if (!categories) categories = await api("/categories").catch(() => []);
    bar.category.insertAdjacentHTML("beforeend", categories.map((c) => `<option ${c.name === evState.category ? "selected" : ""}>${esc(c.name)}</option>`).join(""));
  }

  async function loadEvents() {
    const body = $("#ev-body");
    const data = await busy(null, null, () => api("/admin/events", { params: { q: evState.q, category: evState.category, featured: evState.featured || "", page: evState.page, page_size: PAGE_SIZE } }));
    if (!data) return;
    body.innerHTML = data.items.length ? "" : `<tr><td colspan="9" class="empty">没有匹配的赛事</td></tr>`;
    data.items.forEach((ev) => {
      const tr = document.createElement("tr");
      const cover = safeUrl(ev.cover_url);
      tr.innerHTML = `<td>${ev.id}</td><td>${cover ? `<img class="thumb" src="${esc(cover)}" alt="" loading="lazy">` : `<span class="thumb"></span>`}</td>
        <td><b>${esc(ev.emoji)} ${esc(ev.title)}</b><div class="meta">${esc(ev.geo)} · ${esc(ev.status_text)}</div></td>
        <td>${esc(ev.category)}</td><td class="num">${ev.heat}</td><td class="num">${ev.participant_count}</td><td class="num">${ev.flower_count}</td>
        <td><label class="check"><input type="checkbox" data-featured ${ev.featured ? "checked" : ""}></label></td>
        <td><button class="btn small" data-edit>编辑</button></td>`;
      tr.querySelector("[data-featured]").addEventListener("change", async (e) => {
        const box = e.target;
        box.disabled = true;
        try {
          await api(`/admin/events/${ev.id}`, { method: "PATCH", body: { featured: box.checked } });
          ev.featured = box.checked;
          toast(box.checked ? "已设为精选" : "已取消精选");
        } catch (err) {
          box.checked = ev.featured;
          toast(err.message, true);
        } finally { box.disabled = false; }
      });
      tr.querySelector("[data-edit]").addEventListener("click", () => editEvent(ev));
      body.append(tr);
    });
    $("#ev-pager").replaceChildren(data.total > PAGE_SIZE ? pager(evState.page, data.total, (p) => { evState.page = p; loadEvents(); }) : "");
  }

  const EVENT_FIELDS = [
    ["heat", "热度", "number"], ["participant_count", "参与人数", "number"], ["flower_count", "小红花数", "number"],
    ["reward_text", "奖励说明", "text", 100], ["track", "赛道", "text", 100], ["video_status", "视频状态文案", "text", 40],
    ["ai_label", "AI 标签", "text", 40], ["cover_url", "封面", "text", 500],
  ];

  function editEvent(ev) {
    const dlg = $("#dialog");
    dlg.innerHTML = `<form method="dialog">
      <h2>编辑赛事 · ${esc(ev.title)}</h2>
      <div class="grid2">${EVENT_FIELDS.map(([k, label, type, max]) => `<label ${["reward_text", "track", "cover_url"].includes(k) ? 'style="grid-column:1/-1"' : ""}>${label}
        <input name="${k}" type="${type}" ${type === "number" ? 'min="0" step="1" required' : `maxlength="${max}"`} value="${esc(ev[k])}"></label>`).join("")}</div>
      <div class="actions"><label class="check"><input type="checkbox" name="ai_allowed" ${ev.ai_allowed ? "checked" : ""}> 允许 AI 辅助</label>
        <label class="check"><input type="checkbox" name="featured" ${ev.featured ? "checked" : ""}> 首页精选</label></div>
      <p class="error" hidden></p>
      <div class="foot"><button class="btn ghost" value="cancel" formnovalidate>取消</button><button class="btn primary" value="save">保存</button></div>
    </form>`;
    const form = dlg.querySelector("form");
    form.addEventListener("submit", async (e) => {
      if (e.submitter?.value !== "save") return;
      e.preventDefault();
      const changes = {};
      EVENT_FIELDS.forEach(([k, , type]) => {
        const raw = form.elements[k].value.trim();
        const val = type === "number" ? Number(raw) : raw;
        if (String(val) !== String(ev[k] ?? "")) changes[k] = val;
      });
      ["ai_allowed", "featured"].forEach((k) => { if (form.elements[k].checked !== ev[k]) changes[k] = form.elements[k].checked; });
      if (!Object.keys(changes).length) { dlg.close(); return; }
      const res = await busy(e.submitter, form.querySelector(".error"), () => api(`/admin/events/${ev.id}`, { method: "PATCH", body: changes }));
      if (res) { dlg.close(); toast("已保存"); loadEvents(); }
    });
    dlg.showModal();
  }

  // ---------- users ----------

  const userState = { q: "", page: 1, selected: null, ledgerPage: 1 };

  function renderUsers() {
    main.innerHTML = `<div class="page-head"><div><h1>用户与小红花</h1><p class="hint">点一行查看账本、调整小红花。调整会记入用户账本（“运营调整”），备注用户可见。</p></div></div>
      <form class="toolbar" id="u-bar"><input type="search" name="q" placeholder="昵称或用户 ID" value="${esc(userState.q)}"><button class="btn small">搜索</button></form>
      <div class="split"><div><div class="table-wrap"><table><thead><tr><th>ID</th><th>用户</th><th>城市</th><th class="num">余额</th><th class="num">成长值</th><th class="num">报名/投稿</th><th>注册</th></tr></thead>
        <tbody id="u-body"></tbody></table></div><div id="u-pager"></div></div>
        <div id="u-panel" class="panel"></div></div>`;
    const bar = $("#u-bar");
    bar.addEventListener("submit", (e) => { e.preventDefault(); userState.q = bar.q.value.trim(); userState.page = 1; loadUsers(); });
    loadUsers();
    if (userState.selected) loadUserPanel(userState.selected);
  }

  async function loadUsers() {
    const body = $("#u-body");
    const data = await busy(null, null, () => api("/admin/users", { params: { q: userState.q, page: userState.page, page_size: PAGE_SIZE } }));
    if (!data) return;
    body.innerHTML = data.items.length ? "" : `<tr><td colspan="7" class="empty">没有匹配的用户</td></tr>`;
    data.items.forEach((u) => {
      const tr = document.createElement("tr");
      tr.className = "clickable" + (u.id === userState.selected ? " selected" : "");
      const avatar = safeUrl(u.avatar_url);
      tr.innerHTML = `<td>${u.id}</td><td>${avatar ? `<img class="avatar" src="${esc(avatar)}" alt=""> ` : ""}${esc(u.nickname)}</td>
        <td>${esc([u.city, u.district].filter(Boolean).join(" ") || "—")}</td><td class="num">${u.flower_balance}</td><td class="num">${u.growth_value}</td>
        <td class="num">${u.enrolled_count} / ${u.submission_count}</td><td>${fmtTime(u.created_at).split(" ")[0]}</td>`;
      tr.addEventListener("click", () => {
        userState.selected = u.id;
        userState.ledgerPage = 1;
        body.querySelectorAll("tr").forEach((r) => r.classList.toggle("selected", r === tr));
        loadUserPanel(u.id, u, true);
      });
      body.append(tr);
    });
    $("#u-pager").replaceChildren(data.total > PAGE_SIZE ? pager(userState.page, data.total, (p) => { userState.page = p; loadUsers(); }) : "");
  }

  async function loadUserPanel(uid, user, reveal = false) {
    const panel = $("#u-panel");
    if (!panel) return;
    if (!user) {
      const found = await api("/admin/users", { params: { q: String(uid), page_size: 100 } }).catch(() => null);
      user = found && found.items.find((u) => u.id === uid);
      if (!user) { panel.innerHTML = ""; return; }
    }
    const ledger = await busy(null, null, () => api(`/admin/users/${uid}/ledger`, { params: { page: userState.ledgerPage, page_size: PAGE_SIZE } }));
    if (!ledger) return;
    panel.innerHTML = `<article class="card">
      <h2>${esc(user.nickname)} <span class="hint">ID ${user.id}</span></h2>
      <div class="meta"><span>openid：${esc(user.openid)}</span><span>${esc(user.level_name)}</span><span>${esc([user.city, user.district, user.community].filter(Boolean).join(" "))}</span></div>
      <p style="margin:12px 0 0">当前余额 <b style="font-size:22px;color:var(--olive-dark)">${ledger.balance}</b> 朵</p>
      <form class="adjust" id="adjust">
        <label>增减数量<input name="delta" type="number" step="1" required placeholder="如 50 或 -20"></label>
        <label>备注（必填，用户可见）<input name="note" maxlength="200" required placeholder="如：线下活动补发"></label>
        <button class="btn primary">确认</button>
      </form><p class="error" id="adjust-err" hidden></p>
      <h2 style="margin-top:16px">小红花账本</h2>
      <div id="ledger">${ledger.items.map((l) => `<div class="ledger-row"><div>${esc(l.reason_text)}${l.note ? `<div class="hint" style="margin:0">${esc(l.note)}</div>` : ""}
        <div class="hint" style="margin:0">${fmtTime(l.created_at)}</div></div>
        <div style="text-align:right"><span class="${l.delta > 0 ? "plus" : "minus"}">${l.delta > 0 ? "+" : ""}${l.delta}</span><div class="hint" style="margin:0">余 ${l.balance_after}</div></div></div>`).join("") || `<p class="empty">暂无记录</p>`}</div>
      <div id="ledger-pager"></div></article>`;
    if (ledger.total > PAGE_SIZE) {
      $("#ledger-pager").append(pager(userState.ledgerPage, ledger.total, (p) => { userState.ledgerPage = p; loadUserPanel(uid, user); }));
    }
    // single-column layout: the panel sits below the table, bring it into view
    if (reveal && window.matchMedia("(max-width: 1100px)").matches) panel.scrollIntoView({ behavior: "smooth", block: "start" });
    const form = $("#adjust");
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const delta = Number(form.delta.value);
      const note = form.note.value.trim();
      const err = $("#adjust-err");
      if (!Number.isInteger(delta) || delta === 0) { err.textContent = "请输入非 0 的整数"; err.hidden = false; return; }
      if (!note) { err.textContent = "请填写备注"; err.hidden = false; return; }
      if (!confirm(`确定给「${user.nickname}」${delta > 0 ? "增加" : "扣除"} ${Math.abs(delta)} 朵小红花？`)) return;
      const res = await busy(e.submitter, err, () => api(`/admin/users/${uid}/flowers`, { method: "POST", body: { delta, note } }));
      if (res) {
        toast(`已调整，当前余额 ${res.flower_balance} 朵`);
        userState.ledgerPage = 1;
        loadUserPanel(uid, res);
        loadUsers();
      }
    });
  }

  // ---------- boot ----------

  if (token) {
    api("/admin/stats").then(enter).catch((e) => showLogin(e instanceof ApiError ? e.message : "无法连接后端"));
  } else {
    showLogin();
  }
})();
