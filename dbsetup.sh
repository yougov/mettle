#!/bin/bash
psql -U postgres -c "create database mettle"
mettle migrate
