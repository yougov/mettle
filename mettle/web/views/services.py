import logging
import json

from sqlalchemy.sql.expression import func
import pika
import utc

from mettle.web.framework import JSONResponse, ApiView
from mettle.web.rabbit import state_message_stream
from mettle.models import (JobLogLine, Job, PipelineRun, Pipeline, Service,
                           Notification)


def service_summary(service, notifications=None):
    # Right now just return a dict of data from the instance, but in the future
    # we'll also send some summary of whether the most recent run in each
    # pipeline was successful.
    data = dict(
        id=service.id,
        name=service.name,
        description=service.description,
        updated_by=service.updated_by,
        pipeline_names=service.pipeline_names,
    )

    if notifications is not None:
        data['notifications'] = {n.id: n.as_dict() for n in notifications}
    return data


class ServiceList(ApiView):
    def get_services(self):
        services = self.db.query(Service).order_by(func.lower(Service.name)).all()
        return [
            service_summary(s, s.notifications.filter_by(acknowledged_by=None))
            for s in services
        ]

    def get(self):
        return JSONResponse(dict( objects=self.get_services()))

    def websocket(self):
        # keyed by service name
        self.services = {s['name']: s for s in self.get_services()}

        exchange = self.app.settings['state_exchange']

        # Match all messages that have only one component in the routing key,
        # which will be all changes to rows in the services table.  See
        # publisher.py for more details on how the routing key works on this
        # exchange.
        routing_keys = [
            'services.*',
            'services.#.notifications',
        ]
        self.bind_queue_to_websocket(exchange, routing_keys)

    def on_rabbit_message(self, ch, method, props, body):
        parsed = json.loads(body)
        if parsed['tablename'] == 'services':
            service_name = parsed['name']
            if service_name not in self.services:
                self.services[service_name] = parsed
                # TODO: get any notifications
            else:
                self.services[service_name].update(parsed)
        elif parsed['tablename'] == 'notifications':
            service_name = parsed['service_name']
            self.services[service_name]['notifications'][parsed['id']] = parsed
        self.ws.send(json.dumps(self.services[service_name]))


class ServiceDetail(ApiView):
    def get(self, service_name):
        service = self.db.query(Service).filter_by(name=service_name).one()
        summary = service_summary(
            service, service.notifications.filter_by(acknowledged_by=None))
        return JSONResponse(summary)

    def websocket(self, service_name):
        settings = self.app.settings
        exchange = settings['state_exchange']
        routing_key = 'services.' + service_name
        _, _, stream = state_message_stream(settings.rabbit_url, exchange,
                                            routing_key)
        for msg in stream:
            self.ws.send(msg)

