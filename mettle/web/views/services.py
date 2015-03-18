from sqlalchemy.sql.expression import func

from mettle.web.framework import JSONResponse, View
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
    )

class ServiceList(View):
    def get(self):
        services = self.db.query(Service).order_by(func.lower(Service.name)).all()
        return JSONResponse(dict(
            objects=[service_summary(s) for s in services]
        ))

    def websocket(self):
        settings = self.app.settings
        exchange = settings['state_exchange']

        # Match all messages that have only one component in the routing key,
        # which will be all changes to rows in the services table.  See
        # publisher.py for more details on how the routing key works on this
        # exchange.
        routing_key = '*'

        for msg in state_message_stream(settings.rabbit_url, exchange,
                                        routing_key):
            self.ws.send(msg)
