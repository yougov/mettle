(function() {
  var Router = ReactRouter;
  var Link = Router.Link;
  var RouteHandler = Router.RouteHandler;


  var Target = Mettle.components.Target = React.createClass({
    // There's not actually a database table or API endpoint for targets.  The list of 
    // target names can be fetched from the pipeline run.  The list of jobs can be fetched from 
    // the jobs endpoint.
    mixins: [Router.State],

    render: function() {
      var params=this.getParams();
      var inside = this.getParams().jobId ? <RouteHandler /> : <Mettle.components.JobsList serviceName={params.serviceName} pipelineName={params.pipelineName} runId={params.runId} target={params.target} />;
      return (
      <div>
        {inside}
      </div>
      );
    }
  });

})();
