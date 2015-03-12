BEGIN;
    ALTER TABLE pipeline_runs ADD COLUMN target_parameters JSON;
    ALTER TABLE jobs ADD COLUMN target_parameters JSON;
INSERT INTO migration_history (name) VALUES ('0008-target_parameters');
COMMIT;
