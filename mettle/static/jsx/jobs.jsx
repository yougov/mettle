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


      var headers = {
        '': 'status',
        'ID': 'id',
        'Created': 'created_time',
        'Started': 'start_time',
        'Ended': 'end_time',
        'Host': 'host',
        'PID': 'pid'
      };
      
      var rows = _.map(this.state.jobs, function(data) {
        var status = 'ok';

        if (data.end_time) {
          if (!data.succeeded) {
            status = 'error';
          }
        } else {
          status = 'pending';
        }

        data = _.extend(data, this.getParams());
        data.status = <Mettle.components.StatusLight status={status} />;
        data.jobId = data.id;
        return data;
      }, this); 

      return <Mettle.components.EntityTable
              className={this.props.className}
              caption='Jobs'
              headers={headers}
              rows={rows}
              linkTo='Job'
              idKey='id'
            />;
    }
  });

  var Job = Mettle.components.Job = React.createClass({
    mixins: [Router.State],

    getInitialState: function () {
      return {
        succeeded: false
      };
    },

    componentWillUnmount: function () {
      this.cleanup();
    },

    componentDidMount: function() {
      this.getData();
    },

    cleanup: function() {
      if (this.ws) {
        this.ws.close();
        this.ws = undefined;
      }
    },

    getData: function() {
      var params = this.getParams()
      this.ws = Mettle.getJobStream(params.serviceName, params.pipelineName, params.runId, params.jobId);
      this.ws.onmessage = this.onJobData;
    },

    onJobData: function(ev) {
      this.setState(JSON.parse(ev.data));
    },

    render: function() {
      var params = this.getParams();
      var summary = {
        "Target": this.state.target,
        "Succeeded": this.state.succeeded.toString(),
        "Created": Mettle.formatDate(this.state.created_time),
        "Started": Mettle.formatDate(this.state.start_time),
        "Ended": Mettle.formatDate(this.state.end_time),
        "Host": this.state.host,
        "PID": this.state.pid
      };
      return (
        <div className="pure-u-1 pure-g">
          <Mettle.components.SummaryTable
            caption="Info"
            className="pure-u-1-3 gutter"
            data={summary}
          /> 
          <JobLog
            className="pure-u-2-3"
            serviceName={params.serviceName}
            pipelineName={params.pipelineName}
            runId={params.runId}
            jobId={params.jobId}
          />
        </div>
     );
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

      return <Mettle.components.Log
          className={this.props.className}
          caption="Log" 
          lines={this.state.lines}
        />
    }
  });
})();
