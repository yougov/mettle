from mettle.models import Pipeline, Service
from mettle.web.framework import JSONResponse, View
from mettle.web.rabbit import state_message_stream


class PipelineList(View):
    def get(self, service_name):
        service = self.db.query(Service).filter_by(name=service_name).one()
        pipelines = self.db.query(Pipeline).filter_by(
            service=service
        )
        return JSONResponse(dict(objects=[p.as_dict() for p in pipelines]))

    def websocket(self, service_name):
        settings = self.app.settings
        exchange = settings['state_exchange']

        # Match all messages that have only two components in the routing key,
        # where the first one is the service_name whose pipelines we're
        # watching.
        # See publisher.py for more details on how the routing key works on this
        # exchange.
        routing_key = '%s.*' % service_name

        for msg in state_message_stream(settings.rabbit_url, exchange,
                                        routing_key):
            self.ws.send(msg)


class PipelineDetails(View):
    def get(self, service_name, pipeline_name):
        pipeline = self.db.query(Pipeline).join(Service).filter(
            Service.name==service_name,
            Pipeline.name==pipeline_name,
            Service.id==Pipeline.service_id,
        ).one()
        data = pipeline.as_dict()
        return JSONResponse(data)

