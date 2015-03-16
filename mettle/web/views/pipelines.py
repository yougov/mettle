from mettle.web.framework import JSONResponse, View
from mettle.models import Pipeline, Service


class PipelineList(View):
    def get(self, service_name):
        service = self.db.query(Service).filter_by(name=service_name).one()
        pipelines = self.db.query(Pipeline).filter_by(
            service=service
        )
        return JSONResponse(dict(objects=[p.as_dict() for p in pipelines]))


class PipelineDetails(View):
    def get(self, service_name, pipeline_name):
        pipeline = self.db.query(Pipeline).join(Service).filter(
            Service.name==service_name,
            Pipeline.name==pipeline_name,
            Service.id==Pipeline.service_id,
        ).one()
        data = pipeline.as_dict()
        return JSONResponse(data)

