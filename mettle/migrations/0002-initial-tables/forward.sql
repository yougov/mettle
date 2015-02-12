BEGIN;
CREATE TABLE services (
	id SERIAL NOT NULL, 
	name TEXT NOT NULL, 
	description TEXT, 
	updated_by TEXT NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE notification_lists (
	id SERIAL NOT NULL, 
	name TEXT NOT NULL, 
	recipients TEXT[] NOT NULL, 
	updated_by TEXT NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE change_records (
	id SERIAL NOT NULL, 
	"table" TEXT NOT NULL, 
	row_id INTEGER NOT NULL, 
	time TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	operation TEXT NOT NULL, 
	who TEXT, 
	"old" JSON, 
	"new" JSON, 
	PRIMARY KEY (id)
);

CREATE TABLE pipelines (
	id SERIAL NOT NULL, 
	name TEXT NOT NULL, 
	service_id INTEGER NOT NULL, 
	notification_list_id INTEGER NOT NULL, 
	updated_by TEXT NOT NULL, 
	active BOOLEAN DEFAULT true NOT NULL, 
	retries INTEGER, 
	crontab TEXT, 
	chained_from_id INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (name, service_id), 
	CONSTRAINT crontab_or_pipeline_check CHECK (crontab IS NOT NULL OR chained_from_id IS NOT NULL), 
	CONSTRAINT crontab_and_pipeline_check CHECK (NOT (crontab IS NOT NULL AND chained_from_id IS NOT NULL)), 
	FOREIGN KEY(service_id) REFERENCES services (id), 
	FOREIGN KEY(notification_list_id) REFERENCES notification_lists (id), 
	FOREIGN KEY(chained_from_id) REFERENCES pipelines (id)
);

CREATE TABLE pipeline_runs (
	id SERIAL NOT NULL, 
	pipeline_id INTEGER NOT NULL, 
	target_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_time TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	started_by TEXT NOT NULL, 
	ack_time TIMESTAMP WITH TIME ZONE, 
	targets JSON, 
	end_time TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT run_ack_without_targets_check CHECK (NOT (ack_time IS NOT NULL AND targets IS NULL)), 
	CONSTRAINT run_end_without_ack_check CHECK (NOT (end_time IS NOT NULL AND ack_time IS NULL)), 
	FOREIGN KEY(pipeline_id) REFERENCES pipelines (id)
);

CREATE UNIQUE INDEX unique_run_in_progress ON pipeline_runs (pipeline_id, target_time) WHERE end_time IS NULL;

CREATE TABLE jobs (
	id SERIAL NOT NULL, 
	pipeline_run_id INTEGER NOT NULL, 
	target TEXT NOT NULL, 
	succeeded BOOLEAN DEFAULT false NOT NULL, 
	retries_remaining INTEGER NOT NULL, 
	created_time TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	start_time TIMESTAMP WITH TIME ZONE, 
	assigned_worker TEXT, 
	expires TIMESTAMP WITH TIME ZONE, 
	end_time TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT job_succeeded_without_end_check CHECK (NOT (succeeded AND end_time IS NULL)), 
	CONSTRAINT job_end_without_start_check CHECK (NOT (end_time IS NOT NULL AND start_time IS NULL)), 
	CONSTRAINT job_start_without_worker_check CHECK (NOT (start_time IS NOT NULL AND assigned_worker IS NULL)), 
	CONSTRAINT job_start_without_expire_check CHECK (NOT (start_time IS NOT NULL AND expires IS NULL)), 
	FOREIGN KEY(pipeline_run_id) REFERENCES pipeline_runs (id)
);

CREATE UNIQUE INDEX unique_job_in_progress ON jobs (pipeline_run_id, target) WHERE end_time IS NULL;

CREATE TABLE job_log_lines (
	id SERIAL NOT NULL, 
	job_id INTEGER NOT NULL, 
	message TEXT NOT NULL, 
	line_num INTEGER NOT NULL, 
	received_time TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(job_id) REFERENCES jobs (id)
);

CREATE UNIQUE INDEX unique_log_line ON job_log_lines (job_id, line_num);
INSERT INTO migration_history (name) VALUES ('0002-initial-tables');
COMMIT;
