import logging

from sqlalchemy.sql.expression import func
from geventwebsocket.websocket import WebSocket
import pika
import utc

from mettle.web.framework import JSONResponse, ApiView
from mettle.web.rabbit import state_message_stream
from mettle.models import JobLogLine, Job, PipelineRun, Pipeline, Service


def service_summary(service):
    # Right now just return a dict of data from the instance, but in the future
    # we'll also send some summary of whether the most recent run in each
    # pipeline was successful.
    return dict(
        id=service.id,
        name=service.name,
        description=service.description,
        updated_by=service.updated_by,
        pipeline_names=service.pipeline_names,
        errors=[],
    )

class ServiceList(ApiView):
    def get(self):
        services = self.db.query(Service).order_by(func.lower(Service.name)).all()
        return JSONResponse(dict(
            objects=[service_summary(s) for s in services]
        ))

    def websocket(self):
        exchange = self.app.settings['state_exchange']

        # Match all messages that have only one component in the routing key,
        # which will be all changes to rows in the services table.  See
        # publisher.py for more details on how the routing key works on this
        # exchange.
        routing_key = 'services.*'
        self.bind_queue_to_websocket(exchange, routing_key)


class ServiceDetail(ApiView):
    def get(self, service_name):
        service = self.db.query(Service).filter_by(name=service_name).one()
        return JSONResponse(service_summary(service))

    def websocket(self, service_name):
        settings = self.app.settings
        exchange = settings['state_exchange']
        routing_key = 'services.' + service_name
        for msg in state_message_stream(settings.rabbit_url, exchange,
                                        routing_key):
            self.ws.send(msg)

