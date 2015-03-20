(function() {
  var Router = ReactRouter;
  var Link = Router.Link;
  var RouteHandler = Router.RouteHandler;

  var JobsList = Mettle.components.JobsList = React.createClass({
    mixins: [Router.State],

    getInitialState: function() {
      return {'jobs': {}};
    },

    getData: function(nextProps) {
      this.cleanup();
      var props = nextProps || this.props;
      this.request = Mettle.getTargetJobs(props.serviceName, props.pipelineName, props.runId, props.target, this.onJobsData);
      this.ws = Mettle.getTargetJobsStream(props.serviceName, props.pipelineName, props.runId, props.target);
      this.ws.onmessage = this.onPipelinesStreamData;
    },

    onJobsData: function(data) {
      this.setState({
        'jobs': _.reduce(data.body.objects, function(jobs, job) {
          jobs[job.id] = job;
          return jobs;
        }, {})
      });
    },

    onJobsStreamData: function(ev) {
      var job = JSON.parse(ev.data);
      var jobs = this.state.jobs;
      jobs[job.id] = job;
      this.setState({
        'jobs': jobs
      });
    },

    cleanup: function() {
      if (this.request) {
        this.request.abort();
        this.request = undefined;
      }

      if (this.ws) {
        this.ws.close();
        this.ws = undefined;
      }
    },

    componentWillUnmount: function () {
      this.cleanup();
    },

    componentDidMount: function() {
      this.getData();
    },

    componentWillReceiveProps: function(nextProps) {
      this.getData(nextProps);
    },

    render: function() {
      var nodes = _.map(this.state.jobs, function(job) {
        var params = this.getParams();
        params['jobId'] = job.id;
        return (
          <li key={'job-link-' + job.id}>
            <Link to="Job" params={params}>{job.id}</Link>
          </li>
          );
      }, this);
      return (<ul>{nodes}</ul>);
    }
  });

  var Job = Mettle.components.Job = React.createClass({
    mixins: [Router.State],
    render: function() {
      var params = this.getParams();
      return (<div>
              {this.getParams().jobId}
              <JobLog serviceName={params.serviceName} pipelineName={params.pipelineName} runId={params.runId} jobId={params.jobId} />
              </div>);
    }
  });

  var JobLog = Mettle.components.JobLog = React.createClass({
    // do some ajax to get the log lines
    // subscribe to a websocket to get new log lines
    // render each line with a number.  in a nice fixed width font.
    // account for the fact that a "line" might actually include newline
    // characters.
    getInitialState: function() {
      return {'lines': {}};  // always keep 'lines' sorted with newest lines at the end.
    },

    componentWillUnmount: function () {
      this.cleanup();
    },

    componentDidMount: function() {
      this.getData();
    },

    componentWillReceiveProps: function(nextProps) {
      this.cleanup();
      this.getData(nextProps);
    },

    cleanup: function() {
      if (this.ws) {
        this.ws.close();
        this.ws = undefined;
      }
    },

    getData: function(nextProps) {
      var props = nextProps || this.props;
      this.ws = Mettle.getJobLogStream(props.serviceName, props.pipelineName, props.runId, props.jobId, 100);
      this.ws.onmessage = this.onLogStreamData;
    },

    onLogStreamData: function(ev) {
      var line = JSON.parse(ev.data);
      var lines = this.state.lines;
      lines[line.line_num] = line;
      this.setState({'lines': lines});
    },

    render: function() {
      var lines = _.sortBy(this.state.lines, 'line_num');
      var nodes = _.map(lines, function(line) {
        return <li>{line.line_num + 1}: {line.msg}</li>;
      });
      return <ul>{nodes}</ul>;
    }
  });
})();
