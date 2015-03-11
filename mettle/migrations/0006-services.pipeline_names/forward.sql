BEGIN;
    ALTER TABLE services ADD COLUMN pipeline_names TEXT[];
INSERT INTO migration_history (name) VALUES ('0006-services.pipeline_names');
COMMIT;
