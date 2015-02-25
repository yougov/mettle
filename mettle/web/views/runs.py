from mettle.web.framework import JSONResponse, View
from mettle.models import JobLogLine, Job, PipelineRun, Pipeline, Service


class RunJobs(View):
    def get(self, service_name, pipeline_name, run_id, target=None):

        jobs = self.db.query(Job).join(
            PipelineRun).join(Pipeline).join(Service).filter(
                Service.name==service_name,
                PipelineRun.pipeline_id==Pipeline.id,
                Job.pipeline_run_id==run_id,
            )

        if target is not None:
            jobs = jobs.filter_by(target=target)

        return JSONResponse({
            'jobs': [j.as_dict() for j in jobs]
        })


class RunJob(View):
    def get(self, service_name, pipeline_name, run_id, job_id):

        job = self.db.query(Job).join(
            PipelineRun).join(Pipeline).join(Service).filter(
                Service.name==service_name,
                PipelineRun.pipeline_id==Pipeline.id,
                Job.pipeline_run_id==run_id,
                Job.id==job_id
            ).one()

        return JSONResponse(job.as_dict())
