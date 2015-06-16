from sqlalchemy.sql.expression import func
from spa import JSONResponse

from mettle.web.framework import ApiView
from mettle.models import Service


def service_summary(service):
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
    return data


class ServiceList(ApiView):
    def get_services(self):
        services = self.db.query(Service).order_by(func.lower(Service.name)).all()
        return [service_summary(s) for s in services]

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
        ]
        self.bind_queue_to_websocket(exchange, routing_keys)


class ServiceDetail(ApiView):
    def get(self, service_name):
        service = self.db.query(Service).filter_by(name=service_name).one()
        summary = service_summary(service)
        return JSONResponse(summary)

    def websocket(self, service_name):
        settings = self.app.settings
        exchange = settings['state_exchange']
        routing_keys = ['services.' + service_name]
        self.bind_queue_to_websocket(exchange, routing_keys)
