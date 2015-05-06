import json
import logging

from mettle.models import Service, Pipeline, PipelineRun, Notification
from mettle.web.framework import JSONResponse, ApiView


logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)



class NotificationView(ApiView):
    def filter_acknowledged(self, query):
        # "acknowledged=false in the query string will return only
        # unacknowledged notifications.  acknowledged=true will return only
        # acknowledged ones.  omitting that qs arg will return all.
        acknowledged = self.request.values.get('acknowledged')
        if acknowledged == 'false':
            query = query.filter(Notification.acknowledged_time==None)
        elif acknowledged == 'true':
            query = query.filter(Notification.acknowledged_time!=None)
        return query

    def get_notifications(self, **kwargs):
        raise NotImplementedError

    def get(self, **kwargs):
        return JSONResponse({'notifications': [n.as_dict() for n in
                                               self.get_notifications(**kwargs)]})

    def websocket(self, **kwargs):
        # first, stream out all the notifications.
        ns = self.get_notifications(**kwargs)

        for n in ns:
            self.ws.send(json.dumps(n.as_dict()))

        self.bind_queue_to_websocket('mettle_state',
                                     [self.get_routing_key(**kwargs)])


class ByService(NotificationView):
    def get_notifications(self, service_name):

        ns = self.db.query(Notification).join(Service).filter(
            Service.name==service_name,
        )

        return self.filter_acknowledged(ns)

    def get_routing_key(self, service_name):
        return 'services.{service_name}.#.notifications'.format(service_name=service_name)


class ByPipeline(NotificationView):
    def get_notifications(self, service_name, pipeline_name):

        ns = self.db.query(Notification).join(
            Service, Notification.service_id==Service.id
        ).join(
            Pipeline, Notification.pipeline_id==Pipeline.id
        ).filter(
            Service.name==service_name,
            Pipeline.name==pipeline_name,
        )

        return self.filter_acknowledged(ns)


class ByRun(NotificationView):
    def get_notifications(self, service_name, pipeline_name, run_id):

        ns = self.db.query(Notification).join(
            Service, Notification.service_id==Service.id
        ).join(
            Pipeline, Notification.pipeline_id==Pipeline.id
        ).join(
            PipelineRun, Notification.pipeline_run_id==PipelineRun.id
        ).filter(
            Service.name==service_name,
            Pipeline.name==pipeline_name,
            PipelineRun.id==run_id,
        )

        return self.filter_acknowledged(ns)
