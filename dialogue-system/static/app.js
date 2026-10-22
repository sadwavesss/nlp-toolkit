// === LAB 6: Полнофункциональный клиент диалоговой системы ===
// Связан с Flask backend через REST API.

// ============================================================
//   Утилиты
// ============================================================

// Карта эмодзи для известных категорий и животных
const EMOJI_MAP = {
    "тигр": "🐅", "лев": "🦁", "гепард": "🐆", "волк": "🐺",
    "медведь": "🐻", "лиса": "🦊", "пингвин": "🐧", "дельфин": "🐬",
    "слон": "🐘", "жираф": "🦒", "зебра": "🦓", "акула": "🦈",
    "кит": "🐋", "обезьяна": "🐒", "кролик": "🐇", "лошадь": "🐎",
    "корова": "🐄", "собака": "🐕", "кошка": "🐈", "крокодил": "🐊",
    "носорог": "🦏", "бегемот": "🦛"
};

const CATEGORY_EMOJI = {
    "хищник": "🥩",
    "травоядное": "🌿",
    "всеядное": "🍽️",
    "птица": "🪶",
    "млекопитающее": "🌊"
};

const CATEGORY_LABEL = {
    "хищник": "Хищники",
    "травоядное": "Травоядные",
    "всеядное": "Всеядные",
    "птица": "Птицы",
    "млекопитающее": "Морские"
};

function emojiFor(animal) {
    return EMOJI_MAP[animal?.toLowerCase()] || "🐾";
}

function escapeHtml(s) {
    const div = document.createElement("div");
    div.textContent = s ?? "";
    return div.innerHTML;
}

function formatDate(iso) {
    if (!iso) return "—";
    const d = new Date(iso.replace(" ", "T"));
    if (isNaN(d.getTime())) return iso;
    const today = new Date();
    const yesterday = new Date(today.getTime() - 86400000);
    const sameDay = d.toDateString() === today.toDateString();
    const sameYesterday = d.toDateString() === yesterday.toDateString();
    const time = d.toTimeString().slice(0, 5);
    if (sameDay) return `Сегодня, ${time}`;
    if (sameYesterday) return `Вчера, ${time}`;
    return d.toLocaleDateString("ru-RU", { day: "numeric", month: "short" }) + ", " + time;
}

function timeNow() {
    const d = new Date();
    return d.getHours().toString().padStart(2, "0") + ":" +
           d.getMinutes().toString().padStart(2, "0");
}

async function api(url, options = {}) {
    const res = await fetch(url, {
        headers: { "Content-Type": "application/json" },
        ...options
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

// ============================================================
//   Состояние
// ============================================================
const state = {
    currentView: "chat",
    sending: false,
    animals: [],
    historyLoaded: false,
    topicsLoaded: false
};

// ============================================================
//   Чат
// ============================================================
const chatMessages = document.getElementById("chatMessages");
const messageInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const clearBtn = document.getElementById("clearBtn");
const newDialogBtn = document.getElementById("newDialogBtn");

function renderMessage(container, sender, text, intent, entities, ts) {
    const div = document.createElement("div");
    div.className = `message ${sender}`;
    const senderName = sender === "user" ? "Вы" : "Система";
    const avatar = sender === "user" ? "👤" : "🤖";
    const time = ts ? formatDate(ts).split(", ").pop() : timeNow();

    let metaHTML = `<span class="time">${escapeHtml(time)}</span>`;
    if (intent) {
        metaHTML = `<span class="intent-tag">intent: ${escapeHtml(intent)}</span>` + metaHTML;
    }
    if (Array.isArray(entities)) {
        for (const e of entities) {
            if (!e?.type) continue;
            metaHTML = `<span class="entity-tag">${escapeHtml(e.type)}: ${escapeHtml(e.text || e.value || "")}</span>` + metaHTML;
        }
    }

    // Текст: преобразуем переносы и markdown-подобные **жирный**
    let safeText = escapeHtml(text || "");
    safeText = safeText.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    safeText = safeText.replace(/\n/g, "<br>");

    if (sender === "user") {
        div.innerHTML = `
            <div class="message-content">
                <div class="sender">${senderName}</div>
                <div class="text">${safeText}</div>
                <div class="meta">${metaHTML}</div>
            </div>
            <div class="avatar">${avatar}</div>
        `;
    } else {
        div.innerHTML = `
            <div class="avatar">${avatar}</div>
            <div class="message-content">
                <div class="sender">${senderName}</div>
                <div class="text">${safeText}</div>
                <div class="meta">${metaHTML}</div>
            </div>
        `;
    }

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function showTyping() {
    const t = document.createElement("div");
    t.className = "typing-indicator";
    t.id = "typingIndicator";
    t.innerHTML = `<div class="dot"></div><div class="dot"></div><div class="dot"></div>`;
    chatMessages.appendChild(t);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function hideTyping() {
    document.getElementById("typingIndicator")?.remove();
}

async function sendMessage() {
    if (state.sending) return;
    const text = messageInput.value.trim();
    if (!text) return;

    renderMessage(chatMessages, "user", text);
    messageInput.value = "";
    state.sending = true;
    sendBtn.disabled = true;
    showTyping();

    try {
        const data = await api("/api/send_message", {
            method: "POST",
            body: JSON.stringify({ message: text })
        });
        hideTyping();
        if (data.error) {
            renderMessage(chatMessages, "system", `Ошибка: ${data.error}`, "error");
        } else {
            renderMessage(
                chatMessages,
                "system",
                data.response,
                data.intent,
                data.entities
            );
        }
    } catch (e) {
        hideTyping();
        renderMessage(chatMessages, "system",
            "Ошибка соединения с сервером. Попробуйте позже.", "error");
        console.error(e);
    } finally {
        state.sending = false;
        sendBtn.disabled = false;
        messageInput.focus();
    }
}

async function loadHistoryIntoChat() {
    try {
        const data = await api("/api/get_history");
        chatMessages.innerHTML = "";
        if (data.history?.length) {
            for (const m of data.history) {
                renderMessage(chatMessages, m.sender, m.message,
                    m.intent, m.entities, m.timestamp);
            }
        } else {
            renderMessage(chatMessages, "system",
                "Здравствуйте! Я — диалоговая система по тематике «Животные мира». Могу рассказать о различных животных, их среде обитания, питании и интересных фактах. О чём хотите узнать?",
                "greeting");
        }
    } catch (e) {
        console.error("Не удалось загрузить историю:", e);
    }
}

sendBtn.addEventListener("click", sendMessage);
messageInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendMessage();
    else if (e.key === "Escape") messageInput.value = "";
});

document.querySelectorAll(".chip").forEach(chip => {
    chip.addEventListener("click", () => {
        messageInput.value = chip.dataset.text;
        sendMessage();
    });
});

clearBtn?.addEventListener("click", () => {
    if (!confirm("Очистить окно диалога? (история на сервере останется)")) return;
    chatMessages.innerHTML = "";
    renderMessage(chatMessages, "system",
        "Окно очищено. Чем могу помочь?", "greeting");
});

newDialogBtn?.addEventListener("click", async () => {
    if (!confirm("Закрыть текущий диалог и начать новый?")) return;
    try {
        await api("/api/new_dialogue", { method: "POST" });
        chatMessages.innerHTML = "";
        renderMessage(chatMessages, "system",
            "Начат новый диалог. О чём хотите узнать?", "greeting");
        switchView("chat");
        // обновляем историю и статистику в фоне
        state.historyLoaded = false;
    } catch (e) {
        alert("Ошибка создания нового диалога");
    }
});

// ============================================================
//   Навигация
// ============================================================

function switchView(viewName) {
    document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
    document.querySelector(`[data-view="${viewName}"]`)?.classList.add("active");

    document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
    document.getElementById(`view-${viewName}`)?.classList.add("active");

    state.currentView = viewName;

    if (viewName === "chat") setTimeout(() => messageInput.focus(), 50);
    if (viewName === "history") loadHistoryView();
    if (viewName === "topics") loadTopicsView();
}

document.querySelectorAll(".nav-item").forEach(item => {
    item.addEventListener("click", () => switchView(item.dataset.view));
});

// ============================================================
//   История диалогов
// ============================================================

const historyList = document.getElementById("historyList");
const historySearch = document.getElementById("historySearch");
const refreshHistoryBtn = document.getElementById("refreshHistoryBtn");

async function loadHistoryView() {
    if (state.historyLoaded) return;
    await Promise.all([loadStatistics(), loadDialoguesList()]);
    state.historyLoaded = true;
}

async function loadStatistics() {
    try {
        const stats = await api("/api/statistics");
        document.getElementById("statTotalDialogues").textContent = stats.total_dialogues ?? 0;
        document.getElementById("statTotalMessages").textContent = stats.total_messages ?? 0;
        document.getElementById("statUniqueAnimals").textContent = stats.unique_animals ?? 0;
        document.getElementById("statTopIntent").textContent = stats.top_intent || "—";
    } catch (e) {
        console.error("Ошибка загрузки статистики:", e);
    }
}

async function loadDialoguesList() {
    historyList.innerHTML = `<div class="empty-state">Загрузка...</div>`;
    try {
        const data = await api("/api/dialogues");
        const dialogues = data.dialogues || [];
        if (!dialogues.length) {
            historyList.innerHTML = `<div class="empty-state">История пуста. Начните общение в чате!</div>`;
            return;
        }
        historyList.innerHTML = "";
        for (const d of dialogues) {
            historyList.appendChild(renderHistoryItem(d));
        }
    } catch (e) {
        console.error(e);
        historyList.innerHTML = `<div class="empty-state">Ошибка загрузки истории.</div>`;
    }
}

function renderHistoryItem(d) {
    // Извлекаем первое ANIMAL для иконки
    let icon = "💬";
    let entityLabel = "";
    if (Array.isArray(d.first_entities)) {
        const animals = d.first_entities.filter(e => e.type === "ANIMAL").map(e => e.text);
        if (animals.length) {
            icon = emojiFor(animals[0]);
            entityLabel = `ANIMAL: ${animals.join(", ")}`;
        }
    }

    const div = document.createElement("div");
    div.className = "history-item";
    div.dataset.dialogueId = d.id;
    div.innerHTML = `
        <div class="history-icon">${icon}</div>
        <div class="history-body">
            <div class="history-title">${escapeHtml(d.first_user_message || "(пустой запрос)")}</div>
            <div class="history-preview">${escapeHtml(d.first_system_message || "—")}</div>
            <div class="history-meta">
                ${d.first_intent ? `<span class="intent-tag">intent: ${escapeHtml(d.first_intent)}</span>` : ""}
                ${entityLabel ? `<span class="entity-tag">${escapeHtml(entityLabel)}</span>` : ""}
                <span class="time">${escapeHtml(formatDate(d.created_at))}</span>
                <span class="messages-count">💬 ${d.message_count} сообщ.</span>
            </div>
        </div>
        <div class="history-actions">
            <button class="icon-btn" title="Открыть">→</button>
        </div>
    `;
    div.addEventListener("click", () => openDialogue(d.id));
    return div;
}

historySearch?.addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase().trim();
    document.querySelectorAll(".history-item").forEach(item => {
        const title = item.querySelector(".history-title").textContent.toLowerCase();
        const preview = item.querySelector(".history-preview").textContent.toLowerCase();
        const matches = !q || title.includes(q) || preview.includes(q);
        item.style.display = matches ? "" : "none";
    });
});

refreshHistoryBtn?.addEventListener("click", () => {
    state.historyLoaded = false;
    loadHistoryView();
});

// ============================================================
//   Просмотр конкретного диалога
// ============================================================

const dialogueMessages = document.getElementById("dialogueMessages");
const dialogueTitle = document.getElementById("dialogueTitle");
const dialogueSubtitle = document.getElementById("dialogueSubtitle");
const backToHistoryBtn = document.getElementById("backToHistoryBtn");

async function openDialogue(dialogueId) {
    switchView("dialogue");
    dialogueMessages.innerHTML = `<div class="empty-state">Загрузка...</div>`;
    dialogueTitle.textContent = `Просмотр диалога #${dialogueId}`;
    dialogueSubtitle.textContent = "Загрузка...";
    try {
        const data = await api(`/api/dialogue/${dialogueId}`);
        const messages = data.messages || [];
        dialogueMessages.innerHTML = "";
        if (!messages.length) {
            dialogueMessages.innerHTML = `<div class="empty-state">Диалог пуст</div>`;
        } else {
            for (const m of messages) {
                renderMessage(dialogueMessages, m.sender, m.message,
                    m.intent, m.entities, m.timestamp);
            }
        }
        dialogueSubtitle.textContent = `${messages.length} сообщений · только просмотр`;
    } catch (e) {
        dialogueMessages.innerHTML = `<div class="empty-state">Ошибка загрузки диалога</div>`;
        console.error(e);
    }
}

backToHistoryBtn?.addEventListener("click", () => switchView("history"));

// ============================================================
//   Тематика (база знаний)
// ============================================================

const topicsGrid = document.getElementById("topicsGrid");
const topicsCategories = document.getElementById("topicsCategories");
const topicsSearch = document.getElementById("topicsSearch");

async function loadTopicsView() {
    if (state.topicsLoaded) return;
    topicsGrid.innerHTML = `<div class="empty-state">Загрузка базы знаний...</div>`;
    try {
        const data = await api("/api/animals");
        state.animals = data.animals || [];
        renderCategories();
        renderTopics(state.animals);
        state.topicsLoaded = true;
    } catch (e) {
        topicsGrid.innerHTML = `<div class="empty-state">Ошибка загрузки</div>`;
        console.error(e);
    }
}

function renderCategories() {
    const categories = [...new Set(state.animals.map(a => a.category))];
    // Очистим, оставив "Все"
    topicsCategories.innerHTML = `<button class="category-tab active" data-category="all">Все</button>`;
    for (const cat of categories) {
        const btn = document.createElement("button");
        btn.className = "category-tab";
        btn.dataset.category = cat;
        const emoji = CATEGORY_EMOJI[cat] || "🐾";
        const label = CATEGORY_LABEL[cat] || cat;
        btn.textContent = `${emoji} ${label}`;
        topicsCategories.appendChild(btn);
    }
    topicsCategories.querySelectorAll(".category-tab").forEach(tab => {
        tab.addEventListener("click", () => {
            topicsCategories.querySelectorAll(".category-tab").forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
            const cat = tab.dataset.category;
            const filtered = cat === "all" ? state.animals : state.animals.filter(a => a.category === cat);
            renderTopics(filtered);
        });
    });
}

function renderTopics(animals) {
    if (!animals.length) {
        topicsGrid.innerHTML = `<div class="empty-state">Нет животных в этой категории</div>`;
        return;
    }
    topicsGrid.innerHTML = "";
    for (const a of animals) {
        const card = document.createElement("div");
        card.className = "topic-card";
        card.dataset.category = a.category;
        card.innerHTML = `
            <div class="topic-emoji">${emojiFor(a.name)}</div>
            <h3>${escapeHtml(a.name.charAt(0).toUpperCase() + a.name.slice(1))}</h3>
            <span class="topic-badge">${escapeHtml(a.category)}</span>
            <p>🌍 ${escapeHtml(a.habitat)}</p>
            <p>📏 ${escapeHtml(a.size)}</p>
            <button class="btn-link">Спросить →</button>
        `;
        card.querySelector(".btn-link").addEventListener("click", (e) => {
            e.stopPropagation();
            switchView("chat");
            setTimeout(() => {
                messageInput.value = `Расскажи про ${a.name}`;
                sendMessage();
            }, 100);
        });
        topicsGrid.appendChild(card);
    }
}

topicsSearch?.addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase().trim();
    if (!q) {
        renderTopics(state.animals);
        return;
    }
    const filtered = state.animals.filter(a =>
        a.name.toLowerCase().includes(q) ||
        a.category.toLowerCase().includes(q) ||
        a.habitat.toLowerCase().includes(q)
    );
    renderTopics(filtered);
});

// ============================================================
//   Инициализация
// ============================================================

(async function init() {
    await loadHistoryIntoChat();
    messageInput.focus();
})();
