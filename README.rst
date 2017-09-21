.. image:: https://img.shields.io/pypi/v/mettle.svg
   :target: https://pypi.org/project/mettle

.. image:: https://img.shields.io/pypi/pyversions/mettle.svg

.. image:: https://img.shields.io/pypi/dm/mettle.svg

.. image:: https://img.shields.io/travis/yougov/mettle/master.svg
   :target: http://travis-ci.org/yougov/mettle

Mettle is a framework for managing extract/transform/load (ETL) jobs.  ETL
processes present a number of problems that Mettle is designed to solve:

License
=======

License is indicated in the project metadata (typically one or more
of the Trove classifiers). For more details, see `this explanation
<https://github.com/jaraco/skeleton/issues/1>`_.

Description
===========

- Jobs need to be run at specific times.  Sometimes they need to be triggered by
  the completion of other jobs.   Mettle supports scheduling both time-based
  and trigger-based jobs.
- Various people in an organization need to be able to see job schedules and
  the state of recent runs.  Naive scripts running on cron jobs, scattered
  amongst a large number of servers, create a serious problem with visibility.
  Mettle solves this by centralizing the job scheduling, state reporting, and
  log viewing.
- Sometimes jobs fail because of temporary problems somewhere (a flaky network,
  a too-full disk).  Mettle will automatically retry jobs to deal with this.
- Sometimes jobs fail and will not be able to succeed until the job has been
  reconfigured (a changed password on a database, for example).  Mettle makes it
  easy to manually re-launch a job after such issues have been resolved.
- If you try to solve the above problems by centralizing all your ETL execution,
  you quickly run into a problem of proliferating dependencies.  A centralized
  ETL service can become hard to develop and hard to deploy because all those
  dependencies (libraries, external APIs, external databases) introduce more
  instability.  Mettle is designed to isolate those dependencies into separate
  ETL services, so instability in one ETL doesn't impact any others.

We picked the name "Mettle" because:

- It's got the letters E, T, and L in it.
- It means "ability to continue despite difficulties".
- It sounds like "metal", which is solid.

Mettle is comprised of several components:

- Web UI.  Features:
    - Configure schedules for pipelines.
    - Display past jobs, both successful and failed.
    - Display currently-executing jobs, with live status updates and streaming
      logs.
    - Manually launch jobs.
- Timer: Reads pipeline schedules from the database and sends out RabbitMQ messages
  when pipelines need to be kicked off.
- Dispatcher: Records which jobs are being executed by which workers, and their
  eventual success or failure.
- Logger: Receives log messages sent from ETL Services over RabbitMQ, and saves
  them to Postgres.
- ETL Services: Implement the actual business logic and systems integration to
  move data between systems.

Mettle uses Postgres to store state, and RabbitMQ for inter-process
communication.
