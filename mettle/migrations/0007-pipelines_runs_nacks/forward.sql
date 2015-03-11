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
INSERT INTO migration_history (name) VALUES ('0007-pipelines_runs_nacks');
COMMIT;
