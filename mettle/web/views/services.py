from sqlalchemy.sql.expression import func

from mettle.web.framework import JSONResponse, View
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
