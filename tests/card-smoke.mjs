/**
 * Minimal DOM-free smoke test for the card render path.
 * Run with: node tests/card-smoke.mjs
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";

class FakeElement {
  constructor() {
    this.dataset = {};
    this.value = "";
    this.checked = false;
    this.disabled = false;
    this.innerHTML = "";
  }
  addEventListener() {}
  focus() {}
}

class FakeShadowRoot {
  constructor() {
    this._html = "";
  }
  set innerHTML(value) {
    this._html = value;
  }
  get innerHTML() {
    return this._html;
  }
  getElementById() {
    return new FakeElement();
  }
  querySelectorAll() {
    return [];
  }
}

class FakeHTMLElement {
  constructor() {
    this.shadowRoot = new FakeShadowRoot();
  }
  attachShadow() {
    return this.shadowRoot;
  }
}

let CardClass;

globalThis.HTMLElement = FakeHTMLElement;
globalThis.window = { customCards: [] };
globalThis.customElements = {
  get() {
    return undefined;
  },
  define(_name, klass) {
    CardClass = klass;
  },
};

const source = readFileSync(
  new URL(
    "../custom_components/washing_machine_assistant/www/washing-machine-card.js",
    import.meta.url
  ),
  "utf8"
);
vm.runInThisContext(source, { filename: "washing-machine-card.js" });
assert.ok(CardClass, "card class was registered");

const card = new CardClass();
card.setConfig({ entity: "sensor.washing_machine_controls" });

const parameterEntities = {
  temp: "select.washing_machine_temperature",
  delayTime: "number.washing_machine_delay_time",
  prewash: "switch.washing_machine_prewash",
};
const attributes = {
  program_key: "iot_wash_cotton",
  program_name: "Cotton",
  program_label: "Cotton",
  program_category: "everyday",
  catalog_count: 143,
  model: "RP4476BWMUC8/1-S",
  programs: [
    {
      key: "iot_wash_cotton",
      name: "Cotton",
      label: "Cotton",
      category: "everyday",
      category_label: "Everyday",
    },
    {
      key: "rapid_14_min",
      name: "Rapid 14 min",
      label: "Rapid 14 min",
      category: "everyday",
      category_label: "Everyday",
    },
  ],
  parameter_schema: {
    temp: {
      type: "enum",
      title: "Temperature",
      icon: "mdi:thermometer",
      options: [
        { value: "40", label: "40 °C" },
        { value: "60", label: "60 °C" },
      ],
      default: "60",
    },
    delayTime: {
      type: "range",
      title: "Delay time",
      icon: "mdi:timer-plus",
      min: 0,
      max: 120,
      step: 30,
      unit: "min",
      default: "0",
    },
    prewash: { type: "bool", title: "Prewash", icon: "mdi:water", default: "0" },
  },
  parameter_entities: parameterEntities,
  parameters: { temp: "60", delayTime: "0", prewash: "0" },
  summary: {
    program: "Cotton",
    temp: "60 °C",
    spinSpeed: "1400 rpm",
    delayTime: "0 min",
    options: [],
  },
  favorite_names: ["Cotton 40", "Quick"],
  favorite_options: ["None", "Cotton 40", "Quick"],
  selected_favorite: "None",
  favorite_name: "",
  entities: {
    program: "select.washing_machine_program",
    favorite: "select.washing_machine_favorite",
    favorite_name: "text.washing_machine_favorite_name",
    start: "button.washing_machine_start",
    stop: "button.washing_machine_stop",
    start_favorite: "button.washing_machine_start_favorite",
    save_favorite: "button.washing_machine_save_favorite",
    delete_favorite: "button.washing_machine_delete_favorite",
    controls: "sensor.washing_machine_controls",
  },
  device_id: "device",
};

const states = {
  "sensor.washing_machine_controls": {
    state: "Cotton",
    attributes,
    last_updated: "2026-10-26T12:00:00+00:00",
  },
  "binary_sensor.washing_machine_status": {
    state: "off",
    attributes: {},
    last_updated: "2026-10-26T12:00:00+00:00",
  },
  "sensor.washing_machine_mode": {
    state: "1",
    attributes: {},
    last_updated: "2026-10-26T12:00:00+00:00",
  },
  "binary_sensor.washing_machine_remote_control": {
    state: "on",
    attributes: {},
    last_updated: "2026-10-26T12:00:00+00:00",
  },
  "sensor.washing_machine_remaining_time": {
    state: "0",
    attributes: {},
    last_updated: "2026-10-26T12:00:00+00:00",
  },
  "select.washing_machine_temperature": {
    state: "60 °C",
    attributes: {},
    last_updated: "2026-10-26T12:00:00+00:00",
  },
  "number.washing_machine_delay_time": {
    state: "0",
    attributes: {},
    last_updated: "2026-10-26T12:00:00+00:00",
  },
  "switch.washing_machine_prewash": {
    state: "off",
    attributes: {},
    last_updated: "2026-10-26T12:00:00+00:00",
  },
};

card.hass = { states, callService: async () => undefined };
const html = card.shadowRoot.innerHTML;
assert.match(html, /Washing machine/);
assert.match(html, /Cotton/);
assert.match(html, /Start cycle/);
assert.match(html, /Favorites/);
assert.match(html, /Temperature/);
assert.match(html, /Delay time/);
assert.match(html, /Prewash/);
assert.match(html, /Rapid 14 min/);
assert.match(html, /Ready/);
assert.match(html, /Remote connected/);
assert.doesNotMatch(html, /Running/);
assert.match(html, /id="start" >Start cycle/);
assert.equal(card._summaryText(attributes), "Cotton · 60 °C · 1400 rpm");
assert.equal(card._rangeLabel(30, " min"), "30 min");

// Ready (machMode 1) must not be reported as running even when the
// on/off status sensor is on.
states["binary_sensor.washing_machine_status"].state = "on";
states["sensor.washing_machine_mode"].state = "1";
states["sensor.washing_machine_mode"].last_updated =
  "2026-10-26T12:00:01+00:00";
card.hass = { states, callService: async () => undefined };
assert.match(card.shadowRoot.innerHTML, /Ready/);
assert.match(card.shadowRoot.innerHTML, /Remote connected/);
assert.doesNotMatch(card.shadowRoot.innerHTML, /Running/);

// Remote control off blocks Start/Stop even when the mode is Ready.
states["binary_sensor.washing_machine_remote_control"].state = "off";
states["binary_sensor.washing_machine_remote_control"].last_updated =
  "2026-10-26T12:00:03+00:00";
card.hass = { states, callService: async () => undefined };
assert.match(card.shadowRoot.innerHTML, /Remote off/);
assert.match(card.shadowRoot.innerHTML, /Ready/);
assert.match(card.shadowRoot.innerHTML, /id="start" disabled>Remote off/);
assert.match(card.shadowRoot.innerHTML, /id="stop" disabled>Stop/);

// Restore remote control for the remaining mode checks.
states["binary_sensor.washing_machine_remote_control"].state = "on";
states["binary_sensor.washing_machine_remote_control"].last_updated =
  "2026-10-26T12:00:04+00:00";

// machMode 2 is running.
states["sensor.washing_machine_mode"].state = "2";
states["sensor.washing_machine_mode"].last_updated =
  "2026-10-26T12:00:02+00:00";
states["sensor.washing_machine_remaining_time"].state = "42";
card.hass = { states, callService: async () => undefined };
assert.match(card.shadowRoot.innerHTML, /Running/);
assert.match(card.shadowRoot.innerHTML, /42 min left/);
assert.match(card.shadowRoot.innerHTML, /id="start" disabled>Running/);

const modeCases = [
  { mode: "0", label: "Disconnected", startDisabled: true, stopDisabled: true },
  { mode: "3", label: "Paused", startDisabled: true, stopDisabled: false },
  { mode: "7", label: "Finished", startDisabled: false, stopDisabled: true },
];
for (const testCase of modeCases) {
  states["sensor.washing_machine_mode"].state = testCase.mode;
  states["sensor.washing_machine_mode"].last_updated =
    `2026-10-26T12:10:0${testCase.mode}+00:00`;
  card.hass = { states, callService: async () => undefined };
  const rendered = card.shadowRoot.innerHTML;
  assert.match(rendered, new RegExp(testCase.label));
  assert.equal(
    new RegExp('id="start" disabled').test(rendered),
    testCase.startDisabled,
    `start disabled for mode ${testCase.mode}`
  );
  assert.equal(
    new RegExp('id="stop" disabled').test(rendered),
    testCase.stopDisabled,
    `stop disabled for mode ${testCase.mode}`
  );
}

card._search = "rapid";
const options = card._programOptions(attributes.programs, "Cotton");
assert.match(options, /Rapid 14 min/);
assert.match(options, /Current/);

console.log("card smoke test: OK");
