BEGIN;

CREATE TABLE services (
	id SERIAL NOT NULL, 
	name TEXT NOT NULL, 
	broker TEXT NOT NULL, 
	description TEXT, 
	updated_by TEXT NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
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


CREATE TABLE notification_lists (
	id SERIAL NOT NULL, 
	name TEXT NOT NULL, 
	recipients TEXT[] NOT NULL, 
	updated_by TEXT NOT NULL, 
	PRIMARY KEY (id)
);


CREATE TABLE pipelines (
	id SERIAL NOT NULL, 
	name TEXT NOT NULL, 
	service_id INTEGER NOT NULL, 
	schedule JSON, 
	notification_list_id INTEGER NOT NULL, 
	updated_by TEXT NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name, service_id), 
	FOREIGN KEY(service_id) REFERENCES services (id), 
	FOREIGN KEY(notification_list_id) REFERENCES notification_lists (id)
);


CREATE TABLE pipeline_runs (
	id SERIAL NOT NULL, 
	pipeline_id INTEGER NOT NULL, 
	created_time TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	target_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	ack_time TIMESTAMP WITH TIME ZONE, 
	started_by TEXT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(pipeline_id) REFERENCES pipelines (id)
);


CREATE TABLE jobs (
	id SERIAL NOT NULL, 
	pipeline_run_id INTEGER NOT NULL, 
	target TEXT NOT NULL, 
	in_progress BOOLEAN NOT NULL, 
	status INTEGER NOT NULL, 
	hostname TEXT, 
	created_time TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	start_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	end_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT job_status_check CHECK (status in (0, 1, 2, 3)), 
	FOREIGN KEY(pipeline_run_id) REFERENCES pipeline_runs (id)
);

CREATE UNIQUE INDEX unique_target_in_progress ON jobs (target) WHERE in_progress;
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
