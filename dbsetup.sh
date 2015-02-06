#!/bin/bash
psql -U postgres -c "create database mettle"

for script in `ls migrations/*/forward.sql`; do
    psql -U postgres -f $script mettle
done
