BEGIN;
    ALTER TABLE jobs DROP COLUMN retries_remaining;

    ALTER TABLE pipeline_runs ADD COLUMN succeeded BOOLEAN DEFAULT false;
INSERT INTO migration_history (name) VALUES ('0004-misc-columns');
COMMIT;
