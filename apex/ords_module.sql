-- ORDS RESTful module that the Flask service calls.
-- Run after schema.sql. In APEX you can also create this under
-- SQL Workshop > RESTful Services.
--
-- Endpoints (base: https://<host>/ords/<schema>/sensor/):
--   POST cycles/                      store one validated cycle
--   GET  cycles/                      list cycles (paginated)
--   GET  cycles/:device_id/:cycle_no  readings of one cycle

BEGIN
    ORDS.define_module(
        p_module_name    => 'sensor',
        p_base_path      => '/sensor/',
        p_items_per_page => 50);

    -- Collection: list + create
    ORDS.define_template(
        p_module_name => 'sensor',
        p_pattern     => 'cycles/');

    ORDS.define_handler(
        p_module_name => 'sensor',
        p_pattern     => 'cycles/',
        p_method      => 'GET',
        p_source_type => ORDS.source_type_collection_feed,
        p_source      => q'[
            SELECT c.device_id,
                   c.cycle_no AS cycle,
                   TO_CHAR(c.recorded_at, 'YYYY-MM-DD HH24:MI:SS') AS recorded_at,
                   (SELECT COUNT(*) FROM sensor_reading r WHERE r.cycle_id = c.id) AS sensor_count
              FROM sensor_cycle c
             ORDER BY c.device_id, c.cycle_no]');

    ORDS.define_handler(
        p_module_name => 'sensor',
        p_pattern     => 'cycles/',
        p_method      => 'POST',
        p_source_type => ORDS.source_type_plsql,
        p_source      => q'[
DECLARE
    l_body      json_object_t := json_object_t.parse(:body_text);
    l_readings  json_object_t := l_body.get_object('readings');
    l_keys      json_key_list := l_readings.get_keys;
    l_cycle_id  sensor_cycle.id%TYPE;
BEGIN
    INSERT INTO sensor_cycle (device_id, cycle_no, recorded_at)
    VALUES (l_body.get_string('device_id'),
            l_body.get_number('cycle'),
            TO_TIMESTAMP(l_body.get_string('recorded_at'), 'YYYY-MM-DD HH24:MI:SS'))
    RETURNING id INTO l_cycle_id;

    FOR i IN 1 .. l_keys.COUNT LOOP
        INSERT INTO sensor_reading (cycle_id, sensor_code, value)
        VALUES (l_cycle_id, l_keys(i), l_readings.get_number(l_keys(i)));
    END LOOP;

    :status_code := 201;
EXCEPTION
    WHEN DUP_VAL_ON_INDEX THEN
        ROLLBACK;
        :status_code := 409;
END;]');

    -- Single cycle
    ORDS.define_template(
        p_module_name => 'sensor',
        p_pattern     => 'cycles/:device_id/:cycle_no');

    ORDS.define_handler(
        p_module_name => 'sensor',
        p_pattern     => 'cycles/:device_id/:cycle_no',
        p_method      => 'GET',
        p_source_type => ORDS.source_type_collection_feed,
        p_source      => q'[
            SELECT TO_CHAR(recorded_at, 'YYYY-MM-DD HH24:MI:SS') AS recorded_at,
                   sensor_code,
                   value
              FROM sensor_reading_v
             WHERE device_id = :device_id
               AND cycle_no  = TO_NUMBER(:cycle_no)
             ORDER BY sensor_code]');

    COMMIT;
END;
/
