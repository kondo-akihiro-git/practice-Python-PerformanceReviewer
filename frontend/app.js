const STATUS_LABELS = {
  draft: "自己評価 入力中",
  submitted: "面談担当者 取りまとめ待ち",
  summarized: "マネージャー 評価待ち",
  manager_evaluated: "社長 評価待ち",
  evaluated: "面談担当者 確認・公開待ち",
  published: "公開済み",
};
const ROLE_LABELS = { member: "メンバー", interviewer: "面談担当者", manager: "マネージャー", president: "社長" };
const EVALUATORS = ["manager", "president"];

// 評価の全体フロー。status ごとに「誰の番か」を示す
const STEPS = [
  ["draft", "自己評価", "member"],
  ["submitted", "取りまとめ", "interviewer"],
  ["summarized", "評価", "manager"],
  ["manager_evaluated", "評価", "president"],
  ["evaluated", "確認・公開", "interviewer"],
  ["published", "結果の閲覧", "member"],
];
const TURN = Object.fromEntries(STEPS.slice(0, 5).map(([status, , role]) => [status, role]));
const TODO_TEXT = {
  draft: "全8項目に 1〜5 の評価点とコメントを入力し、「提出する」を押してください。「下書き保存」で途中保存もできます。",
  submitted: "メンバーの自己評価を確認し、項目ごとの所見と総括を記入して「取りまとめを確定する」を押してください。",
  summarized: "自己評価と面談担当者の取りまとめを確認し、項目ごとに評価点とコメントを入力して「評価を確定する」を押してください。",
  manager_evaluated: "自己評価・取りまとめ・マネージャーの評価を確認し、項目ごとに評価点とコメントを入力して「評価を確定する」を押してください。",
  evaluated: "マネージャーと社長の評価を確認し、問題なければ「本人に公開する」を押してください。公開後にメンバーが結果を閲覧できます。",
};
const TODO_SHORT = {
  draft: "自己評価を入力して提出", submitted: "取りまとめを記入", summarized: "評価を記入",
  manager_evaluated: "評価を記入", evaluated: "確認して本人に公開",
};
const WAIT_ACTION = { draft: "自己評価の入力", submitted: "取りまとめ", summarized: "評価", manager_evaluated: "評価", evaluated: "確認・公開" };

// ログイン中のユーザーが今この評価で操作する番か
const isMyTurn = (roles, status) => status in TURN && roles.includes(TURN[status]);

function stepper(status, roles = []) {
  const idx = STEPS.findIndex(([s]) => s === status);
  const mine = isMyTurn(roles, status);
  return `<ol class="stepper">${STEPS.map(([, label, role], i) => {
    const state = status === "published" || i < idx ? "done" : i === idx ? (mine ? "current mine" : "current") : "";
    const mark = i + 1;
    return `<li class="step ${state}"><span class="num">${mark}</span><b>${label}</b>${ROLE_LABELS[role]}${state.includes("mine") ? `<span class="tag">あなたの番</span>` : ""}</li>`;
  }).join("")}</ol>`;
}

function guideCard(status, roles) {
  if (isMyTurn(roles, status)) {
    return `<div class="card guide todo"><div><h2>あなたの番です</h2><p>${TODO_TEXT[status]}</p></div></div>`;
  }
  let title, text;
  if (status === "published") {
    const isMember = roles.includes("member");
    title = isMember ? "評価結果が公開されました" : "本人への公開が完了しています";
    text = isMember ? "各項目の評価点とコメントをご確認ください。いつでもこの画面で見返せます。" : "メンバーが結果を閲覧できます。必要に応じて面談で結果を伝えてください。";
  } else {
    const submitted = roles.includes("member") && status !== "draft" ? "自己評価は提出済みです。" : "";
    title = "現在、あなたの操作は不要です";
    text = `${submitted}現在は「${ROLE_LABELS[TURN[status]]}」の${WAIT_ACTION[status]}の段階です。完了すると次の担当者に進みます。`;
  }
  return `<div class="card guide done"><div><h2>${title}</h2><p>${text}</p></div></div>`;
}

const app = document.getElementById("app");
const header = document.getElementById("header");
let token = sessionStorage.getItem("token");
let me = null;

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

async function api(path, options = {}) {
  const res = await fetch(`/api${path}`, {
    method: options.method || "GET",
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  if (res.status === 401 && path !== "/login") {
    logout();
    throw new Error("ログインが必要です");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = Array.isArray(data.detail) ? "入力内容を確認してください" : data.detail;
    throw new Error(detail || "エラーが発生しました");
  }
  return data;
}

function logout() {
  token = null;
  me = null;
  sessionStorage.removeItem("token");
  location.hash = "";
  render();
}

function renderHeader() {
  header.innerHTML = `<a class="title" href="#/">人事評価システム</a>` +
    (me ? `<span class="user"><span class="avatar">${esc(me.name.slice(0, 1))}</span>${esc(me.name)}<button id="logout">ログアウト</button></span>` : "");
  document.getElementById("logout")?.addEventListener("click", logout);
}

function showMessage(el, text, ok = false) {
  el.className = ok ? "ok" : "error";
  el.textContent = text;
}

function renderLogin() {
  app.innerHTML = `<div class="card"><h1>ログイン</h1><p class="subtle">自己評価の入力や、評価結果の確認を行います。</p>
    <label>メールアドレス<input id="email" type="email" autocomplete="username"></label>
    <label>パスワード<input id="password" type="password" autocomplete="current-password"></label>
    <div id="msg"></div><div class="actions"><button id="login">ログイン</button></div></div>
    <div class="card"><h2>評価のながれ</h2>${stepper("")}
    <p class="subtle">メンバーが自己評価を提出すると、順番に各担当者へ進み、最後に結果が本人へ公開されます。</p></div>`;
  const submit = async () => {
    try {
      const data = await api("/login", { method: "POST", body: { email: app.querySelector("#email").value, password: app.querySelector("#password").value } });
      token = data.token;
      me = data.user;
      sessionStorage.setItem("token", token);
      render();
    } catch (e) {
      showMessage(app.querySelector("#msg"), e.message);
    }
  };
  app.querySelector("#login").addEventListener("click", submit);
  app.querySelector("#password").addEventListener("keydown", (e) => e.key === "Enter" && submit());
}

async function renderList() {
  const reviews = await api("/reviews");
  const pending = reviews.filter((r) => isMyTurn(r.roles, r.status)).length;
  const rows = reviews.map((r) => {
    const turn = isMyTurn(r.roles, r.status);
    return `<tr>
      <td><b>${esc(r.period)}</b></td><td>${esc(r.member.name)}さん</td>
      <td>${r.roles.map((x) => ROLE_LABELS[x]).join("・") || "-"}</td>
      <td><span class="badge ${r.status}">${STATUS_LABELS[r.status]}</span></td>
      <td>${turn ? `<span class="badge todo">あなたの番</span><div class="todo-text">${TODO_SHORT[r.status]}</div>` : `<span class="badge none">対応なし</span>`}</td>
      <td>${r.roles.length ? `<a href="#/reviews/${r.id}">開く</a>` : ""}</td></tr>`;
  }).join("");
  const summary = pending
    ? `あなたの対応待ちが <b>${pending}件</b> あります。「あなたの番」の評価を開いて操作してください。`
    : "現在、あなたが対応する必要のある評価はありません。";
  app.innerHTML = `<div class="card"><h1>評価一覧</h1><p class="subtle">${summary}</p>
    ${reviews.length ? `<div class="table-wrap"><table><thead><tr><th>期間</th><th>被評価者</th><th>あなたの役割</th><th>状態</th><th>次にやること</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>` : `<p class="empty">対象の評価はありません</p>`}</div>
    <div class="card"><h2>評価のながれ</h2>${stepper("")}
      <p class="subtle">各評価の画面では、現在の段階とあなたの操作が表示されます。</p></div>
    <div id="admin"></div>`;
  if (me.is_admin) await renderAdmin();
}

async function renderAdmin() {
  const users = await api("/users");
  const options = (list) => list.map((u) => `<option value="${u.id}">${esc(u.name)}（${esc(u.email)}）</option>`).join("");
  const evaluators = users.filter((u) => u.can_decide);
  app.querySelector("#admin").innerHTML = `
    <div class="card"><h2>評価の作成（管理者）</h2>
      <label>期間<input id="period" placeholder="例：2027年 上期"></label>
      <label>被評価者<select id="member">${options(users)}</select></label>
      <label>面談担当者<select id="interviewer">${options(users)}</select></label>
      <label>マネージャー<select id="manager">${options(evaluators)}</select></label>
      <label>社長<select id="president">${options(evaluators)}</select></label>
      <div id="review-msg"></div><div class="actions"><button id="create-review">評価を作成</button></div></div>
    <div class="card"><h2>ユーザーの追加（管理者）</h2>
      <label>氏名<input id="u-name"></label><label>メールアドレス<input id="u-email" type="email"></label>
      <label>初期パスワード（8文字以上）<input id="u-password" type="password" autocomplete="new-password"></label>
      <label>所属<input id="u-aff"></label>
      <label><input id="u-decide" type="checkbox" style="width:auto"> マネージャー・社長として評価できる</label>
      <div id="user-msg"></div><div class="actions"><button id="create-user">ユーザーを追加</button></div></div>`;
  const val = (id) => app.querySelector(id).value;
  app.querySelector("#create-review").addEventListener("click", async () => {
    try {
      await api("/reviews", { method: "POST", body: { period: val("#period"), member_id: +val("#member"), interviewer_id: +val("#interviewer"), manager_id: +val("#manager"), president_id: +val("#president") } });
      render();
    } catch (e) { showMessage(app.querySelector("#review-msg"), e.message); }
  });
  app.querySelector("#create-user").addEventListener("click", async () => {
    try {
      await api("/users", { method: "POST", body: { name: val("#u-name"), email: val("#u-email"), password: val("#u-password"), affiliation: val("#u-aff"), can_decide: app.querySelector("#u-decide").checked } });
      render();
    } catch (e) { showMessage(app.querySelector("#user-msg"), e.message); }
  });
}

const field = (label, text) =>
  `<div class="field"><div class="field-label">${label}</div><div class="field-body">${text ? esc(text) : `<span class="empty">記入なし</span>`}</div></div>`;

// 評価基準（1〜5）をすべて表示し、選ばれたものを明示する
const block = (cls, title, body) => body == null ? "" :
  `<div class="block ${cls}"><h3>${title}</h3>${field("内容", body)}</div>`;

function scoredBlock(cls, title, item, score, comment, commentLabel) {
  if (score == null) return "";
  const options = item.anchors.map((text, i) => {
    const on = score === i + 1;
    return `<li class="opt ${on ? "on" : ""}"><span class="opt-no">${i + 1}</span><span class="opt-text">${esc(text)}</span>${on ? `<span class="opt-tag">選択</span>` : ""}</li>`;
  }).join("");
  return `<div class="block ${cls}"><h3>${title}：<b>${score}</b> を選択</h3><ul class="opts">${options}</ul>${field(commentLabel, comment)}</div>`;
}

function scoreInputs(item, name, current) {
  return `<div class="score">${item.anchors.map((text, i) =>
    `<label><input type="radio" name="${name}-${item.item_id}" value="${i + 1}" ${current === i + 1 ? "checked" : ""}>${i + 1}：${esc(text)}</label>`).join("")}</div>`;
}

async function renderReview(id) {
  const r = await api(`/reviews/${id}`);
  const has = (role) => r.roles.includes(role);
  const mode = has("member") && r.status === "draft" ? "self"
    : has("interviewer") && r.status === "submitted" ? "interviewer"
    : has("manager") && r.status === "summarized" ? "manager"
    : has("president") && r.status === "manager_evaluated" ? "president"
    : has("interviewer") && r.status === "evaluated" ? "publish" : "view";

  const evalBlock = (it, role) => {
    const label = ROLE_LABELS[role];
    if (mode === role) {
      return `<div class="block ${role}"><h3>${label}の評価（1〜5）</h3>${scoreInputs(it, role, it[`${role}_score`])}
        <label>コメント<textarea data-${role}-comment="${it.item_id}">${esc(it[`${role}_comment`])}</textarea></label></div>`;
    }
    return scoredBlock(role, `${label}の評価`, it, it[`${role}_score`], it[`${role}_comment`], "評価コメント");
  };

  const itemsHtml = r.items.map((it, n) => {
    const self = mode === "self"
      ? `<div class="block self"><h3>自己評価（1〜5）</h3>${scoreInputs(it, "self", it.self_score)}
         <label>補足コメント<textarea data-self-comment="${it.item_id}">${esc(it.self_comment)}</textarea></label></div>`
      : scoredBlock("self", "自己評価", it, it.self_score, it.self_comment, "補足コメント");
    const interviewer = mode === "interviewer"
      ? `<div class="block interviewer"><h3>面談担当者の取りまとめ</h3><textarea data-note="${it.item_id}">${esc(it.interviewer_note)}</textarea></div>`
      : block("interviewer", "面談担当者の取りまとめ", it.interviewer_note);
    return `<div class="card"><div class="item-head"><span class="no">${n + 1}</span><h2>${esc(it.title)}</h2></div>${self}${interviewer}${EVALUATORS.map((role) => evalBlock(it, role)).join("")}</div>`;
  }).join("");

  const overallCard = (role, label, value) => mode === role
    ? `<div class="card"><h2>${label}の総括</h2><textarea id="${role}-overall">${esc(value)}</textarea></div>`
    : value == null ? "" : `<div class="card"><h2>${label}の総括</h2>${field("総括", value)}</div>`;
  const overall = overallCard("interviewer", "面談担当者", r.interviewer_overall) +
    EVALUATORS.map((role) => overallCard(role, ROLE_LABELS[role], r[`${role}_overall`])).join("");

  const submitLabel = { self: "提出する", interviewer: "取りまとめを確定する", manager: "評価を確定する", president: "評価を確定する" };
  const actions = mode === "publish" ? `<button id="publish">本人に公開する</button>`
    : mode === "view" ? ""
    : `<button id="save" class="secondary">下書き保存</button><button id="submit">${submitLabel[mode]}</button>`;
  const hints = {
    self: "確定すると編集できません", interviewer: "確定するとマネージャーの評価に進みます",
    manager: "確定すると社長の評価に進みます", president: "確定すると面談担当者の確認に進みます",
    publish: "公開するとメンバーが結果を閲覧できます", view: "",
  };

  app.innerHTML = `<p><a href="#/">評価一覧に戻る</a></p>
    <div class="card"><h1>${esc(r.period)}　${esc(r.member.name)}さんの評価</h1>
      <span class="badge ${r.status}">${STATUS_LABELS[r.status]}</span>
      <p class="subtle" style="margin-top:8px">面談担当者：${esc(r.interviewer.name)}　マネージャー：${esc(r.manager.name)}　社長：${esc(r.president.name)}　／　あなたの役割：<b>${r.roles.map((x) => ROLE_LABELS[x]).join("・")}</b></p>
      ${stepper(r.status, r.roles)}</div>
    ${guideCard(r.status, r.roles)}
    ${itemsHtml}${overall}
    ${actions ? `<div class="action-bar"><div class="inner"><span class="hint">${hints[mode]}</span><span id="msg"></span>${actions}</div></div>` : `<div id="msg"></div>`}`;

  const msg = app.querySelector("#msg");
  const checked = (prefix, itemId) => {
    const el = app.querySelector(`input[name="${prefix}-${itemId}"]:checked`);
    return el ? +el.value : null;
  };
  const scoredItems = (role) => r.items.map((it) => ({
    item_id: it.item_id,
    score: checked(role, it.item_id),
    comment: app.querySelector(`[data-${role}-comment="${it.item_id}"]`).value,
  }));
  const payload = {
    self: () => ({ items: scoredItems("self") }),
    interviewer: () => ({ items: r.items.map((it) => ({ item_id: it.item_id, note: app.querySelector(`[data-note="${it.item_id}"]`).value })), overall: app.querySelector("#interviewer-overall").value }),
    manager: () => ({ items: scoredItems("manager"), overall: app.querySelector("#manager-overall").value }),
    president: () => ({ items: scoredItems("president"), overall: app.querySelector("#president-overall").value }),
  };

  const run = async (fn, done) => {
    try { await fn(); done(); } catch (e) { showMessage(msg, e.message); }
  };
  app.querySelector("#save")?.addEventListener("click", () =>
    run(() => api(`/reviews/${id}/${mode}`, { method: "PUT", body: payload[mode]() }), () => showMessage(msg, "保存しました", true)));
  app.querySelector("#submit")?.addEventListener("click", () => {
    if (!confirm("確定すると編集できなくなります。よろしいですか？")) return;
    run(async () => {
      await api(`/reviews/${id}/${mode}`, { method: "PUT", body: payload[mode]() });
      await api(`/reviews/${id}/${mode}/submit`, { method: "POST" });
    }, () => renderReview(id));
  });
  app.querySelector("#publish")?.addEventListener("click", () => {
    if (!confirm("公開すると本人が評価結果を閲覧できるようになります。よろしいですか？")) return;
    run(() => api(`/reviews/${id}/publish`, { method: "POST" }), () => renderReview(id));
  });
}

async function render() {
  if (!token) { renderHeader(); return renderLogin(); }
  try {
    me = me || await api("/me");
    renderHeader();
    const match = location.hash.match(/^#\/reviews\/(\d+)$/);
    await (match ? renderReview(+match[1]) : renderList());
  } catch (e) {
    if (token) app.innerHTML = `<div class="card error">${esc(e.message)}</div><p><a href="#/">評価一覧に戻る</a></p>`;
  }
}

window.addEventListener("hashchange", render);
render();
