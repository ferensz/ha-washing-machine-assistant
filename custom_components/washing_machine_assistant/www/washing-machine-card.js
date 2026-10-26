/**
 * Washing Machine Assistant card.
 *
 * The integration exposes a single control sensor; this card renders the
 * program picker, the current program's parameters, and favorites.
 */

const CATEGORY_ORDER = [
  "everyday",
  "special",
  "stains",
  "branded",
  "steam",
  "extras",
];

const CATEGORY_LABELS = {
  everyday: "Everyday",
  special: "Special care",
  stains: "Stains",
  branded: "Branded",
  steam: "Steam",
  extras: "Extras",
};

// hOn washing-machine `machMode` values (from the hOn translation file).
const MODE_LABELS = {
  "0": "Disconnected",
  "1": "Ready",
  "2": "Running",
  "3": "Paused",
  "4": "Scheduled",
  "5": "Scheduled",
  "6": "Error",
  "7": "Finished",
  "8": "Test",
  "9": "Ending",
};
const ACTIVE_MODES = new Set(["2", "3", "4", "5", "9"]);

const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[char]
  );

const asArray = (value) => (Array.isArray(value) ? value : []);

class WashingMachineCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._search = "";
    this._favoriteName = undefined;
    this._lastStamp = undefined;
  }

  static getStubConfig() {
    return { entity: "sensor.washing_machine_controls" };
  }

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error("Please define the Washing Machine Assistant control sensor.");
    }
    this._config = {
      entity: config.entity,
      title: config.title || "Washing machine",
      mode_entity: config.mode_entity || "sensor.washing_machine_mode",
      status_entity:
        config.status_entity || "binary_sensor.washing_machine_status",
      remaining_entity:
        config.remaining_entity || "sensor.washing_machine_remaining_time",
    };
  }

  set hass(hass) {
    this._hass = hass;
    const sensor = hass.states[this._config?.entity];
    if (!sensor) {
      this._renderMissing();
      return;
    }
    const mode = hass.states[this._config.mode_entity];
    const status = hass.states[this._config.status_entity];
    const remaining = hass.states[this._config.remaining_entity];
    const stamp = [
      sensor.last_updated || sensor.last_changed,
      mode?.last_updated || mode?.last_changed,
      status?.last_updated || status?.last_changed,
      remaining?.last_updated || remaining?.last_changed,
    ].join("|");
    if (stamp === this._lastStamp) return;
    this._lastStamp = stamp;
    this._render();
  }

  getCardSize() {
    return 9;
  }

  _renderMissing() {
    this.shadowRoot.innerHTML = `
      <style>${this._styles()}</style>
      <ha-card><div class="card-content">
        <div class="title">${esc(this._config?.title || "Washing machine")}</div>
        <div class="error">Entity ${esc(this._config?.entity || "")} was not found.</div>
      </div></ha-card>`;
  }

  _render() {
    const hass = this._hass;
    const attrs = hass.states[this._config.entity]?.attributes || {};
    const state = hass.states[this._config.entity]?.state;
    if (state === "unavailable") {
      this.shadowRoot.innerHTML = `
        <style>${this._styles()}</style>
        <ha-card><div class="card-content">
          <div class="title">${esc(this._config.title)}</div>
          <div class="error">The integration is unavailable. Check the hOn integration.</div>
        </div></ha-card>`;
      return;
    }

    const entities = attrs.entities || {};
    const programs = asArray(attrs.programs);
    const schema = attrs.parameter_schema || {};
    const parameterEntities = attrs.parameter_entities || {};
    const summary = attrs.summary || {};
    const favoriteNames = asArray(attrs.favorite_names);
    const selectedFavorite = attrs.selected_favorite || "None";
    const currentLabel = attrs.program_label || state || "";
    const currentCategory = CATEGORY_LABELS[attrs.program_category] || "";
    if (this._favoriteName === undefined) {
      this._favoriteName = attrs.favorite_name || "";
    }

    const status = this._status();
    const error = this._error
      ? `<div class="error">${esc(this._error)}</div>`
      : "";
    const currentMeta = [attrs.model, attrs.catalog_count ? `${attrs.catalog_count} programs` : "", currentCategory]
      .filter(Boolean)
      .join(" · ");

    this.shadowRoot.innerHTML = `
      <style>${this._styles()}</style>
      <ha-card>
        <div class="card-content">
          <div class="header">
            <div>
              <div class="title">${esc(this._config.title)}</div>
              <div class="subtitle">${esc(currentMeta)}</div>
            </div>
            ${status.html}
          </div>
          ${error}

          <div class="section program-section">
            <div class="row-label">
              <span>Program</span>
              <span class="current">${esc(currentLabel)}</span>
            </div>
            <input class="search" id="search" type="search" placeholder="Search ${esc(attrs.catalog_count || programs.length)} programs…" value="${esc(this._search)}" autocomplete="off">
            <select class="program-select" id="program">${this._programOptions(programs, currentLabel)}</select>
            <div class="hint">Search by name, key or category. The program list is ordered by category.</div>
          </div>

          <div class="section">
            <div class="section-title">Settings</div>
            ${this._parameterControls(schema, parameterEntities, hass)}
          </div>

          <div class="summary">
            <div class="summary-main">${esc(this._summaryText(attrs))}</div>
            ${this._optionChips(summary)}
          </div>

          <div class="actions">
            <button class="btn primary" id="start" ${status.blocked ? "disabled" : ""}>${esc(status.button_label || "Start cycle")}</button>
            <button class="btn" id="stop" ${status.active ? "" : "disabled"}>Stop</button>
          </div>

          <div class="section">
            <div class="section-title">Favorites</div>
            <div class="favorite-row">
              <select id="favorite">${this._favoriteOptions(favoriteNames, selectedFavorite)}</select>
              <button class="btn small" id="start-favorite" ${selectedFavorite === "None" ? "disabled" : ""}>Start</button>
              <button class="btn small danger" id="delete-favorite" ${selectedFavorite === "None" ? "disabled" : ""}>Delete</button>
            </div>
            <div class="favorite-row save-row">
              <input id="favorite-name" type="text" maxlength="40" placeholder="Name this setup…" value="${esc(this._favoriteName)}">
              <button class="btn small" id="save-favorite" ${String(this._favoriteName || "").trim() ? "" : "disabled"}>Save current</button>
            </div>
            <div class="hint">Saving stores the program and every current setting. Selecting a favorite loads it; Start favorite starts it.</div>
          </div>
        </div>
      </ha-card>`;

    this._bind(attrs, entities);
  }

  _bind(attrs, entities) {
    const root = this.shadowRoot;
    const hass = this._hass;
    const search = root.getElementById("search");
    const program = root.getElementById("program");
    const start = root.getElementById("start");
    const stop = root.getElementById("stop");
    const favorite = root.getElementById("favorite");
    const startFavorite = root.getElementById("start-favorite");
    const deleteFavorite = root.getElementById("delete-favorite");
    const favoriteName = root.getElementById("favorite-name");
    const saveFavorite = root.getElementById("save-favorite");

    search?.addEventListener("input", (event) => {
      this._search = event.target.value;
      if (program) {
        const current = attrs.program_label || hass.states[this._config.entity]?.state || "";
        program.innerHTML = this._programOptions(asArray(attrs.programs), current);
        const matching = asArray(attrs.programs).filter((item) =>
          this._matches(item, this._search)
        );
        const currentMatch = matching.find(
          (item) => item.label === current
        );
        if (currentMatch) {
          program.value = currentMatch.label;
        }
      }
    });

    program?.addEventListener("change", () => {
      if (!program.value || !entities.program) return;
      this._call("select", "select_option", {
        entity_id: entities.program,
        option: program.value,
      });
    });

    root.querySelectorAll("[data-param-select]").forEach((element) => {
      element.addEventListener("change", () => {
        const entityId = element.dataset.entity;
        if (!entityId) return;
        this._call("select", "select_option", {
          entity_id: entityId,
          option: element.value,
        });
      });
    });

    root.querySelectorAll("[data-param-range]").forEach((element) => {
      const valueElement = root.getElementById(`value-${element.dataset.param}`);
      element.addEventListener("input", () => {
        if (valueElement) {
          valueElement.textContent = this._rangeLabel(
            element.value,
            element.dataset.unit
          );
        }
      });
      element.addEventListener("change", () => {
        const entityId = element.dataset.entity;
        if (!entityId) return;
        this._call("number", "set_value", {
          entity_id: entityId,
          value: Number(element.value),
        });
      });
    });

    root.querySelectorAll("[data-param-switch]").forEach((element) => {
      element.addEventListener("change", () => {
        const entityId = element.dataset.entity;
        if (!entityId) return;
        this._call("switch", element.checked ? "turn_on" : "turn_off", {
          entity_id: entityId,
        });
      });
    });

    start?.addEventListener("click", () => {
      if (!entities.start) return;
      if (!window.confirm(`Start ${this._summaryText(attrs)}?`)) return;
      this._call("button", "press", { entity_id: entities.start });
    });

    stop?.addEventListener("click", () => {
      if (!entities.stop) return;
      if (!window.confirm("Stop the current cycle?")) return;
      this._call("button", "press", { entity_id: entities.stop });
    });

    favorite?.addEventListener("change", () => {
      if (!entities.favorite) return;
      this._call("select", "select_option", {
        entity_id: entities.favorite,
        option: favorite.value,
      });
    });

    startFavorite?.addEventListener("click", () => {
      if (!entities.start_favorite) return;
      const name = favorite?.value || attrs.selected_favorite;
      if (!name || name === "None") return;
      if (!window.confirm(`Start favorite “${name}”?`)) return;
      this._call("button", "press", { entity_id: entities.start_favorite });
    });

    deleteFavorite?.addEventListener("click", () => {
      if (!entities.delete_favorite) return;
      const name = favorite?.value || attrs.selected_favorite;
      if (!name || name === "None") return;
      if (!window.confirm(`Delete favorite “${name}”?`)) return;
      this._call("button", "press", { entity_id: entities.delete_favorite });
    });

    favoriteName?.addEventListener("input", () => {
      this._favoriteName = favoriteName.value;
      if (saveFavorite) saveFavorite.disabled = !favoriteName.value.trim();
    });

    favoriteName?.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        saveFavorite?.click();
      }
    });

    saveFavorite?.addEventListener("click", () => {
      const name = (favoriteName?.value || "").trim();
      if (!name) {
        favoriteName?.focus();
        return;
      }
      this._call("washing_machine_assistant", "save_favorite", {
        name,
        device_id: attrs.device_id,
      }).then(() => {
        if (this._error) return;
        this._favoriteName = "";
        if (favoriteName) favoriteName.value = "";
        if (saveFavorite) saveFavorite.disabled = true;
      });
    });
  }

  _call(domain, service, data) {
    this._error = "";
    return this._hass
      .callService(domain, service, data)
      .catch((err) => {
        this._error = err?.message || String(err);
        this._lastStamp = undefined;
        this._render();
      });
  }

  _status() {
    const modeState = this._hass.states[this._config.mode_entity];
    const remaining = this._hass.states[this._config.remaining_entity];
    const remainingValue = Number(remaining?.state);
    const remainingText =
      Number.isFinite(remainingValue) && remainingValue > 0
        ? ` · ${Math.round(remainingValue)} min left`
        : "";

    if (
      modeState &&
      modeState.state !== "unavailable" &&
      modeState.state !== "unknown"
    ) {
      const mode = String(modeState.state);
      const label = MODE_LABELS[mode] || `Mode ${mode}`;
      const active = ACTIVE_MODES.has(mode);
      const blocked = active || mode === "0";
      let buttonLabel = "Start cycle";
      if (mode === "2") buttonLabel = "Running…";
      else if (mode === "3") buttonLabel = "Paused";
      else if (mode === "4" || mode === "5") buttonLabel = "Scheduled";
      else if (mode === "9") buttonLabel = "Ending…";
      else if (mode === "0") buttonLabel = "Disconnected";
      const tone = mode === "6" ? "error" : active ? "on" : "";
      const showRemaining = ["2", "3"].includes(mode);
      return {
        active,
        blocked,
        button_label: buttonLabel,
        html: `<div class="status ${tone}"><span class="status-dot"></span>${esc(label)}${showRemaining ? esc(remainingText) : ""}</div>`,
      };
    }

    // The mode sensor is normally present. If it is not, fall back to the
    // hOn on/off status without calling it "Running": onOffStatus is true
    // while the appliance is merely powered/ready.
    const fallback = this._hass.states[this._config.status_entity];
    if (!fallback) {
      return { active: false, blocked: false, button_label: "Start cycle", html: "" };
    }
    const label = fallback.state === "on" ? "On" : fallback.state === "off" ? "Off" : fallback.state;
    return {
      active: false,
      blocked: false,
      button_label: "Start cycle",
      html: `<div class="status"><span class="status-dot"></span>${esc(label)}</div>`,
    };
  }

  _programOptions(programs, currentLabel) {
    const query = this._search.trim().toLowerCase();
    const filtered = programs.filter((item) => this._matches(item, query));
    const groups = new Map();
    for (const item of filtered) {
      const category = item.category || "everyday";
      if (!groups.has(category)) groups.set(category, []);
      groups.get(category).push(item);
    }
    let html = `<option value="" disabled ${currentLabel ? "" : "selected"}>Select a program…</option>`;
    const currentInFiltered = filtered.some((item) => item.label === currentLabel);
    if (currentLabel && !currentInFiltered) {
      html += `<optgroup label="Current"><option value="${esc(currentLabel)}" selected>${esc(currentLabel)}</option></optgroup>`;
    }
    for (const category of CATEGORY_ORDER) {
      const items = groups.get(category);
      if (!items || !items.length) continue;
      html += `<optgroup label="${esc(CATEGORY_LABELS[category] || category)}">`;
      for (const item of items) {
        html += `<option value="${esc(item.label)}" ${item.label === currentLabel ? "selected" : ""}>${esc(item.label)}</option>`;
      }
      html += "</optgroup>";
    }
    if (!filtered.length && !currentLabel) {
      html += `<option value="" disabled>No programs match</option>`;
    }
    return html;
  }

  _matches(item, query) {
    if (!query) return true;
    return [item.label, item.name, item.key, item.category_label]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(query));
  }

  _favoriteOptions(names, selected) {
    let html = `<option value="None" ${selected === "None" ? "selected" : ""}>None</option>`;
    for (const name of names) {
      html += `<option value="${esc(name)}" ${name === selected ? "selected" : ""}>${esc(name)}</option>`;
    }
    return html;
  }

  _parameterControls(schema, entities, hass) {
    const entries = Object.entries(schema);
    if (!entries.length) {
      return `<div class="hint">This program has no adjustable parameters.</div>`;
    }
    const controls = [];
    for (const [key, spec] of entries) {
      const entityId = entities[key];
      if (!entityId) continue;
      const stateObj = hass.states[entityId];
      if (!stateObj || stateObj.state === "unavailable" || stateObj.state === "unknown") {
        continue;
      }
      const title = esc(spec.title || key);
      const icon = esc(spec.icon || "mdi:tune");
      let control = "";
      if (spec.type === "enum") {
        const options = asArray(spec.options)
          .map(
            (option) =>
              `<option value="${esc(option.label)}" ${String(option.label) === String(stateObj.state) ? "selected" : ""}>${esc(option.label)}</option>`
          )
          .join("");
        control = `<select data-param-select data-entity="${esc(entityId)}">${options}</select>`;
      } else if (spec.type === "range") {
        const value = Number(stateObj.state);
        const unit = spec.unit ? ` ${spec.unit}` : "";
        control = `
          <div class="range-line">
            <input type="range" data-param-range data-param="${esc(key)}" data-entity="${esc(entityId)}" data-unit="${esc(unit)}" min="${esc(spec.min)}" max="${esc(spec.max)}" step="${esc(spec.step)}" value="${Number.isFinite(value) ? value : spec.min}">
            <span class="range-value" id="value-${esc(key)}">${esc(this._rangeLabel(value, unit))}</span>
          </div>`;
      } else if (spec.type === "bool") {
        control = `
          <label class="switch">
            <input type="checkbox" data-param-switch data-entity="${esc(entityId)}" ${stateObj.state === "on" ? "checked" : ""}>
            <span class="switch-track"></span>
          </label>`;
      }
      if (!control) continue;
      controls.push(`
        <div class="param">
          <div class="param-head"><ha-icon icon="${icon}"></ha-icon><span>${title}</span></div>
          <div class="param-control">${control}</div>
        </div>`);
    }
    if (!controls.length) {
      return `<div class="hint">No adjustable settings are available for this program right now.</div>`;
    }
    return `<div class="param-grid">${controls.join("")}</div>`;
  }

  _rangeLabel(value, unit) {
    const number = Number(value);
    const text = Number.isFinite(number) ? String(Math.round(number * 10) / 10) : String(value);
    return `${text}${unit || ""}`;
  }

  _summaryText(attrs) {
    const summary = attrs.summary || {};
    const parts = [];
    if (summary.temp) parts.push(summary.temp);
    if (summary.spinSpeed) parts.push(summary.spinSpeed);
    if (summary.delayTime && !String(summary.delayTime).startsWith("0")) {
      parts.push(`Delay ${summary.delayTime}`);
    }
    const base = `${summary.program || attrs.program_label || "program"}${parts.length ? ` · ${parts.join(" · ")}` : ""}`;
    const options = asArray(summary.options);
    return options.length ? `${base} with ${options.join(", ")}` : base;
  }

  _optionChips(summary) {
    const options = asArray(summary?.options);
    if (!options.length) return "";
    return `<div class="chips">${options
      .map((option) => `<span class="chip">${esc(option)}</span>`)
      .join("")}</div>`;
  }

  _styles() {
    return `
      :host { display: block; }
      ha-card { overflow: hidden; }
      .card-content { padding: 16px; }
      .header { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
      .title { font-size: 1.1rem; font-weight: 600; color: var(--primary-text-color); }
      .subtitle { margin-top: 2px; font-size: .78rem; color: var(--secondary-text-color); }
      .status { display: inline-flex; align-items: center; gap: 6px; padding: 4px 9px; border-radius: 999px; background: var(--secondary-background-color); color: var(--secondary-text-color); font-size: .75rem; white-space: nowrap; }
      .status.on { color: var(--primary-color); }
      .status.error { color: var(--error-color, #b00020); }
      .status-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--disabled-text-color, #9e9e9e); }
      .status.on .status-dot { background: var(--primary-color); box-shadow: 0 0 0 3px color-mix(in srgb, var(--primary-color) 18%, transparent); }
      .status.error .status-dot { background: var(--error-color, #b00020); box-shadow: none; }
      .error { margin-top: 10px; padding: 8px 10px; border-radius: 8px; background: color-mix(in srgb, var(--error-color, #b00020) 12%, transparent); color: var(--error-color, #b00020); font-size: .8rem; }
      .section { margin-top: 16px; }
      .section.program-section { margin-top: 14px; }
      .section-title { margin-bottom: 8px; font-size: .72rem; font-weight: 600; letter-spacing: .04em; text-transform: uppercase; color: var(--secondary-text-color); }
      .row-label { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; margin-bottom: 7px; font-size: .78rem; color: var(--secondary-text-color); }
      .row-label .current { color: var(--primary-text-color); font-weight: 600; text-align: right; }
      .search, .program-select, .favorite-row select, .favorite-row input {
        width: 100%; box-sizing: border-box; padding: 9px 10px; border: 1px solid var(--divider-color); border-radius: 8px; background: var(--card-background-color); color: var(--primary-text-color); font: inherit; font-size: .85rem;
      }
      .search { margin-bottom: 7px; }
      .search:focus, .program-select:focus, .favorite-row select:focus, .favorite-row input:focus { outline: 2px solid var(--primary-color); outline-offset: -1px; }
      .hint { margin-top: 6px; font-size: .72rem; line-height: 1.35; color: var(--secondary-text-color); }
      .param-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(145px, 1fr)); gap: 8px; }
      .param { border: 1px solid var(--divider-color); border-radius: 10px; padding: 9px; min-width: 0; }
      .param-head { display: flex; align-items: center; gap: 5px; margin-bottom: 7px; min-width: 0; color: var(--secondary-text-color); font-size: .76rem; }
      .param-head span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .param-head ha-icon { --mdc-icon-size: 15px; flex: none; }
      .param-control select { width: 100%; box-sizing: border-box; padding: 6px 7px; border: 1px solid var(--divider-color); border-radius: 7px; background: var(--card-background-color); color: var(--primary-text-color); font: inherit; font-size: .82rem; }
      .range-line { display: flex; align-items: center; gap: 7px; }
      input[type="range"] { flex: 1; min-width: 0; accent-color: var(--primary-color); }
      .range-value { flex: none; min-width: 3.2em; text-align: right; font-size: .76rem; color: var(--primary-text-color); font-variant-numeric: tabular-nums; }
      .switch { display: inline-flex; align-items: center; cursor: pointer; }
      .switch input { position: absolute; opacity: 0; width: 0; height: 0; }
      .switch-track { width: 38px; height: 22px; border-radius: 999px; background: var(--divider-color); position: relative; transition: background .15s ease; }
      .switch-track::after { content: ""; position: absolute; top: 3px; left: 3px; width: 16px; height: 16px; border-radius: 50%; background: var(--card-background-color); transition: transform .15s ease; }
      .switch input:checked + .switch-track { background: var(--primary-color); }
      .switch input:checked + .switch-track::after { transform: translateX(16px); }
      .summary { margin-top: 14px; }
      .summary-main { font-size: .9rem; font-weight: 500; color: var(--primary-text-color); line-height: 1.35; }
      .chips { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 7px; }
      .chip { padding: 3px 7px; border-radius: 999px; background: var(--secondary-background-color); color: var(--secondary-text-color); font-size: .7rem; }
      .actions { display: flex; gap: 8px; margin-top: 14px; }
      .btn { flex: 1; padding: 10px 12px; border: 1px solid var(--divider-color); border-radius: 8px; background: var(--card-background-color); color: var(--primary-text-color); font: inherit; font-size: .88rem; font-weight: 600; cursor: pointer; }
      .btn:hover { background: var(--secondary-background-color); }
      .btn.primary { border-color: var(--primary-color); background: var(--primary-color); color: var(--text-primary-color, #fff); }
      .btn.primary:hover { filter: brightness(1.03); }
      .btn.small { flex: 0 0 auto; padding: 8px 10px; font-size: .8rem; }
      .btn.danger { color: var(--error-color, #b00020); }
      .btn:disabled { opacity: .45; cursor: not-allowed; }
      .favorite-row { display: flex; flex-wrap: wrap; gap: 7px; align-items: center; }
      .favorite-row select, .favorite-row input { flex: 1 1 140px; width: auto; }
      .save-row { margin-top: 7px; }
      .save-row input { flex: 1 1 160px; }
      @media (max-width: 460px) {
        .card-content { padding: 13px; }
        .param-grid { grid-template-columns: 1fr 1fr; }
        .header { flex-direction: column; }
        .status { align-self: flex-start; }
      }
      @media (max-width: 340px) {
        .param-grid { grid-template-columns: 1fr; }
      }
    `;
  }
}

if (!customElements.get("washing-machine-card")) {
  customElements.define("washing-machine-card", WashingMachineCard);
}
window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "washing-machine-card")) {
  window.customCards.push({
    type: "washing-machine-card",
    name: "Washing Machine",
    description: "Program search, parameters and favorites for the washing machine assistant.",
    preview: true,
  });
}
