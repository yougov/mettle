BEGIN;

CREATE TABLE checkins (
	proc_name TEXT NOT NULL,
	time TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (proc_name)
);

INSERT INTO migration_history (name) VALUES ('0013-add-checkins-table');
COMMIT;