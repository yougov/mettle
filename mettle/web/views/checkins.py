from mettle.web.framework import ApiView
from mettle.models import Checkin

from spa import JSONResponse


class CheckinList(ApiView):
    def get_checkins(self):
        checkins = self.db.query(Checkin).order_by(Checkin.time).all()
        return [s.as_dict() for s in checkins]

    def get(self):
        return JSONResponse(dict( objects=self.get_checkins()))

    # PIZZA: I don't know what this method is for
    def websocket(self):
        # keyed by proc_name name
        self.checkins = {s['proc_name']: s for s in self.get_checkins()}

        exchange = self.app.settings['state_exchange']

        routing_keys = [
            'checkins.*',
        ]
        self.bind_queue_to_websocket(exchange, routing_keys)
