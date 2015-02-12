#!/usr/bin/env python

"""
This is a proc meant to stand in for the UI until we have it ready.  It
expects this structure in settings:

stub_services:
- foo
stub_notification_lists:
- name: devs
  recipients:
  - brent.tubbs@yougov.com
  - alejandro.rivera@yougov.com
  - fernando.gutierrez@yougov.com
stub_pipelines:
- name: bar
  crontab: "0 2 * * *"
  service: foo
  notification_list: devs

Given that structure, this service will do the following:

- For each service listed in stub_services, ensure there's a corresponding
service in the database.
- For each pipeline listed in stub_pipelines, ensure there's a corresponding
pipeline in the database.
- For each list in stub_notification_lists, ensure there's a corresponding
notification list in the database.
- For each pipeline in the database that's *not* listed in stub_pipelines,
ensure that it's set to inactive.
- Sleep forever by blocking on stdin.

"""

import logging
import sys

from mettle.models import Service, Pipeline, NotificationList
from mettle.settings import get_settings
from mettle.db import make_session_cls

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def main():
    settings = get_settings()
    session = make_session_cls(settings.db_url)()

    services = {}
    for service_name in settings.stub_services:
        service = session.query(Service).filter_by(name=service_name).first()
        if not service:
            logger.info('Making service %s' % service_name)
            service = Service(
                name=service_name,
                updated_by='datastub',
            )
            session.add(service)
        services[service.name] = service

    nl_lists = {}

    for nl_data in settings.stub_notification_lists:
        nl = session.query(NotificationList).filter_by(
            name=nl_data['name'],
        ).first()

        if not nl:
            logger.info('Making notification list %s' % nl_data['name'])
            nl = NotificationList(
                name=nl_data['name'],
                updated_by='datastub',
            )
            session.add(nl)
        nl.recipients = nl_data['recipients']
        nl_lists[nl.name] = nl

    for pl_data in settings.stub_pipelines:
        pipeline = session.query(Pipeline).filter_by(
            name=pl_data['name'],
            service=services[pl_data['service']],
        ).first()

        if not pipeline:
            logger.info('Making pipeline %s' % pl_data['name'])
            pipeline = Pipeline(
                name=pl_data['name'],
                service=services[pl_data['service']],
                updated_by='datastub',
            )
            session.add(pipeline)
        pipeline.crontab = pl_data['crontab']
        pipeline.notification_list = nl_lists[pl_data['notification_list']]

    session.commit()

    logger.info('Sleeping')
    sys.stdin.read()


if __name__ == '__main__':
    main()
