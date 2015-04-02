BEGIN;

ALTER TABLE pipelines ADD UNIQUE (id, service_id);
ALTER TABLE pipeline_runs ADD UNIQUE (id, pipeline_id);
ALTER TABLE jobs ADD UNIQUE (id, pipeline_run_id);

CREATE TABLE notifications (
	id SERIAL NOT NULL, 
	created_time TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	message TEXT NOT NULL, 
	acknowledged_by TEXT, 
	acknowledged_time TIMESTAMP WITH TIME ZONE, 
	service_id INTEGER NOT NULL, 
	pipeline_id INTEGER, 
	pipeline_run_id INTEGER, 
	job_id INTEGER, 
	PRIMARY KEY (id), 
	CONSTRAINT notification_ack_time_check CHECK (NOT (acknowledged_by IS NOT NULL AND acknowledged_time IS NULL)), 
	CONSTRAINT notification_ack_by_check CHECK (NOT (acknowledged_time IS NOT NULL AND acknowledged_by IS NULL)), 
	CONSTRAINT notification_job_check CHECK (NOT (job_id IS NOT NULL AND pipeline_run_id IS NULL)), 
	CONSTRAINT notification_run_check CHECK (NOT (pipeline_run_id IS NOT NULL AND pipeline_id IS NULL)), 
	FOREIGN KEY(service_id, pipeline_id) REFERENCES pipelines (service_id, id), 
	FOREIGN KEY(pipeline_id, pipeline_run_id) REFERENCES pipeline_runs (pipeline_id, id), 
	FOREIGN KEY(pipeline_run_id, job_id) REFERENCES jobs (pipeline_run_id, id), 
	FOREIGN KEY(service_id) REFERENCES services (id), 
	FOREIGN KEY(pipeline_id) REFERENCES pipelines (id), 
	FOREIGN KEY(pipeline_run_id) REFERENCES pipeline_runs (id), 
	FOREIGN KEY(job_id) REFERENCES jobs (id)
);


CREATE OR REPLACE FUNCTION notifications_notify_func() RETURNS trigger as $$
DECLARE
  payload text;
BEGIN
  payload := row_to_json(new_with_table)::text FROM (SELECT NEW.*, 'notifications' as tablename) new_with_table;
  IF octet_length( payload ) > 8000 THEN
    -- this won't work in a pg_notify
    payload := ('{"id": "' || NEW.id || '", "error": "too long", "tablename": "notifications"}')::json::text;
  END IF;
  PERFORM pg_notify( 'mettle_state'::text, payload );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;


CREATE TRIGGER notifications_notify_trig AFTER INSERT OR UPDATE ON notifications
   FOR EACH ROW EXECUTE PROCEDURE notifications_notify_func();

-- clean up old log lines index a little, replacing named index with unique
-- constraint on table.
DROP INDEX unique_log_line;
ALTER TABLE job_log_lines ADD UNIQUE (job_id, line_num);

INSERT INTO migration_history (name) VALUES ('0010-notifications');
COMMIT;
