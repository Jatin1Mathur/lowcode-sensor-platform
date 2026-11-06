# Oracle APEX application

The low-code side of the platform. It reads the tables filled by the Flask
service and gives users screens without hand-written frontend code.

## Setup

1. Run `schema.sql`, then `ords_module.sql`, in **SQL Workshop > SQL Scripts**.
2. Protect the module: **RESTful Services > Privileges**, create a privilege for
   the `sensor` module and an OAuth client (client credentials). Put the token in
   the Flask service's `APEX_ORDS_TOKEN`.
3. Create the app: **App Builder > Create > New Application** with the pages below.

## Pages

| Page | Type | Source |
|------|------|--------|
| Dashboard | Cards + Chart | Latest cycle per device, line chart of a chosen sensor over cycles from `sensor_reading_v` |
| Cycles | Interactive Report | `sensor_cycle` with drill-down link to page 3 |
| Cycle detail | Classic Report | `sensor_reading_v WHERE device_id = :P3_DEVICE_ID AND cycle_no = :P3_CYCLE_NO` |
| Sensors | Interactive Grid | `sensor` (admins can adjust units and ranges) |

### Chart query (Dashboard)

```sql
SELECT cycle_no, value
  FROM sensor_reading_v
 WHERE sensor_code = :P1_SENSOR
   AND device_id   = :P1_DEVICE
 ORDER BY cycle_no
```

`P1_SENSOR` is a select list based on `SELECT name || ' (' || unit || ')', sensor_code FROM sensor`.

## Why this split

- **APEX (low-code):** storage, reports, charts and user management, built fast with
  wizards.
- **Flask (custom code):** device-facing API, strict validation and clear error
  messages, independent of the UI.
