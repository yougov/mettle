BEGIN;

-- Services
CREATE OR REPLACE FUNCTION services_notify_func() RETURNS trigger as $$
DECLARE
  payload text;
BEGIN
  payload := row_to_json(new_with_table)::text FROM (SELECT NEW.*, 'services' as tablename) new_with_table;
  IF octet_length( payload ) > 8000 THEN
    -- this won't work in a pg_notify
    payload := ('{"id": "' || NEW.id || '", "error": "too long", "tablename": "services"}')::json::text;
  END IF;
  PERFORM pg_notify( 'mettle_state'::text, payload );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER services_notify_trig AFTER INSERT OR UPDATE ON services
   FOR EACH ROW EXECUTE PROCEDURE services_notify_func();

-- Pipelines
CREATE OR REPLACE FUNCTION pipelines_notify_func() RETURNS trigger as $$
DECLARE
  payload text;
BEGIN
  payload := row_to_json(new_with_table)::text FROM (SELECT NEW.*, 'pipelines' as tablename) new_with_table;
  IF octet_length( payload ) > 8000 THEN
    -- this won't work in a pg_notify
    payload := ('{"id": "' || NEW.id || '", "error": "too long", "tablename": "pipelines"}')::json::text;
  END IF;
  PERFORM pg_notify( 'mettle_state'::text, payload );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER pipelines_notify_trig AFTER INSERT OR UPDATE ON pipelines
   FOR EACH ROW EXECUTE PROCEDURE pipelines_notify_func();

-- Pipeline Runs
CREATE OR REPLACE FUNCTION pipeline_runs_notify_func() RETURNS trigger as $$
DECLARE
  payload text;
BEGIN
  payload := row_to_json(new_with_table)::text FROM (SELECT NEW.*, 'pipeline_runs' as tablename) new_with_table;
  IF octet_length( payload ) > 8000 THEN
    -- this won't work in a pg_notify
    payload := ('{"id": "' || NEW.id || '", "error": "too long", "tablename": "pipeline_runs"}')::json::text;
  END IF;
  PERFORM pg_notify( 'mettle_state'::text, payload );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER pipeline_runs_notify_trig AFTER INSERT OR UPDATE ON pipeline_runs
   FOR EACH ROW EXECUTE PROCEDURE pipeline_runs_notify_func();

-- Jobs
CREATE OR REPLACE FUNCTION jobs_notify_func() RETURNS trigger as $$
DECLARE
  payload text;
BEGIN
  payload := row_to_json(new_with_table)::text FROM (SELECT NEW.*, 'jobs' as tablename) new_with_table;
  IF octet_length( payload ) > 8000 THEN
    -- this won't work in a pg_notify
    payload := ('{"id": "' || NEW.id || '", "error": "too long", "tablename": "jobs"}')::json::text;
  END IF;
  PERFORM pg_notify( 'mettle_state'::text, payload );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER jobs_notify_trig AFTER INSERT OR UPDATE ON jobs
   FOR EACH ROW EXECUTE PROCEDURE jobs_notify_func();


INSERT INTO migration_history (name) VALUES ('0005-notify-triggers');

COMMIT;
