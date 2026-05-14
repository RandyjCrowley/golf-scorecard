(() => {
  const form = document.getElementById("round-form");
  const holesContainer = document.getElementById("holes-container");
  const totalParEl = document.getElementById("total-par");
  const totalScoreEl = document.getElementById("total-score");
  const relativeParEl = document.getElementById("relative-par");
  const roundsList = document.getElementById("rounds-list");
  const listEmpty = document.getElementById("list-empty");
  const courseInput = document.getElementById("course-name");
  const playerInput = document.getElementById("player-name");
  const dateInput = document.getElementById("round-date");
  const editIdInput = document.getElementById("edit-round-id");
  const formTitle = document.getElementById("form-title");
  const saveBtn = document.getElementById("save-btn");
  const cancelEditBtn = document.getElementById("cancel-edit");
  const listPagination = document.getElementById("list-pagination");
  const pagerPrev = document.getElementById("pager-prev");
  const pagerNext = document.getElementById("pager-next");
  const pagerStatus = document.getElementById("pager-status");
  const listFiltersForm = document.getElementById("list-filters");
  const filterPlayer = document.getElementById("filter-player-name");
  const filterCourse = document.getElementById("filter-course-name");
  const filterClearBtn = document.getElementById("filter-clear");

  const PAGE_SIZE = 3;
  let listPage = 0;

  const MSG_LIST_EMPTY = "No rounds yet. Save one above.";
  const MSG_LIST_NO_MATCH = "No rounds match these filters.";

  const defaultPars = () => Array.from({ length: 18 }, (_, i) => (i % 3 === 0 ? 3 : i % 3 === 1 ? 4 : 5));

  function todayISODate() {
    const d = new Date();
    const z = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}`;
  }

  function getHoleCount() {
    const sel = form.querySelector('input[name="holeCount"]:checked');
    return sel ? Number(sel.value) : 18;
  }

  function formatRelative(rel) {
    if (rel === 0) return "E";
    return rel > 0 ? `+${rel}` : String(rel);
  }

  function recalcTotals() {
    const cards = holesContainer.querySelectorAll(".hole-card");
    let totalPar = 0;
    let totalScore = 0;
    cards.forEach((card) => {
      const par = Number(card.querySelector('[data-field="par"]').value) || 0;
      const score = Number(card.querySelector('[data-field="score"]').value) || 0;
      totalPar += par;
      totalScore += score;
    });
    const rel = totalScore - totalPar;
    totalParEl.textContent = String(totalPar);
    totalScoreEl.textContent = String(totalScore);
    relativeParEl.textContent = formatRelative(rel);
  }

  function buildHoleInputs(count, existingHoles) {
    holesContainer.innerHTML = "";
    const pars = defaultPars();
    for (let i = 1; i <= count; i += 1) {
      const existing = existingHoles && existingHoles[i - 1];
      const par = existing ? existing.par : pars[i - 1] ?? 4;
      const score = existing ? existing.score : par;

      const wrap = document.createElement("div");
      wrap.className = "hole-card";
      wrap.innerHTML = `
        <h3>Hole ${i}</h3>
        <label>Par
          <input type="number" min="1" max="10" data-field="par" value="${par}" />
        </label>
        <label>Score
          <input type="number" min="1" max="20" data-field="score" value="${score}" />
        </label>
      `;
      holesContainer.appendChild(wrap);
    }
    holesContainer.querySelectorAll("input").forEach((el) => {
      el.addEventListener("input", recalcTotals);
    });
    recalcTotals();
  }

  function collectHolesFromForm() {
    const cards = holesContainer.querySelectorAll(".hole-card");
    const holes = [];
    cards.forEach((card, idx) => {
      const par = Number(card.querySelector('[data-field="par"]').value);
      const score = Number(card.querySelector('[data-field="score"]').value);
      holes.push({
        holeNumber: idx + 1,
        par: Number.isFinite(par) ? par : 4,
        score: Number.isFinite(score) ? score : 4,
      });
    });
    return holes;
  }

  function resetFormNew() {
    editIdInput.value = "";
    formTitle.textContent = "New round";
    saveBtn.textContent = "Save round";
    cancelEditBtn.classList.add("hidden");
    courseInput.value = "";
    playerInput.value = "";
    dateInput.value = todayISODate();
    form.querySelector('input[name="holeCount"][value="18"]').checked = true;
    buildHoleInputs(18);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function filtersActive() {
    return Boolean(filterPlayer.value.trim() || filterCourse.value.trim());
  }

  function roundListPageUrl() {
    const params = new URLSearchParams();
    params.set("limit", String(PAGE_SIZE));
    params.set("offset", String(listPage * PAGE_SIZE));
    const p = filterPlayer.value.trim();
    const c = filterCourse.value.trim();
    if (p) params.set("playerName", p);
    if (c) params.set("courseName", c);
    return `/api/rounds/page?${params.toString()}`;
  }

  function totalPages(total) {
    if (total <= 0) return 0;
    return Math.ceil(total / PAGE_SIZE);
  }

  function updatePager(total) {
    if (total === 0) {
      listPagination.classList.add("hidden");
      return;
    }
    listPagination.classList.remove("hidden");
    const pages = totalPages(total);
    const safePage = Math.min(listPage, Math.max(0, pages - 1));
    listPage = safePage;
    const pageNum = safePage + 1;
    const start = safePage * PAGE_SIZE + 1;
    const end = Math.min(safePage * PAGE_SIZE + PAGE_SIZE, total);
    pagerStatus.textContent = `Page ${pageNum} of ${pages} · ${start}–${end} of ${total}`;
    pagerPrev.disabled = safePage <= 0;
    pagerNext.disabled = safePage >= pages - 1;
  }

  async function loadRounds(options = {}) {
    const { resetToFirstPage = false } = options;
    if (resetToFirstPage) listPage = 0;

    const res = await fetch(roundListPageUrl());
    if (!res.ok) throw new Error("Failed to load rounds");
    const data = await res.json();
    const rounds = data.items;
    const total = data.total;

    const pages = totalPages(total);
    if (total > 0 && listPage > pages - 1) {
      listPage = pages - 1;
      return loadRounds(options);
    }

    roundsList.innerHTML = "";
    if (!rounds.length && total === 0) {
      listEmpty.classList.remove("hidden");
      listEmpty.textContent = filtersActive() ? MSG_LIST_NO_MATCH : MSG_LIST_EMPTY;
      listPagination.classList.add("hidden");
      return;
    }
    listEmpty.classList.add("hidden");
    updatePager(total);

    rounds.forEach((r) => {
      const li = document.createElement("li");
      li.className = "round-item";
      const relStr = formatRelative(r.relativeToPar);
      li.innerHTML = `
        <h3>${escapeHtml(r.courseName)}</h3>
        <p class="round-meta">${escapeHtml(r.playerName)} · ${escapeHtml(r.date)}</p>
        <p class="round-stats">Score: <strong>${r.totalScore}</strong> · Par: ${r.totalPar} · ${relStr}</p>
        <div class="round-actions">
          <button type="button" class="btn small ghost" data-action="edit" data-id="${escapeAttr(r.id)}">Edit</button>
          <button type="button" class="btn small danger" data-action="delete" data-id="${escapeAttr(r.id)}">Delete</button>
        </div>
      `;
      roundsList.appendChild(li);
    });
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escapeAttr(s) {
    return escapeHtml(s).replace(/'/g, "&#39;");
  }

  async function submitRound(ev) {
    ev.preventDefault();
    const payload = {
      courseName: courseInput.value.trim(),
      playerName: playerInput.value.trim(),
      date: dateInput.value,
      holes: collectHolesFromForm(),
    };
    const editingId = editIdInput.value.trim();
    const url = editingId ? `/api/rounds/${encodeURIComponent(editingId)}` : "/api/rounds";
    const method = editingId ? "PUT" : "POST";
    const res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(err.detail || "Could not save round");
      return;
    }
    resetFormNew();
    await loadRounds({ resetToFirstPage: true });
  }

  roundsList.addEventListener("click", async (ev) => {
    const btn = ev.target.closest("button[data-action]");
    if (!btn) return;
    const id = btn.getAttribute("data-id");
    if (btn.dataset.action === "delete") {
      if (!confirm("Delete this round?")) return;
      const res = await fetch(`/api/rounds/${encodeURIComponent(id)}`, { method: "DELETE" });
      if (!res.ok) {
        alert("Could not delete round");
        return;
      }
      await loadRounds();
      if (editIdInput.value === id) resetFormNew();
    }
    if (btn.dataset.action === "edit") {
      const res = await fetch(`/api/rounds/${encodeURIComponent(id)}`);
      if (!res.ok) {
        alert("Round not found");
        return;
      }
      const r = await res.json();
      editIdInput.value = r.id;
      formTitle.textContent = "Edit round";
      saveBtn.textContent = "Update round";
      cancelEditBtn.classList.remove("hidden");
      courseInput.value = r.courseName;
      playerInput.value = r.playerName;
      dateInput.value = r.date;
      const n = r.holes.length;
      const holeCountRadio = form.querySelector(`input[name="holeCount"][value="${n === 9 ? 9 : 18}"]`);
      if (holeCountRadio) holeCountRadio.checked = true;
      buildHoleInputs(n, r.holes);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  });

  form.querySelectorAll('input[name="holeCount"]').forEach((r) => {
    r.addEventListener("change", () => {
      const editing = editIdInput.value.trim();
      const count = getHoleCount();
      if (editing) {
        buildHoleInputs(count);
      } else {
        buildHoleInputs(count);
      }
    });
  });

  cancelEditBtn.addEventListener("click", () => resetFormNew());

  pagerPrev.addEventListener("click", () => {
    if (listPage <= 0) return;
    listPage -= 1;
    loadRounds().catch(() => {});
  });
  pagerNext.addEventListener("click", () => {
    listPage += 1;
    loadRounds().catch(() => {});
  });

  function applyListFilters(ev) {
    if (ev) ev.preventDefault();
    listPage = 0;
    loadRounds().catch(() => {});
  }

  listFiltersForm.addEventListener("submit", applyListFilters);
  filterClearBtn.addEventListener("click", () => {
    filterPlayer.value = "";
    filterCourse.value = "";
    listPage = 0;
    loadRounds().catch(() => {});
  });

  dateInput.value = todayISODate();
  buildHoleInputs(18);
  form.addEventListener("submit", submitRound);
  loadRounds().catch(() => {
    listEmpty.textContent = "Could not load rounds. Is the server running?";
  });
})();
