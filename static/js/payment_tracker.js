import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.5/firebase-app.js";
import {
  getDatabase,
  ref,
  get,
  set,
  push,
  update,
  remove,
  onValue,
  off
} from "https://www.gstatic.com/firebasejs/10.12.5/firebase-database.js";

const firebaseConfig = {
  apiKey: "AIzaSyAhuKxwKANcVDvHvDD85gpO1JzZRELuFGM",
  authDomain: "odemetakip-b5822.firebaseapp.com",
  databaseURL: "https://odemetakip-b5822-default-rtdb.firebaseio.com",
  projectId: "odemetakip-b5822",
  storageBucket: "odemetakip-b5822.firebasestorage.app",
  messagingSenderId: "479091174180",
  appId: "1:479091174180:web:a3f89ad2de502ebd5161b1",
  measurementId: "G-0BLDNCHGMV"
};

const app = initializeApp(firebaseConfig);
const db = getDatabase(app);

const DEFAULT_USER_ID = "mahmut";
const DEFAULT_USER_NAME = "Mahmut";
const DEFAULT_PASSWORD = "1234";

const state = {
  users: {},
  currentUserId: "",
  purchases: {},
  allPurchases: {},
  unsubscribePurchases: null,
  unsubscribeAllPurchases: null
};

const els = {
  loginView: document.querySelector("#loginView"),
  appView: document.querySelector("#appView"),
  loginForm: document.querySelector("#loginForm"),
  userSelect: document.querySelector("#userSelect"),
  passwordInput: document.querySelector("#passwordInput"),
  loginError: document.querySelector("#loginError"),
  loginHint: document.querySelector("#loginHint"),
  welcomeTitle: document.querySelector("#welcomeTitle"),
  refreshButton: document.querySelector("#refreshButton"),
  logoutButton: document.querySelector("#logoutButton"),
  tabs: document.querySelectorAll(".tab-button"),
  panels: {
    dashboard: document.querySelector("#dashboardTab"),
    overview: document.querySelector("#overviewTab"),
    history: document.querySelector("#historyTab"),
    users: document.querySelector("#usersTab")
  },
  totalDebt: document.querySelector("#totalDebt"),
  paidAmount: document.querySelector("#paidAmount"),
  remainingAmount: document.querySelector("#remainingAmount"),
  upcomingAmount: document.querySelector("#upcomingAmount"),
  groupTotalDebt: document.querySelector("#groupTotalDebt"),
  groupPaidAmount: document.querySelector("#groupPaidAmount"),
  groupRemainingAmount: document.querySelector("#groupRemainingAmount"),
  groupUserCount: document.querySelector("#groupUserCount"),
  groupSummary: document.querySelector("#groupSummary"),
  userOverviewList: document.querySelector("#userOverviewList"),
  emptyOverview: document.querySelector("#emptyOverview"),
  purchaseCount: document.querySelector("#purchaseCount"),
  purchaseList: document.querySelector("#purchaseList"),
  emptyPurchases: document.querySelector("#emptyPurchases"),
  historyList: document.querySelector("#historyList"),
  emptyHistory: document.querySelector("#emptyHistory"),
  addUserForm: document.querySelector("#addUserForm"),
  newUserName: document.querySelector("#newUserName"),
  newUserPassword: document.querySelector("#newUserPassword"),
  userFormError: document.querySelector("#userFormError"),
  userList: document.querySelector("#userList"),
  purchaseDialog: document.querySelector("#purchaseDialog"),
  detailDialog: document.querySelector("#detailDialog"),
  openPurchaseDialog: document.querySelector("#openPurchaseDialog"),
  purchaseForm: document.querySelector("#purchaseForm"),
  purchaseTitle: document.querySelector("#purchaseTitle"),
  purchaseMerchant: document.querySelector("#purchaseMerchant"),
  purchaseAmount: document.querySelector("#purchaseAmount"),
  installmentCount: document.querySelector("#installmentCount"),
  firstDueDate: document.querySelector("#firstDueDate"),
  purchaseNote: document.querySelector("#purchaseNote"),
  purchaseFormError: document.querySelector("#purchaseFormError"),
  detailTitle: document.querySelector("#detailTitle"),
  detailMeta: document.querySelector("#detailMeta"),
  installmentList: document.querySelector("#installmentList"),
  toast: document.querySelector("#toast")
};

const currency = new Intl.NumberFormat("tr-TR", {
  style: "currency",
  currency: "TRY"
});

const dateFormatter = new Intl.DateTimeFormat("tr-TR", {
  day: "2-digit",
  month: "short",
  year: "numeric"
});

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function hashPassword(password) {
  const bytes = new TextEncoder().encode(password);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

function parseDate(value) {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function toDateInputValue(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function addMonths(date, months) {
  const next = new Date(date.getFullYear(), date.getMonth() + months, 1);
  const lastDay = new Date(next.getFullYear(), next.getMonth() + 1, 0).getDate();
  next.setDate(Math.min(date.getDate(), lastDay));
  return next;
}

function formatDate(value) {
  if (!value) return "-";
  return dateFormatter.format(parseDate(value));
}

function formatMoney(value) {
  return currency.format(Number(value || 0));
}

function getToday() {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate());
}

function getDaysUntil(value) {
  const dueDate = parseDate(value);
  return Math.round((dueDate - getToday()) / 86400000);
}

function makeInstallments(amount, count, firstDate) {
  const totalCents = Math.round(Number(amount) * 100);
  const baseCents = Math.floor(totalCents / count);
  let remainder = totalCents - baseCents * count;
  const installments = {};
  const start = parseDate(firstDate);

  for (let index = 1; index <= count; index += 1) {
    const cents = baseCents + (remainder > 0 ? 1 : 0);
    remainder -= remainder > 0 ? 1 : 0;
    installments[index] = {
      no: index,
      amount: cents / 100,
      dueDate: toDateInputValue(addMonths(start, index - 1)),
      paid: false,
      paidAt: ""
    };
  }

  return installments;
}

function getPurchaseEntries(purchases = state.purchases) {
  return Object.entries(purchases || {})
    .map(([id, purchase]) => ({ id, ...purchase }))
    .sort((a, b) => String(b.createdAt || "").localeCompare(String(a.createdAt || "")));
}

function getInstallmentEntries(purchase) {
  return Object.values(purchase.installments || {})
    .sort((a, b) => Number(a.no) - Number(b.no));
}

function calculateStats(purchases = getPurchaseEntries()) {
  const stats = {
    total: 0,
    paid: 0,
    remaining: 0,
    upcoming: 0
  };
  const today = getToday();
  const upcomingLimit = new Date(today);
  upcomingLimit.setDate(upcomingLimit.getDate() + 30);

  purchases.forEach((purchase) => {
    getInstallmentEntries(purchase).forEach((installment) => {
      const amount = Number(installment.amount || 0);
      const dueDate = parseDate(installment.dueDate);
      stats.total += amount;

      if (installment.paid) {
        stats.paid += amount;
      } else {
        stats.remaining += amount;
        if (dueDate >= today && dueDate <= upcomingLimit) {
          stats.upcoming += amount;
        }
      }
    });
  });

  return stats;
}

function showToast(message) {
  els.toast.textContent = message;
  els.toast.classList.remove("is-hidden");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    els.toast.classList.add("is-hidden");
  }, 2600);
}

function setError(element, message = "") {
  element.textContent = message;
}

async function ensureDefaultUser() {
  const snapshot = await get(ref(db, `users/${DEFAULT_USER_ID}`));
  if (snapshot.exists()) return;

  await set(ref(db, `users/${DEFAULT_USER_ID}`), {
    name: DEFAULT_USER_NAME,
    passwordHash: await hashPassword(DEFAULT_PASSWORD),
    createdAt: new Date().toISOString(),
    default: true
  });
}

function listenUsers() {
  onValue(ref(db, "users"), (snapshot) => {
    state.users = snapshot.val() || {};
    renderUserSelect();
    renderUsers();
    renderOverview();
  }, (error) => {
    setError(els.loginError, `Firebase bağlantısı kurulamadı: ${error.message}`);
  });
}

function renderUserSelect() {
  const entries = Object.entries(state.users)
    .sort(([, a], [, b]) => String(a.name || "").localeCompare(String(b.name || ""), "tr"));

  els.userSelect.innerHTML = entries.map(([id, user]) => (
    `<option value="${escapeHtml(id)}">${escapeHtml(user.name)}</option>`
  )).join("");

  if (state.users[DEFAULT_USER_ID]) {
    els.userSelect.value = DEFAULT_USER_ID;
  }
}

function renderUsers() {
  const entries = Object.entries(state.users)
    .sort(([, a], [, b]) => String(a.name || "").localeCompare(String(b.name || ""), "tr"));

  if (!entries.length) {
    els.userList.innerHTML = "";
    return;
  }

  els.userList.innerHTML = entries.map(([id, user]) => `
    <article class="user-row">
      <div class="user-main">
        <strong>${escapeHtml(user.name)}</strong>
        <span>${id === DEFAULT_USER_ID ? "Varsayılan kullanıcı" : "Ek kullanıcı"}</span>
      </div>
      <span class="status-pill ${id === state.currentUserId ? "paid" : "waiting"}">
        <i class="bi ${id === state.currentUserId ? "bi-check2" : "bi-person"}"></i>
        ${id === state.currentUserId ? "Aktif" : "Kayıtlı"}
      </span>
    </article>
  `).join("");
}

function getUserSummaries() {
  return Object.entries(state.users)
    .sort(([, a], [, b]) => String(a.name || "").localeCompare(String(b.name || ""), "tr"))
    .map(([userId, user]) => {
      const purchases = getPurchaseEntries(state.allPurchases[userId] || {});
      const stats = calculateStats(purchases);
      const installmentTotals = purchases.reduce((totals, purchase) => {
        getInstallmentEntries(purchase).forEach((installment) => {
          totals.total += 1;
          if (installment.paid) totals.paid += 1;
        });
        return totals;
      }, { total: 0, paid: 0 });

      return {
        userId,
        user,
        purchases,
        stats,
        installmentTotals,
        progress: stats.total > 0 ? Math.round((stats.paid / stats.total) * 100) : 0
      };
    });
}

function listenAllPurchases() {
  if (state.unsubscribeAllPurchases) {
    state.unsubscribeAllPurchases();
  }

  const allPurchasesRef = ref(db, "purchases");
  const callback = (snapshot) => {
    state.allPurchases = snapshot.val() || {};
    renderOverview();
  };

  onValue(allPurchasesRef, callback);
  state.unsubscribeAllPurchases = () => off(allPurchasesRef, "value", callback);
}

function renderOverview() {
  if (!els.userOverviewList) return;

  const summaries = getUserSummaries();
  const groupStats = summaries.reduce((totals, summary) => {
    totals.total += summary.stats.total;
    totals.paid += summary.stats.paid;
    totals.remaining += summary.stats.remaining;
    totals.upcoming += summary.stats.upcoming;
    totals.purchases += summary.purchases.length;
    return totals;
  }, { total: 0, paid: 0, remaining: 0, upcoming: 0, purchases: 0 });

  els.groupTotalDebt.textContent = formatMoney(groupStats.total);
  els.groupPaidAmount.textContent = formatMoney(groupStats.paid);
  els.groupRemainingAmount.textContent = formatMoney(groupStats.remaining);
  els.groupUserCount.textContent = String(summaries.length);
  els.groupSummary.textContent = `${summaries.length} kullanıcı, ${groupStats.purchases} satın alma`;

  els.emptyOverview.classList.toggle("is-hidden", summaries.length > 0);
  els.userOverviewList.innerHTML = summaries.map(renderOverviewCard).join("");
}

function renderOverviewCard(summary) {
  const paidInstallments = summary.installmentTotals.paid;
  const totalInstallments = summary.installmentTotals.total;
  const activeLabel = summary.userId === state.currentUserId ? "Aktif kullanıcı" : "Kayıtlı kullanıcı";

  return `
    <article class="overview-card">
      <div class="overview-card-head">
        <h3>${escapeHtml(summary.user.name)}</h3>
        <p>${activeLabel} - ${summary.purchases.length} satın alma</p>
      </div>
      <div class="overview-money">
        <strong>${formatMoney(summary.stats.remaining)}</strong>
        <span>Kalan borç</span>
      </div>
      <div class="overview-progress">
        <div class="progress-track" aria-label="Ödeme ilerlemesi">
          <div class="progress-fill" style="width: ${summary.progress}%"></div>
        </div>
        <div class="purchase-meta">
          <span>${summary.progress}% ödendi</span>
          <span>${paidInstallments}/${totalInstallments} taksit</span>
        </div>
      </div>
      <div class="overview-stats">
        <div class="overview-stat">
          <span>Toplam</span>
          <strong>${formatMoney(summary.stats.total)}</strong>
        </div>
        <div class="overview-stat">
          <span>Ödenen</span>
          <strong>${formatMoney(summary.stats.paid)}</strong>
        </div>
        <div class="overview-stat">
          <span>Yaklaşan</span>
          <strong>${formatMoney(summary.stats.upcoming)}</strong>
        </div>
      </div>
    </article>
  `;
}

function listenPurchases(userId) {
  if (state.unsubscribePurchases) {
    state.unsubscribePurchases();
  }

  const purchaseRef = ref(db, `purchases/${userId}`);
  const callback = (snapshot) => {
    state.purchases = snapshot.val() || {};
    renderDashboard();
    renderHistory();
  };

  onValue(purchaseRef, callback);
  state.unsubscribePurchases = () => off(purchaseRef, "value", callback);
}

function renderDashboard() {
  const purchases = getPurchaseEntries();
  const stats = calculateStats();

  els.totalDebt.textContent = formatMoney(stats.total);
  els.paidAmount.textContent = formatMoney(stats.paid);
  els.remainingAmount.textContent = formatMoney(stats.remaining);
  els.upcomingAmount.textContent = formatMoney(stats.upcoming);
  els.purchaseCount.textContent = `${purchases.length} kayıt`;

  els.emptyPurchases.classList.toggle("is-hidden", purchases.length > 0);
  els.purchaseList.innerHTML = purchases.map(renderPurchaseCard).join("");
}

function renderPurchaseCard(purchase) {
  const installments = getInstallmentEntries(purchase);
  const paidCount = installments.filter((installment) => installment.paid).length;
  const progress = installments.length ? Math.round((paidCount / installments.length) * 100) : 0;
  const nextInstallment = installments.find((installment) => !installment.paid);
  const nextLabel = nextInstallment ? `${formatDate(nextInstallment.dueDate)} - ${formatMoney(nextInstallment.amount)}` : "Tamamlandı";

  return `
    <article class="purchase-card" data-purchase-id="${escapeHtml(purchase.id)}">
      <div class="purchase-head">
        <div class="purchase-title">
          <h3>${escapeHtml(purchase.title)}</h3>
          <p>${escapeHtml(purchase.merchant || "Mağaza belirtilmedi")}</p>
        </div>
        <div class="purchase-amount">${formatMoney(purchase.amount)}</div>
      </div>
      <div class="progress-track" aria-label="Taksit ilerlemesi">
        <div class="progress-fill" style="width: ${progress}%"></div>
      </div>
      <div class="purchase-meta">
        <span>${paidCount}/${installments.length} taksit ödendi</span>
        <span>Sıradaki: ${nextLabel}</span>
      </div>
      <div class="purchase-actions">
        <button class="mini-action" type="button" data-detail="${escapeHtml(purchase.id)}">
          <i class="bi bi-list-check"></i>
          Detay
        </button>
        <button class="mini-action danger" type="button" data-delete="${escapeHtml(purchase.id)}">
          <i class="bi bi-trash3"></i>
          Sil
        </button>
      </div>
    </article>
  `;
}

function renderHistory() {
  const history = [];

  getPurchaseEntries().forEach((purchase) => {
    getInstallmentEntries(purchase)
      .filter((installment) => installment.paid)
      .forEach((installment) => {
        history.push({
          purchaseTitle: purchase.title,
          no: installment.no,
          amount: installment.amount,
          dueDate: installment.dueDate,
          paidAt: installment.paidAt
        });
      });
  });

  history.sort((a, b) => String(b.paidAt || "").localeCompare(String(a.paidAt || "")));
  els.emptyHistory.classList.toggle("is-hidden", history.length > 0);

  els.historyList.innerHTML = history.map((item) => `
    <article class="history-item">
      <div class="history-main">
        <strong>${escapeHtml(item.purchaseTitle)} - ${item.no}. taksit</strong>
        <span>Ödeme: ${item.paidAt ? dateFormatter.format(new Date(item.paidAt)) : formatDate(item.dueDate)}</span>
      </div>
      <div class="history-amount">${formatMoney(item.amount)}</div>
    </article>
  `).join("");
}

function openDetail(purchaseId) {
  const purchase = state.purchases[purchaseId];
  if (!purchase) return;

  const installments = getInstallmentEntries(purchase);
  const paidCount = installments.filter((installment) => installment.paid).length;

  els.detailTitle.textContent = purchase.title;
  els.detailMeta.innerHTML = `
    <span class="meta-pill">${formatMoney(purchase.amount)}</span>
    <span class="meta-pill">${paidCount}/${installments.length} taksit</span>
    <span class="meta-pill">${escapeHtml(purchase.merchant || "Mağaza yok")}</span>
  `;

  els.installmentList.innerHTML = installments.map((installment) => {
    const daysUntil = getDaysUntil(installment.dueDate);
    const dueLabel = installment.paid
      ? "Ödendi"
      : daysUntil < 0
        ? `${Math.abs(daysUntil)} gün gecikti`
        : daysUntil === 0
          ? "Bugün"
          : `${daysUntil} gün kaldı`;

    return `
      <article class="installment-row ${installment.paid ? "is-paid" : ""}">
        <div class="installment-main">
          <strong>${installment.no}. taksit</strong>
          <span>${formatDate(installment.dueDate)} - ${dueLabel}</span>
        </div>
        <div class="installment-amount">
          <div>${formatMoney(installment.amount)}</div>
          <span class="status-pill ${installment.paid ? "paid" : "waiting"}">
            <i class="bi ${installment.paid ? "bi-check2" : "bi-hourglass-split"}"></i>
            ${installment.paid ? "Ödendi" : "Bekliyor"}
          </span>
        </div>
        <button class="mini-action" type="button" data-toggle-paid="${escapeHtml(purchaseId)}" data-installment="${installment.no}">
          <i class="bi ${installment.paid ? "bi-arrow-counterclockwise" : "bi-check2"}"></i>
          ${installment.paid ? "Geri Al" : "Ödendi"}
        </button>
      </article>
    `;
  }).join("");

  if (!els.detailDialog.open) {
    els.detailDialog.showModal();
  }
}

function switchTab(tabName) {
  els.tabs.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.tab === tabName);
  });

  Object.entries(els.panels).forEach(([name, panel]) => {
    panel.classList.toggle("is-active", name === tabName);
  });
}

async function handleLogin(event) {
  event.preventDefault();
  setError(els.loginError);

  const userId = els.userSelect.value;
  const user = state.users[userId];
  if (!user) {
    setError(els.loginError, "Kullanıcı bulunamadı.");
    return;
  }

  const passwordHash = await hashPassword(els.passwordInput.value);
  if (passwordHash !== user.passwordHash) {
    setError(els.loginError, "Şifre hatalı.");
    return;
  }

  state.currentUserId = userId;
  els.passwordInput.value = "";
  els.welcomeTitle.textContent = `Merhaba, ${user.name}`;
  els.loginView.classList.add("is-hidden");
  els.appView.classList.remove("is-hidden");
  renderUsers();
  listenPurchases(userId);
  listenAllPurchases();
  showToast("Giriş yapıldı.");
}

async function handleAddUser(event) {
  event.preventDefault();
  setError(els.userFormError);

  const name = els.newUserName.value.trim();
  const password = els.newUserPassword.value;
  const duplicate = Object.values(state.users).some((user) => (
    String(user.name || "").toLocaleLowerCase("tr-TR") === name.toLocaleLowerCase("tr-TR")
  ));

  if (name.length < 2) {
    setError(els.userFormError, "Kullanıcı adı en az 2 karakter olmalı.");
    return;
  }

  if (password.length < 4) {
    setError(els.userFormError, "Şifre en az 4 karakter olmalı.");
    return;
  }

  if (duplicate) {
    setError(els.userFormError, "Bu kullanıcı zaten var.");
    return;
  }

  const newUserRef = push(ref(db, "users"));
  await set(newUserRef, {
    name,
    passwordHash: await hashPassword(password),
    createdAt: new Date().toISOString()
  });

  els.addUserForm.reset();
  showToast("Kullanıcı eklendi.");
}

async function handlePurchaseSubmit(event) {
  event.preventDefault();
  setError(els.purchaseFormError);

  const title = els.purchaseTitle.value.trim();
  const amount = Number(els.purchaseAmount.value);
  const installmentCount = Number(els.installmentCount.value);
  const firstDueDate = els.firstDueDate.value;

  if (!title || !amount || amount <= 0 || !installmentCount || installmentCount < 1 || !firstDueDate) {
    setError(els.purchaseFormError, "Satın alma bilgilerini kontrol et.");
    return;
  }

  const purchaseRef = push(ref(db, `purchases/${state.currentUserId}`));
  await set(purchaseRef, {
    title,
    merchant: els.purchaseMerchant.value.trim(),
    amount,
    installmentCount,
    firstDueDate,
    note: els.purchaseNote.value.trim(),
    createdAt: new Date().toISOString(),
    installments: makeInstallments(amount, installmentCount, firstDueDate)
  });

  els.purchaseForm.reset();
  els.installmentCount.value = "3";
  els.firstDueDate.value = toDateInputValue(getToday());
  els.purchaseDialog.close();
  showToast("Satın alma eklendi.");
}

async function toggleInstallmentPaid(purchaseId, installmentNo) {
  const installment = state.purchases?.[purchaseId]?.installments?.[installmentNo];
  if (!installment) return;

  await update(ref(db, `purchases/${state.currentUserId}/${purchaseId}/installments/${installmentNo}`), {
    paid: !installment.paid,
    paidAt: installment.paid ? "" : new Date().toISOString()
  });

  openDetail(purchaseId);
  showToast(installment.paid ? "Taksit bekliyor olarak işaretlendi." : "Taksit ödendi.");
}

async function deletePurchase(purchaseId) {
  const purchase = state.purchases[purchaseId];
  if (!purchase) return;

  const ok = window.confirm(`${purchase.title} kaydı silinsin mi?`);
  if (!ok) return;

  await remove(ref(db, `purchases/${state.currentUserId}/${purchaseId}`));
  showToast("Satın alma silindi.");
}

function bindEvents() {
  els.loginForm.addEventListener("submit", handleLogin);
  els.addUserForm.addEventListener("submit", handleAddUser);
  els.purchaseForm.addEventListener("submit", handlePurchaseSubmit);

  els.openPurchaseDialog.addEventListener("click", () => {
    els.purchaseForm.reset();
    els.installmentCount.value = "3";
    els.firstDueDate.value = toDateInputValue(getToday());
    setError(els.purchaseFormError);
    els.purchaseDialog.showModal();
  });

  els.logoutButton.addEventListener("click", () => {
    state.currentUserId = "";
    state.purchases = {};
    if (state.unsubscribePurchases) state.unsubscribePurchases();
    if (state.unsubscribeAllPurchases) state.unsubscribeAllPurchases();
    state.unsubscribePurchases = null;
    state.unsubscribeAllPurchases = null;
    els.appView.classList.add("is-hidden");
    els.loginView.classList.remove("is-hidden");
    showToast("Çıkış yapıldı.");
  });

  els.refreshButton.addEventListener("click", () => {
    renderDashboard();
    renderHistory();
    renderOverview();
    showToast("Ekran yenilendi.");
  });

  els.tabs.forEach((button) => {
    button.addEventListener("click", () => switchTab(button.dataset.tab));
  });

  document.querySelectorAll("[data-close-dialog]").forEach((button) => {
    button.addEventListener("click", () => {
      const dialog = button.closest("dialog");
      if (dialog) dialog.close();
    });
  });

  els.purchaseList.addEventListener("click", (event) => {
    const detailButton = event.target.closest("[data-detail]");
    const deleteButton = event.target.closest("[data-delete]");

    if (detailButton) {
      openDetail(detailButton.dataset.detail);
    }

    if (deleteButton) {
      deletePurchase(deleteButton.dataset.delete);
    }
  });

  els.installmentList.addEventListener("click", (event) => {
    const button = event.target.closest("[data-toggle-paid]");
    if (!button) return;
    toggleInstallmentPaid(button.dataset.togglePaid, button.dataset.installment);
  });
}

async function init() {
  bindEvents();
  els.firstDueDate.value = toDateInputValue(getToday());

  try {
    await ensureDefaultUser();
    listenUsers();
  } catch (error) {
    setError(els.loginError, `Başlatılamadı: ${error.message}`);
  }
}

init();
