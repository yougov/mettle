BEGIN;

ALTER TABLE pipeline_runs ADD COLUMN chained_from_id INTEGER REFERENCES pipelines (id);
CREATE UNIQUE INDEX unique_run_chained_from ON pipeline_runs (pipeline_id, chained_from_id);
INSERT INTO migration_history (name) VALUES ('0011-pipeline-run-chained-from');
COMMIT;
