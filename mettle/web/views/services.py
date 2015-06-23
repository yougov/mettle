import json

from sqlalchemy.sql.expression import func
from spa import JSONResponse

from mettle.web.framework import ApiView
from mettle.models import Service


class ServiceList(ApiView):
    def get_services(self):
        services = self.db.query(Service).order_by(func.lower(Service.name)).all()
        return [s.as_dict() for s in services]

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
        return JSONResponse(service.as_dict())

    def websocket(self, service_name):
        service = self.db.query(Service).filter_by(name=service_name).one()
        self.ws.send(json.dumps(service.as_dict()))
        settings = self.app.settings
        exchange = settings['state_exchange']
        routing_keys = ['services.' + service_name]
        self.bind_queue_to_websocket(exchange, routing_keys)
