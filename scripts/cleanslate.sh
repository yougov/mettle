#!/bin/bash

# run this script from the root of the mettle repository to clean out the
# current DB and get a new one with fake data inside.  Like this:

# $ scripts/freshdb.sh

psql -U postgres -c "drop database mettle"
psql -U postgres -c "create database mettle"

mettle migrate

# Clean out anything in ./tmp/foo/*.
if [ -d tmp ]; then
    rm -rf tmp/HawaiianPipeline/*
    rm -rf tmp/PepperoniPipeline/*
fi

# Delete Rabbit exchanges.
scripts/rabbitmqadmin delete exchange name=mettle_announce_service
scripts/rabbitmqadmin delete exchange name=mettle_announce_pipeline_run
scripts/rabbitmqadmin delete exchange name=mettle_ack_pipeline_run
scripts/rabbitmqadmin delete exchange name=mettle_nack_pipeline_run
scripts/rabbitmqadmin delete exchange name=mettle_claim_job
scripts/rabbitmqadmin delete exchange name=mettle_end_job
scripts/rabbitmqadmin delete exchange name=mettle_job_logs
scripts/rabbitmqadmin delete exchange name=mettle_state

# Delete Rabbit queues.
scripts/rabbitmqadmin delete queue name=etl_service_pizza
scripts/rabbitmqadmin delete queue name=mettle_dispatcher
scripts/rabbitmqadmin delete queue name=mettle_job_logs
