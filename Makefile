.PHONY: dbsetup clean migrate dev

PYPATH=$(shell dirname `which python`)

JSX_DIR=mettle/static/jsx
JSX_TARGETS=$(shell find $(JSX_DIR) -name "*.jsx" | sed s/jsx$$/js/)

dbsetup:
	-psql -U postgres -c "drop database mettle"
	psql -U postgres -c "create database mettle"

clean: dbsetup
	-rm -rf mettle/static/jsx/.module-cache
	-rm mettle/static/jsx/*js
	-rm -rf mettle/static/bower
	-rm -rf tmp/HawaiianPipeline/*
	-rm -rf tmp/PepperoniPipeline/*
	-rm -rf mettle/static/bower
	-scripts/rabbitmqadmin delete exchange name=mettle_announce_service
	-scripts/rabbitmqadmin delete exchange name=mettle_announce_pipeline_run
	-scripts/rabbitmqadmin delete exchange name=mettle_ack_pipeline_run
	-scripts/rabbitmqadmin delete exchange name=mettle_nack_pipeline_run
	-scripts/rabbitmqadmin delete exchange name=mettle_claim_job
	-scripts/rabbitmqadmin delete exchange name=mettle_end_job
	-scripts/rabbitmqadmin delete exchange name=mettle_job_logs
	-scripts/rabbitmqadmin delete exchange name=mettle_state	
	-scripts/rabbitmqadmin delete queue name=etl_service_pizza
	-scripts/rabbitmqadmin delete queue name=mettle_dispatcher
	-scripts/rabbitmqadmin delete queue name=mettle_job_logs

$(PYPATH)/npm:
	pip install nodeenv
	nodeenv -p --prebuilt

$(PYPATH)/jsx: $(PYPATH)/npm
	npm install -g react-tools
	touch $(PYPATH)/jsx # Make 'make' realize this is new.

$(PYPATH)/bower: $(PYPATH)/npm
	npm install -g bower
	touch $(PYPATH)/bower

mettle/static/bower: $(PYPATH)/bower
	cd mettle/static; bower install --config.interactive=0

$(PYPATH)/mettle:
	pip install -e . -i http://cheese.yougov.net

migrate: $(PYPATH)/mettle
	mettle migrate

dev: clean mettle/static/bower migrate

jsx: $(JSX_TARGETS)

$(JSX_DIR)/%.js: $(PYPATH)/jsx
	jsx $(shell echo $@ | sed s/js$$/jsx/) > $@
