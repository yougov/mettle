from mettle.web.framework import ApiView
from mettle.models import Checkin

from spa import JSONResponse


class CheckinList(ApiView):
    def get_checkins(self):
        checkins = self.db.query(Checkin).order_by(Checkin.time).all()
        return [s.as_dict() for s in checkins]

    def get(self):
        return JSONResponse(dict( objects=self.get_checkins()))

