import json
import logging

import utc
from werkzeug.utils import redirect
from werkzeug.exceptions import BadRequest
from spa import JSONResponse

from mettle.models import Service, Pipeline, PipelineRun, Notification
from mettle.web.framework import ApiView


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

class List(NotificationView):
    def get_notifications(self):
        ns = self.db.query(Notification)
        return self.filter_acknowledged(ns)

    def get_routing_key(self):
        return 'services.#.notifications'


# Note that this isn't a streamable resource.  We haven't needed it to be, yet.
class Detail(ApiView):
    def get(self, notification_id):
        print notification_id
        n = self.db.query(Notification).filter_by(id=notification_id).one()
        return JSONResponse(n.as_dict())

    def post(self, notification_id):
        n = self.db.query(Notification).filter_by(id=notification_id).one()
        if n.acknowledged_by is None:
            # TODO: check data length first so we can't be DOSed with a huge
            # payload.

            data = json.loads(self.request.get_data())
            if data.get('acknowledged') == True:
                user = self.request.session['username']
                n.acknowledged_by = user
                n.acknowledged_time = utc.now()
                print n
                self.db.commit()
                return redirect('/api/notifications/{id}/'.format(
                    id=notification_id), code=303)
            else:
                return BadRequest('Must include acknowledged: true to '
                                  'acknowledge a notification.')
        else:
            return BadRequest('Notification already acknowledged.')


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

    def get_routing_key(self, service_name, pipeline_name):
        return 'services.{service_name}.pipelines.{pipeline_name}.#.notifications'.format(
            service_name=service_name,
            pipeline_name=pipeline_name
        )


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

    def get_routing_key(self, service_name, pipeline_name, run_id):
        return 'services.{service_name}.pipelines.{pipeline_name}.runs.{run_id}.#.notifications'.format(
            service_name=service_name,
            pipeline_name=pipeline_name,
            run_id=run_id
        )
