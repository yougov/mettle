BEGIN;
    CREATE TABLE pipeline_runs_nacks (
      id SERIAL NOT NULL, 
      pipeline_run_id INTEGER NOT NULL, 
      created_time TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
      message TEXT NOT NULL, 
      reannounce_time TIMESTAMP WITH TIME ZONE, 
      PRIMARY KEY (id), 
      FOREIGN KEY(pipeline_run_id) REFERENCES pipeline_runs (id)
    );

    CREATE OR REPLACE FUNCTION pipeline_runs_nacks_notify_func() RETURNS trigger as $$
    DECLARE
      payload text;
    BEGIN
      payload := row_to_json(new_with_table)::text FROM (SELECT NEW.*, 'pipeline_runs_nacks' as tablename) new_with_table;
      IF octet_length( payload ) > 8000 THEN
        -- too long for a pg_notify
        payload := ('{"id": "' || NEW.id || '", "error": "too long", "tablename": "pipeline_runs_nacks"}')::json::text;
      END IF;
      PERFORM pg_notify( 'mettle_state'::text, payload );
      RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER pipeline_runs_nacks_notify_trig AFTER INSERT OR UPDATE ON pipeline_runs_nacks
       FOR EACH ROW EXECUTE PROCEDURE pipeline_runs_nacks_notify_func();
INSERT INTO migration_history (name) VALUES ('0007-pipelines_runs_nacks');
COMMIT;
