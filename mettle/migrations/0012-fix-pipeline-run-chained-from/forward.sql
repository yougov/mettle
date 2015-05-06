BEGIN;

DROP INDEX unique_run_chained_from;
ALTER TABLE pipeline_runs DROP COLUMN chained_from_id;


ALTER TABLE pipeline_runs ADD COLUMN chained_from_id INTEGER REFERENCES pipeline_runs (id);
CREATE UNIQUE INDEX unique_run_chained_from ON pipeline_runs (pipeline_id, chained_from_id);


INSERT INTO migration_history (name) VALUES ('0012-fix-pipeline-run-chained-from');
COMMIT;
