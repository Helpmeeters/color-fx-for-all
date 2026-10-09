const DOMAIN = "color_fx";
const MEDIA_ART = "Media Art";

const STYLE = `
  ha-card {
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .zone {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .zone + .zone {
    border-top: 1px solid var(--divider-color);
    padding-top: 12px;
  }
  .head {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .toggle {
    display: flex;
    align-items: center;
    gap: 10px;
    flex: 1;
    min-width: 0;
    padding: 0;
    border: none;
    background: none;
    color: inherit;
    font: inherit;
    text-align: left;
    cursor: pointer;
  }
  .icon {
    flex: none;
    width: 36px;
    height: 36px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    --mdc-icon-size: 20px;
    color: var(--disabled-text-color, #9e9e9e);
    background: rgba(158, 158, 158, 0.2);
    transition: color 0.3s, background 0.3s;
  }
  .on .icon {
    color: var(--indigo-color, #3f51b5);
    background: rgba(63, 81, 181, 0.2);
  }
  .text {
    min-width: 0;
  }
  .name,
  .state {
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
  }
  .name {
    font-size: 14px;
    font-weight: 600;
    color: var(--primary-text-color);
  }
  .state {
    font-size: 12px;
    color: var(--secondary-text-color);
  }
  .picker {
    position: relative;
    flex: none;
    max-width: 50%;
  }
  select {
    width: 100%;
    appearance: none;
    -webkit-appearance: none;
    padding: 8px 30px 8px 12px;
    border: none;
    border-radius: 18px;
    font: inherit;
    font-size: 13px;
    color: var(--primary-text-color);
    background: var(--secondary-background-color, rgba(127, 127, 127, 0.15));
    cursor: pointer;
    text-overflow: ellipsis;
  }
  .picker ha-icon {
    position: absolute;
    right: 8px;
    top: 50%;
    transform: translateY(-50%);
    --mdc-icon-size: 18px;
    color: var(--secondary-text-color);
    pointer-events: none;
  }
  .palette {
    display: flex;
    gap: 3px;
    height: 14px;
    transition: opacity 0.3s;
  }
  .palette span {
    flex: 1;
    border-radius: 4px;
    box-shadow: inset 0 0 0 1px rgba(127, 127, 127, 0.25);
    transition: background-color 0.6s;
  }
  .off .palette {
    opacity: 0.5;
  }
  .empty {
    font-size: 12px;
    color: var(--secondary-text-color);
  }
`;

function hubName(hass, entityId) {
  const name = hass.states[entityId]?.attributes.friendly_name || entityId;
  return name.replace(/\s*Color FX$/i, "") || name;
}

function findHubs(hass) {
  const ids = hass.entities
    ? Object.values(hass.entities)
        .filter((e) => e.platform === DOMAIN && !e.hidden && e.entity_id.startsWith("switch."))
        .map((e) => e.entity_id)
    : Object.keys(hass.states).filter((id) => id.startsWith("switch.color_fx_"));
  return ids
    .filter((id) => hass.states[id])
    .sort((a, b) => hubName(hass, a).localeCompare(hubName(hass, b)));
}

class ColorFxCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._rows = new Map();
    this._states = new Map();
  }

  static getStubConfig(hass) {
    const [entity] = hass ? findHubs(hass) : [];
    return entity ? { entity } : {};
  }

  static getConfigElement() {
    return document.createElement("color-fx-card-editor");
  }

  setConfig(config) {
    this._config = config || {};
    this._rows.clear();
    this._states.clear();
    this._card = null;
  }

  getCardSize() {
    return Math.max(1, this._zones().length * 2);
  }

  getGridOptions() {
    return { columns: 12 };
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _zones() {
    const hass = this._hass;
    if (!hass) return [];
    if (this._config.entity) return hass.states[this._config.entity] ? [this._config.entity] : [];
    if (this._config.entities) {
      return this._config.entities.filter((id) => hass.states[id]);
    }
    return findHubs(hass);
  }

  _name(entityId) {
    if (this._config.name && entityId === this._config.entity) return this._config.name;
    return hubName(this._hass, entityId);
  }

  _render() {
    if (!this._card) {
      this.shadowRoot.innerHTML = `<style>${STYLE}</style><ha-card></ha-card>`;
      this._card = this.shadowRoot.querySelector("ha-card");
    }

    const zones = this._zones();
    if (!zones.length) {
      this._rows.clear();
      this._states.clear();
      const message = this._config.entity
        ? `Color FX hub ${this._config.entity} not found.`
        : "No Color FX hubs found.";
      this._card.innerHTML = `<div class="empty"></div>`;
      this._card.firstChild.textContent = message;
      return;
    }
    if (!this._rows.size) this._card.innerHTML = "";

    for (const [id, row] of this._rows) {
      if (!zones.includes(id)) {
        row.el.remove();
        this._rows.delete(id);
        this._states.delete(id);
      }
    }
    zones.forEach((id) => {
      const row = this._rows.get(id) || this._createRow(id);
      this._card.appendChild(row.el);
      const state = this._hass.states[id];
      if (this._states.get(id) !== state) {
        this._states.set(id, state);
        this._updateRow(row, state);
      }
    });
  }

  _createRow(entityId) {
    const el = document.createElement("div");
    el.className = "zone";
    el.innerHTML = `
      <div class="head">
        <button class="toggle" type="button">
          <div class="icon"><ha-icon icon="mdi:shimmer"></ha-icon></div>
          <div class="text">
            <div class="name"></div>
            <div class="state"></div>
          </div>
        </button>
        <div class="picker">
          <select aria-label="Sequence"></select>
          <ha-icon icon="mdi:chevron-down"></ha-icon>
        </div>
      </div>
      <div class="palette"></div>
    `;
    const row = {
      el,
      name: el.querySelector(".name"),
      state: el.querySelector(".state"),
      select: el.querySelector("select"),
      palette: el.querySelector(".palette"),
      options: "",
      colors: "",
    };
    el.querySelector(".toggle").addEventListener("click", () => {
      this._hass.callService("switch", "toggle", { entity_id: entityId });
    });
    row.select.addEventListener("change", () => {
      this._hass.callService(DOMAIN, "set_sequence", {
        entity_id: entityId,
        sequence: row.select.value,
      });
    });
    this._rows.set(entityId, row);
    return row;
  }

  _updateRow(row, state) {
    const attrs = state.attributes;
    const on = state.state === "on";
    const sequence = attrs.current_sequence;

    row.el.classList.toggle("on", on);
    row.el.classList.toggle("off", !on);
    row.name.textContent = this._name(state.entity_id);
    row.state.textContent = this._describe(on, sequence, attrs.palette_source);

    const sequences = attrs.available_sequences || [];
    const options = sequences.join("\n");
    if (options !== row.options) {
      row.options = options;
      row.select.replaceChildren(
        ...sequences.map((name) => {
          const opt = document.createElement("option");
          opt.value = opt.textContent = name;
          return opt;
        })
      );
    }
    if (row.select.value !== sequence) row.select.value = sequence;

    const palette = attrs.palette || [];
    const colors = palette.length ? palette.join(",") : `empty:${sequence}`;
    if (colors !== row.colors) {
      row.colors = colors;
      if (palette.length) {
        row.palette.replaceChildren(
          ...palette.map((color) => {
            const swatch = document.createElement("span");
            swatch.style.backgroundColor = color;
            swatch.title = color;
            return swatch;
          })
        );
      } else {
        const note = document.createElement("div");
        note.className = "empty";
        note.textContent =
          sequence === MEDIA_ART ? "Waiting for something playing with artwork\u2026" : "No colors";
        row.palette.replaceChildren(note);
      }
    }
  }

  _describe(on, sequence, source) {
    const status = on ? "On" : "Off";
    if (sequence !== MEDIA_ART || !source) return status;
    const player = this._hass.states[source];
    return `${status} \u00b7 ${player?.attributes.friendly_name || source}`;
  }
}

const EDITOR_SCHEMA = [
  {
    name: "entity",
    selector: { entity: { filter: { integration: DOMAIN, domain: "switch" } } },
  },
  { name: "name", selector: { text: {} } },
];

const EDITOR_LABELS = {
  entity: "Hub (leave empty to show every hub)",
  name: "Name",
};

class ColorFxCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.schema = EDITOR_SCHEMA;
      this._form.computeLabel = (field) => EDITOR_LABELS[field.name];
      this._form.addEventListener("value-changed", (ev) => {
        const config = { ...this._config, ...ev.detail.value };
        for (const key of ["entity", "name"]) if (!config[key]) delete config[key];
        this.dispatchEvent(
          new CustomEvent("config-changed", { detail: { config }, bubbles: true, composed: true })
        );
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.data = this._config;
  }
}

if (!customElements.get("color-fx-card")) {
  customElements.define("color-fx-card", ColorFxCard);
  customElements.define("color-fx-card-editor", ColorFxCardEditor);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "color-fx-card",
    name: "Color FX",
    description: "Toggle a Color FX hub, pick its sequence, and see the live palette.",
    preview: true,
  });
}
