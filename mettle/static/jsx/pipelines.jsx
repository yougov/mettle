(function() {
  var Router = ReactRouter;
  var Link = Router.Link;
  var RouteHandler = Router.RouteHandler;

  var PipelinesList = Mettle.components.PipelinesList = React.createClass({
    mixins: [Router.State],
    getInitialState: function() {
      return {'pipelines': {}};
    },

    getData: function(nextProps) {
      this.cleanup();

      var props = nextProps || this.props;
      this.request = Mettle.getPipelines(props.serviceName, this.onPipelinesData);
      this.ws = Mettle.getPipelinesStream(props.serviceName);
      this.ws.onmessage = this.onPipelinesStreamData;
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

    onPipelinesData: function(data) {
      this.setState({
        'pipelines': _.reduce(data.body.objects, function(pipelines, pipeline) {
          pipelines[pipeline.name] = pipeline;
          return pipelines;
        }, {})
      });
    },

    onPipelinesStreamData: function(ev) {
      var pipeline = JSON.parse(ev.data);
      var pipelines = this.state.pipelines;
      pipelines[pipeline.name] = pipeline;
      this.setState({
        'pipelines': pipelines
      });
    },

    render: function() {
      var nodes = _.map(this.state.pipelines, function(data, name) {
        var run_id, params = {
          newRunTime: new Date(data.next_run_time).toLocaleString(),
          lastRunTime: null
        }
        if(Object.keys(data['runs']).length > 0) {
          run_id = Object.keys(data['runs'])[0];
          params['lastRunTime'] = data['runs'][run_id].end_time ? new Date(data['runs'][run_id].end_time).toLocaleString() : null
        }

        return (
          <div className="pipeline pure-g" key={"pipeline-link-" + name}>
            <div className="pure-u-1-24"><div className="circle"></div></div>
            <div className="pure-u-6-24"><Link to="Pipeline" params={{serviceName: this.props.serviceName, pipelineName: data.name}}>{name}</Link></div>
            <div className="pure-u-6-24">{data.updated_by}</div>
            <div className="pure-u-3-24">{data.crontab}</div>
            <div className="pure-u-2-24">{data.retries}</div>
            <div className="pure-u-2-24">{params.lastRunTime}</div>
            <div className="pure-u-2-24">{params.newRunTime}</div>
          </div>);
      }, this);
      return (
      <div className="pure-u-1">
        <h1 className="page-header"><Link to="App">Home</Link><Breadcrumbs /><span>Pipelines</span></h1>
        <table className="table">
          <thead>
            <tr className="pure-g">
              <th className="pure-u-1-24"></th>
              <th className="pure-u-6-24">Name</th>
              <th className="pure-u-6-24">Updated By</th>
              <th className="pure-u-3-24">Crontab</th>
              <th className="pure-u-2-24">Retries</th>
              <th className="pure-u-2-24">Last Run</th>
              <th className="pure-u-2-24">Next Run</th>
            </tr>
          </thead>
        </table>
        {nodes}
      </div>
      );
    }
  });

  var Pipeline = Mettle.components.Pipeline = React.createClass({
    mixins: [Router.State],

    render: function() {
      var inside = this.getParams().runId ? <RouteHandler /> : <Mettle.components.RunsList serviceName={this.getParams().serviceName} pipelineName={this.getParams().pipelineName} />;
      return (
        <div>
          {inside}
        </div>
      );
    }
  });
})();
