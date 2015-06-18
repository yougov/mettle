(function() {
  var Router = ReactRouter;
  var Link = Router.Link;
  var RouteHandler = Router.RouteHandler;

  var PipelinesList = Mettle.components.PipelinesList = React.createClass({
    mixins: [Router.State],
    getInitialState: function() {
      return {'pipelines': {}, 'notifications': {}};
    },

    getData: function(nextProps) {
      this.cleanup();

      var props = nextProps || this.props;
      this.request = Mettle.getPipelines(props.serviceName, this.onPipelinesData);
      this.ws = Mettle.getPipelinesStream(props.serviceName);
      this.ws.onmessage = this.onPipelinesStreamData;

      this.ws_notifications = Mettle.getNotificationStream(false, this.getParams().serviceName);
      this.ws_notifications.onmessage = this.onNotificationsStreamData;
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

      if (this.ws_notifications) {
        this.ws_notifications.close();
        this.ws_notifications = undefined;
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

    onNotificationsStreamData: function(ev) {
      var notification = JSON.parse(ev.data);
      var notifications = this.state.notifications;
      if(notifications[notification.pipeline_name] === undefined) {
        notifications[notification.pipeline_name] = {};        
      }
      notifications[notification.pipeline_name][notification.id] = notification;
      this.setState({
        'notifications': notifications
      });
    },

    render: function() {
      var notifications = this.state.notifications;
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
          <div className={Object.size(notifications[data.name])==0 ? 'pipeline pure-g' : 'pipeline pure-g warning'} key={"pipeline-link-" + name}>
            <div className="pure-u-1-24"><Link to="Pipeline" params={{serviceName: this.props.serviceName, pipelineName: data.name}}><div className="circle"></div></Link></div>
            <div className="pure-u-6-24"><Link to="Pipeline" params={{serviceName: this.props.serviceName, pipelineName: data.name}}>{name}</Link></div>
            <div className="pure-u-6-24"><Link to="Pipeline" params={{serviceName: this.props.serviceName, pipelineName: data.name}}>{data.updated_by}</Link></div>
            <div className="pure-u-3-24"><Link to="Pipeline" params={{serviceName: this.props.serviceName, pipelineName: data.name}}>{data.crontab}</Link></div>
            <div className="pure-u-2-24"><Link to="Pipeline" params={{serviceName: this.props.serviceName, pipelineName: data.name}}>{data.retries}</Link></div>
            <div className="pure-u-2-24 notifications"><Link to="PipelineNotifications" params={{serviceName: this.props.serviceName, pipelineName: data.name}} className="badge">{Object.size(notifications[data.name])}</Link></div>
            <div className="pure-u-2-24"><Link to="Pipeline" params={{serviceName: this.props.serviceName, pipelineName: data.name}}>{params.lastRunTime}</Link></div>
            <div className="pure-u-2-24"><Link to="Pipeline" params={{serviceName: this.props.serviceName, pipelineName: data.name}}>{params.newRunTime}</Link></div>
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
              <th className="pure-u-2-24">Notifications</th>
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
      var inside;
      var routes = this.getRoutes();
      if (routes[routes.length-1].name === 'Pipeline') {
        inside = <Mettle.components.RunsList serviceName={this.getParams().serviceName} pipelineName={this.getParams().pipelineName} />;
      } else {
        inside = <RouteHandler />;
      }
      return (
        <div>
          {inside}
        </div>
      );
    }
  });
})();
