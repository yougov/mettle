.PHONY: dbsetup clean_files clean_rabbit clean migrate dev js

# Both Python and Node programs will be put here.
BIN=$(shell dirname `which python`)

STATIC_DIR=mettle/static
JSX_DIR=$(STATIC_DIR)/jsx
# Our React components have dependencies on each other.  This ordering is important.
JSX_MODULES=common jobs targets runs pipelines services app
JSX_TARGETS=$(foreach module,$(JSX_MODULES),$(JSX_DIR)/$(module).js)

dbsetup:
	-psql -U postgres -c "drop database mettle"
	psql -U postgres -c "create database mettle"

clean_files:
	-rm -rf mettle/static/jsx/.module-cache
	-rm mettle/static/jsx/*js
	-rm -rf mettle/static/bower
	-rm -rf tmp/*Pipeline/*
	-rm -rf mettle/static/bower_components
	-rm -rf $(STATIC_DIR)/js/compiled.js
	-rm -rf $(JSX_TARGETS)

clean_rabbit:
	-scripts/rabbitmqadmin delete exchange name=mettle_announce_service
	-scripts/rabbitmqadmin delete exchange name=mettle_announce_pipeline_run
	-scripts/rabbitmqadmin delete exchange name=mettle_ack_pipeline_run
	-scripts/rabbitmqadmin delete exchange name=mettle_nack_pipeline_run
	-scripts/rabbitmqadmin delete exchange name=mettle_claim_job
	-scripts/rabbitmqadmin delete exchange name=mettle_end_job
	-scripts/rabbitmqadmin delete exchange name=mettle_job_logs
	-scripts/rabbitmqadmin delete exchange name=mettle_state	
	-scripts/rabbitmqadmin delete queue name=etl_service_pizza
	-scripts/rabbitmqadmin delete queue name=etl_service_sun
	-scripts/rabbitmqadmin delete queue name=mettle_dispatcher
	-scripts/rabbitmqadmin delete queue name=mettle_job_logs

clean: dbsetup clean_files clean_rabbit

$(BIN)/bumpversion:
	pip install bumpversion

# By letting 'nodeenv' install node.js, it will be placed into the Python virtualenv.
$(BIN)/npm:
	pip install nodeenv
	nodeenv -p --prebuilt

$(BIN)/jsx: $(BIN)/npm
	npm install -g react-tools
	touch $(BIN)/jsx # Make 'make' realize this is new.

$(BIN)/bower: $(BIN)/npm
	npm install -g bower
	touch $(BIN)/bower

$(BIN)/uglifyjs: $(BIN)/npm
	npm install -g uglify-js
	touch $(BIN)/uglifyjs

# This is slightly hacky.  mettle/static/bower is a folder, not a file, so Make
# is never going to recognize it as already existing.
mettle/static/bower: $(BIN)/bower
	cd mettle/static; bower install --config.interactive=0

$(BIN)/mettle:
	pip install -e .

migrate: $(BIN)/mettle
	mettle migrate

dev: clean mettle/static/bower migrate $(BIN)/bumpversion

$(JSX_DIR)/%.js: $(BIN)/jsx
	jsx $(shell echo $@ | sed s/js$$/jsx/) > $@

$(STATIC_DIR)/js/compiled.js: $(BIN)/uglifyjs $(JSX_TARGETS)
	uglifyjs $(STATIC_DIR)/js/mettle.js $(JSX_TARGETS) -c -m > $@

# shorthand
js: $(STATIC_DIR)/js/compiled.js
