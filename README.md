# Washing Machine Assistant

A companion integration for the [hOn (Haier/Candy/Hoover) integration](https://github.com/gvigroux/hon) that adds what the hOn washing-machine entities do not expose:

- choose any of the appliance's programs;
- set the parameters that the chosen program supports;
- start and stop a cycle;
- save complete program + settings combinations as favorites;
- drive it all from a custom Lovelace card with a searchable program picker.

It does **not** replace or patch hOn. It calls the public `hon.start_program` service and keeps its own draft/favorites state.

## Requirements

- Home Assistant 2026.10 or newer.
- hOn integration **0.8.4** installed through HACS and the washing machine added there.
- This version's catalog is built for the Candy `RP4476BWMUC8/1-S` (`WM`). The config flow refuses other models instead of guessing their parameters.

## Installation (HACS, recommended)

1. In HACS, open **Integrations → ⋮ → Custom repositories**.
2. Add `https://github.com/ferensz/ha-washing-machine-assistant` with category **Integration**.
3. Search for **Washing Machine Assistant** and install it.
4. Restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration**, search for **Washing Machine Assistant**, and select the hOn washing machine.
6. Add the card resource:
   **Settings → Dashboards → Resources → Add resource**
   - URL: `/washing_machine_assistant/washing-machine-card.js`
   - Resource type: **JavaScript module**
7. Add the card to a dashboard:

   ```yaml
   type: custom:washing-machine-card
   entity: sensor.washing_machine_controls
   title: Washing machine
   mode_entity: sensor.washing_machine_mode
   remote_control_entity: binary_sensor.washing_machine_remote_control
   remaining_entity: sensor.washing_machine_remaining_time
   ```

   `mode_entity`, `remote_control_entity` and `remaining_entity` are optional; the values above are the defaults. The card uses hOn's `machMode` (Ready/Running/Paused/Scheduled/Finished/Error) rather than the on/off status sensor, which is also on while the appliance is merely powered or ready. It shows the remote-control state separately and disables Start/Stop while remote control is off.

## Manual installation (zip)

1. Extract the zip so that this folder exists:

   ```
   /config/custom_components/washing_machine_assistant/
   ```

2. Restart Home Assistant.

3. Follow steps 5–7 above to add the integration and the card.

## How it works

- The 143-program catalog in `catalog.json` was generated from the appliance's **Get programs details** notifications. It contains each program's display name, category, and parameter defaults/options.
- Selecting a program loads that program's defaults. Values that also exist on the new program and are still valid are kept.
- **Start cycle** validates the draft and calls the hOn service:

  ```yaml
  service: hon.start_program
  data:
    program: iot_wash_cotton
    parameters: "{'delayTime': '0', 'lang': '1', ...}"
  ```

  The integration builds that call; you do not have to handle the parameter string yourself.

- **Stop** calls `hon.turn_off` for the same device.
- Favorites are stored through Home Assistant's `Store` helper in `.storage/washing_machine_assistant.<hOn device id>`, so they are included in normal Home Assistant backups.
- The catalog is intentionally separate from hOn. Updating hOn does not overwrite this integration, and updating this integration does not touch hOn.

## Entities

The entity IDs are stable and explicit:

| Entity | Purpose |
| --- | --- |
| `select.washing_machine_program` | Program picker (all 143 programs) |
| `select.washing_machine_favorite` | Load a saved favorite into the draft |
| `select.washing_machine_temperature` | Temperature, when the program supports it |
| `select.washing_machine_spin_speed` | Spin speed, when supported |
| `number.washing_machine_delay_time` | Delay start, minutes |
| `number.washing_machine_soiling_level` | Soiling level 1–3, when supported |
| `number.washing_machine_steam_level` | Steam level 1–3, when supported |
| `switch.washing_machine_prewash` | Prewash |
| `switch.washing_machine_hygiene` | Hygiene |
| `switch.washing_machine_anti_crease` | Anti-crease |
| `switch.washing_machine_good_night` | Good night |
| `switch.washing_machine_extra_rinse_1/2/3` | Extra rinses |
| `switch.washing_machine_aqua_plus` | Aqua plus |
| `text.washing_machine_favorite_name` | Name used by the **Save favorite** button |
| `button.washing_machine_start` | Start the current draft |
| `button.washing_machine_stop` | Stop the cycle |
| `button.washing_machine_start_favorite` | Start the selected favorite |
| `button.washing_machine_save_favorite` | Save the current draft under the favorite-name value |
| `button.washing_machine_delete_favorite` | Delete the selected favorite |
| `sensor.washing_machine_controls` | Card/dashboard snapshot |

Parameter entities that do not belong to the selected program become unavailable rather than showing meaningless controls.

## Services

All services accept an optional `device_id` (the hOn washing-machine device). When only one washing machine is configured, it can be omitted.

### `washing_machine_assistant.start`

Start the draft, or supply a program/parameters directly.

```yaml
service: washing_machine_assistant.start
data:
  program: iot_wash_cotton
  parameters:
    temp: "40"
    spinSpeed: "1400"
    delayTime: 0
```

Validate the exact payload without starting anything:

```yaml
service: washing_machine_assistant.start
data:
  program: iot_wash_cotton
  parameters:
    temp: "40"
  dry_run: true
```

`dry_run` returns the program key, parameters and a readable summary; it does not call hOn.

### `washing_machine_assistant.stop`

```yaml
service: washing_machine_assistant.stop
```

### Favorites

```yaml
service: washing_machine_assistant.save_favorite
data:
  name: Cotton 40
```

```yaml
service: washing_machine_assistant.load_favorite
data:
  name: Cotton 40
```

```yaml
service: washing_machine_assistant.start_favorite
data:
  name: Cotton 40
```

```yaml
service: washing_machine_assistant.delete_favorite
data:
  name: Cotton 40
```

Saving a name that already exists (case-insensitive) overwrites it. Favorite names are limited to 40 characters and `None` is reserved.

## Card behavior

- **Program search** filters by program name, key or category. The picker shows all 143 programs grouped as Everyday, Special care, Stains, Branded, Steam and Extras.
- **Settings** are generated from the selected program's schema; unavailable controls are hidden.
- **Start cycle** asks for confirmation with a summary such as `Cotton · 40 °C · 1400 rpm`.
- **Favorites** can be loaded, started, deleted, or created from the current draft.
- The card reads `sensor.washing_machine_controls`; if that entity is renamed, update `entity` in the card config.

## Safety notes

- Starting is a real appliance command. The card asks for confirmation, but the `start` service does not.
- hOn's remote-control permission must be enabled on the appliance. If it is off, the service call fails and Home Assistant shows the error.
- Do not run a test start with laundry in the drum unless you intend to wash it. Use `dry_run` to verify the payload first.
- The integration does not check door state, load weight or remote-control permission itself; hOn remains the authority.

## Updating the catalog

The bundled catalog is generated from the appliance's program dump. If a firmware update adds or removes programs, regenerate it:

1. In Home Assistant, open the washing machine device and press **Get programs details** (this creates one persistent notification per program).
2. Read the notifications through `ha-mcp`'s `ha_get_overview` (or your preferred export) and save the JSON.
3. Run:

   ```bash
   python tools/build_catalog.py notifications.json \
     custom_components/washing_machine_assistant/catalog.json
   ```

4. Copy the updated `catalog.json` to `/config/custom_components/washing_machine_assistant/catalog.json` and restart Home Assistant.

The `catalog.json` in this repository was built from 143 programs and includes program defaults, valid enum values, ranges and the hidden `lang` default.

## Troubleshooting

**The integration does not appear in Add integration.**
Check that `/config/custom_components/washing_machine_assistant/manifest.json` exists, then restart Home Assistant and check **Settings → System → Logs** for `washing_machine_assistant`.

**The config flow says the model is unsupported.**
The bundled catalog only covers Candy `RP4476BWMUC8/1-S`. Add a catalog for the new model or ask for a new catalog to be generated.

**The card says "Entity … was not found".**
Add the integration, then confirm `sensor.washing_machine_controls` exists. If you renamed it, update `entity` in the card config.

**The card is blank or the resource does not load.**
Confirm the Lovelace resource URL is exactly `/washing_machine_assistant/washing-machine-card.js` and its type is **JavaScript module**. A hard refresh of the browser may be needed after replacing the file.

**Start fails.**
Check the hOn logs and confirm the appliance has remote control enabled. Try `dry_run: true` first to verify the integration's payload.

**A favorite is missing after a catalog update.**
Favorites whose program is no longer in the catalog are ignored at startup. The rest remain.

## Development

The integration is pure Python; the card is a single vanilla JavaScript file with no build step.

```bash
python -m compileall custom_components/washing_machine_assistant
python -m unittest discover -s tests -v
```

The tests validate the catalog (143 programs, parameter types/defaults, categories) and the pure parameter helper functions.

## License

MIT. See [LICENSE](LICENSE).
