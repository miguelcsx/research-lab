(() => {
  const status = document.querySelector("[data-live-status]");

  // ---- List controller: filter + sort + paginate -------------------------
  class ListView {
    constructor(scope) {
      this.scope = scope;
      this.list = scope.querySelector("[data-list]");
      if (!this.list) return;
      this.isTable = this.list.tagName === "TABLE";
      this.size = parseInt(this.list.dataset.pageSize || "25", 10);
      this.page = 0;
      this.filter = scope.querySelector("[data-filter]");
      this.pager = scope.querySelector("[data-pager]");

      if (this.filter) {
        this.filter.addEventListener("input", () => {
          this.page = 0;
          this.render();
        });
      }
      this.setupSort();
      this.render();
    }

    items() {
      if (this.isTable) return this.list.tBodies[0] ? [...this.list.tBodies[0].rows] : [];
      return [...this.list.children].filter((el) => el.matches("[data-page-item]"));
    }

    matched() {
      const query = (this.filter?.value || "").trim().toLowerCase();
      if (!query) return this.items();
      return this.items().filter((item) => item.textContent.toLowerCase().includes(query));
    }

    setupSort() {
      if (!this.isTable) return;
      const headers = this.list.querySelectorAll("th[data-sort]");
      const offset = this.list.querySelector("th.col-check") ? 1 : 0;
      headers.forEach((header, columnIndex) => {
        header.addEventListener("click", () => {
          const body = this.list.tBodies[0];
          if (!body) return;
          const dir = header.dataset.dir === "asc" ? "desc" : "asc";
          for (const other of headers) delete other.dataset.dir;
          header.dataset.dir = dir;
          const rows = [...body.rows];
          rows.sort((a, b) => {
            const cellA = a.cells[columnIndex + offset];
            const cellB = b.cells[columnIndex + offset];
            const av = (cellA?.dataset.sort ?? cellA?.textContent ?? "").trim();
            const bv = (cellB?.dataset.sort ?? cellB?.textContent ?? "").trim();
            const an = parseFloat(av), bn = parseFloat(bv);
            const numeric = !isNaN(an) && !isNaN(bn) && /^[-\d.]+$/.test(av) && /^[-\d.]+$/.test(bv);
            const cmp = numeric ? an - bn : av.localeCompare(bv, undefined, { numeric: true });
            return dir === "asc" ? cmp : -cmp;
          });
          for (const row of rows) body.appendChild(row);
          this.page = 0;
          this.render();
        });
      });
    }

    render() {
      const all = this.items();
      const matched = this.matched();
      const total = matched.length;
      const pages = Math.max(1, Math.ceil(total / this.size));
      if (this.page >= pages) this.page = pages - 1;
      const start = this.page * this.size;
      const end = start + this.size;
      const visible = new Set(matched.slice(start, end));
      for (const item of all) item.hidden = !visible.has(item);
      this.renderPager(total, start, Math.min(end, total));
    }

    renderPager(total, start, shownEnd) {
      if (!this.pager) return;
      const pages = Math.max(1, Math.ceil(total / this.size));
      if (total <= this.size) {
        this.pager.innerHTML = total === 0
          ? `<span class="pager-info">No matches</span>`
          : `<span class="pager-info">${total} item${total === 1 ? "" : "s"}</span>`;
        return;
      }
      this.pager.innerHTML = `
        <span class="pager-info">${start + 1}–${shownEnd} of ${total}</span>
        <div class="pager-controls">
          <button type="button" class="button ghost" data-prev ${this.page === 0 ? "disabled" : ""}>Prev</button>
          <span class="pager-page">Page ${this.page + 1} / ${pages}</span>
          <button type="button" class="button ghost" data-next ${this.page >= pages - 1 ? "disabled" : ""}>Next</button>
        </div>`;
      this.pager.querySelector("[data-prev]")?.addEventListener("click", () => {
        this.page = Math.max(0, this.page - 1);
        this.render();
        this.scope.scrollIntoView({ block: "nearest" });
      });
      this.pager.querySelector("[data-next]")?.addEventListener("click", () => {
        this.page += 1;
        this.render();
        this.scope.scrollIntoView({ block: "nearest" });
      });
    }
  }

  for (const scope of document.querySelectorAll("[data-list-scope]")) new ListView(scope);

  // ---- Compare selection --------------------------------------------------
  const bar = document.querySelector("[data-compare-bar]");
  if (bar) {
    const items = () => [...document.querySelectorAll("[data-compare-item]")];
    const countEl = bar.querySelector("[data-compare-count]");
    const goEl = bar.querySelector("[data-compare-go]");
    const clearEl = bar.querySelector("[data-compare-clear]");
    const allEl = document.querySelector("[data-compare-all]");

    const sync = () => {
      const selected = items().filter((box) => box.checked).map((box) => box.value);
      bar.hidden = selected.length === 0;
      if (countEl) countEl.textContent = `${selected.length} selected`;
      if (goEl) {
        goEl.href = `/compare?runs=${selected.map(encodeURIComponent).join(",")}`;
        goEl.setAttribute("aria-disabled", String(selected.length < 2));
      }
    };

    for (const box of items()) box.addEventListener("change", sync);
    if (allEl) {
      allEl.addEventListener("change", () => {
        for (const box of items()) {
          if (!box.closest("[data-filter-row]")?.hidden) box.checked = allEl.checked;
        }
        sync();
      });
    }
    if (clearEl) {
      clearEl.addEventListener("click", () => {
        for (const box of items()) box.checked = false;
        if (allEl) allEl.checked = false;
        sync();
      });
    }
    sync();
  }

  // ---- Liveness ping ------------------------------------------------------
  const dot = document.querySelector("[data-live-dot]");
  function setLive(stale) {
    if (status) {
      status.textContent = stale ? "Reconnecting…" : "Live";
      status.classList.toggle("is-stale", stale);
    }
    if (dot) dot.classList.toggle("is-stale", stale);
  }
  async function poll() {
    const refreshables = document.querySelectorAll("[data-refresh-url]");
    if (refreshables.length === 0) return;
    try {
      await Promise.all([...refreshables].map((node) => fetch(node.dataset.refreshUrl, { cache: "no-store" })));
      setLive(false);
    } catch (_error) {
      setLive(true);
    }
  }
  window.setInterval(poll, 5000);
})();
