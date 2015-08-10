import json
import logging

from spa import JSONResponse
from spa import exceptions

from mettle.models import Pipeline, Service
from mettle.web.framework import ApiView

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class PipelineList(ApiView):
    def get_pipelines(self, service_name=None):
        pipelines = self.db.query(Pipeline)
        if service_name:
            service = self.db.query(Service).filter_by(name=service_name).one()
            pipelines = pipelines.filter_by(service=service)

        pipelines = pipelines.order_by(Pipeline.service_id,
                                       Pipeline.name.asc())
        return [p.as_dict() for p in pipelines]

    def get(self, service_name=None):
        return JSONResponse(dict(objects=self.get_pipelines(service_name)))

    def websocket(self, service_name):
        # keyed by pipeline name
        self.pipelines = {p['name']: p for p in self.get_pipelines(service_name)}

        exchange = self.app.settings['state_exchange']

        # Match all messages that have only two components in the routing key,
        # where the first one is the service_name whose pipelines we're
        # watching.
        # See publisher.py for more details on how the routing key works on this
        # exchange.
        routing_keys = [
            'services.%s.pipelines.*' % service_name,
            'services.%s.pipelines.#.runs.*' % service_name,
        ]
        self.bind_queue_to_websocket(exchange, routing_keys)

    def on_rabbit_message(self, ch, method, props, body):
        parsed = json.loads(body)
        if parsed['tablename'] == 'pipelines':
            pipeline_name = parsed['name']
            if pipeline_name not in self.pipelines:
                self.pipelines[pipeline_name] = parsed
            else:
                self.pipelines[pipeline_name].update(parsed)
        elif parsed['tablename'] == 'pipeline_runs':
            pipeline_name = parsed['pipeline_name']
            self.pipelines[pipeline_name]['runs'][parsed['id']] = parsed
        self.ws.send(json.dumps(self.pipelines[pipeline_name]))

    def post(self, service_name):
        service = self.db.query(Service).filter_by(name=service_name).one()
        data = self.request.json()

        # name must match one of the pipeline_names in the service
        assert data['name'] in service.pipeline_names, 'Invalid pipeline name'

        pipeline = Pipeline(
            name=data['name'],
            notification_list_id=data['notification_list_id'],
            crontab=data.get('crontab'),
            chained_from_id=data.get('chained_from_id'),
            service=service,
            updated_by=self.request.session['username'],
        )

        # optional field
        if 'retries' in data:
            pipeline.retries = data['retries']

        self.db.add(pipeline)
        self.db.commit()

        url = self.app.url('pipeline_detail', dict(
            service_name=service_name,
            pipeline_name=pipeline.name,
        ))

        return JSONResponse(pipeline.as_dict(), headers={'Location': url},
                            status=302)


class PipelineDetails(ApiView):
    def get(self, service_name, pipeline_name):
        pipeline = self.db.query(Pipeline).join(Service).filter(
            Service.name==service_name,
            Pipeline.name==pipeline_name,
            Service.id==Pipeline.service_id,
        ).one()
        return JSONResponse(pipeline.as_dict())

    def put(self, service_name, pipeline_name):
        pipeline = self.db.query(Pipeline).join(Service).filter(
            Service.name==service_name,
            Pipeline.name==pipeline_name,
            Service.id==Pipeline.service_id,
        ).one()
        data = self.request.json()

        # These are controlled from messages in the mettle protocol, not from
        # the UI.
        uneditable_fields = ('service_id', 'name')
        for f in uneditable_fields:
            if f in data and data[f] != getattr(pipeline, f):
                raise exceptions.JSONBadRequest('Cannot change %s' % f)

        editable_fields = ('active', 'retries', 'crontab', 'chained_from_id',
                           'notification_list_id')
        edited = False
        for f in editable_fields:
            if f in data:
                oldval = getattr(pipeline, f)
                newval = data[f]
                if newval != oldval:
                    setattr(pipeline, f, newval)
                    edited = True
        if edited:
            pipeline.updated_by = self.request.session['username']
        self.db.commit()
        return JSONResponse(pipeline.as_dict())

    def websocket(self, service_name, pipeline_name):
        pipeline = self.db.query(Pipeline).join(Service).filter(
            Service.name==service_name,
            Pipeline.name==pipeline_name,
            Service.id==Pipeline.service_id,
        ).one()
        self.ws.send(json.dumps(pipeline.as_dict()))
        exchange = self.app.settings['state_exchange']
        routing_keys = [
            'services.%s.pipelines.%s' % (service_name, pipeline_name),
        ]
        self.bind_queue_to_websocket(exchange, routing_keys)

    def on_rabbit_message(self, ch, method, props, body):
        # Here we're doing an extra DB query for every change event.  That's a
        # bit wasteful, but this is a low traffic stream.
        info = json.loads(body)
        pipeline = self.db.query(Pipeline).get(info['id'])
        info.update(pipeline.as_dict())
        self.ws.send(json.dumps(info))


class PipelineDetailsById(ApiView):
    def get(self, pipeline_id):
        pipeline = self.db.query(Pipeline).filter(
            Pipeline.id==pipeline_id,
        ).one()
        return JSONResponse(pipeline.as_dict())
