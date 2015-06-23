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

      var headers = {
        "": "status",
        "Name": "name",
        "Updated By": "updated_by",
        "Retries": "retries",
        "Schedule": "schedule",
        "Last Run": "last_run_formatted",
        "Next Run": "next_run_formatted",
        "Notifications": "notificationsCount"
      };

      var rows = _.map(this.state.pipelines, function(data) {
        var notificationsCount = Object.size(this.state.notifications[data.name]);
        var status = notificationsCount === 0 ? "ok" : "warning";
        return _.extend(data, {
          // format next and last run
          "next_run_formatted": Mettle.formatDate(data.next_run_time),
          "last_run_formatted": Mettle.formatDate(data.last_run_time),
          // set schedule from crontab or chained from ID
          "schedule": data.crontab || "Chained from " + data.chained_from_id,
          // a little renaming so the data can be fed to react router.
          "pipelineName": data.name,
          "serviceName": this.props.serviceName,
          "notificationsCount": notificationsCount, 
          "className": "pipeline " + status,
          "status": <Mettle.components.StatusLight status={status} />
        });
      }, this);

      return (
          <Mettle.components.EntityTable
            className={this.props.className}
            caption="Pipelines"
            headers={headers}
            rows={rows}
            linkTo="Pipeline"
            idKey="id"
          />
      );
    }
  });

  var Pipeline = Mettle.components.Pipeline = React.createClass({
    mixins: [Router.State],

    render: function() {
      var routes = this.getRoutes();
      var serviceName = this.getParams().serviceName;
      var pipelineName = this.getParams().pipelineName;
      if (routes[routes.length-1].name === 'Pipeline') {
        // we're the last thing in the path.  Render!
        return (<div className="pure-u-1 pure-g l-box">
          <PipelineSummary
            className="pure-u-1-4 gutter"
            serviceName={serviceName}
            pipelineName={pipelineName}
          />
          <Mettle.components.RunsList
            className="pure-u-3-4"
            serviceName={serviceName}
            pipelineName={pipelineName}
          />
          </div>);
      } else {
        // we're not the last thing in the path.  delegate!
        return <RouteHandler />;
      }
    }
  });

  var PipelineSummary = Mettle.components.PipelineSummary = React.createClass({
    mixins: [Router.State],

    getInitialState: function() {
      return {};
    },

    getData: function(nextProps) {
      this.cleanup();

      this.ws = Mettle.getPipelineStream(this.props.serviceName, this.props.pipelineName);
      this.ws.onmessage = this.onMessage;

      this.ws_notifications = Mettle.getNotificationStream(false, this.props.serviceName);
      this.ws_notifications.onmessage = this.onNotificationsStreamData;
    },

    onMessage: function(ev) {
      this.setState(JSON.parse(ev.data));
    },

    cleanup: function() {
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

    render: function () {

      // We're cobbling together the object this way because we want the
      // properties to show in a certain order in the table.
      var summary = {
        "Name": this.state.name,
      };

      // show crontab, or chained from, but not both.
      if (this.state.crontab) {
        summary['Crontab'] = this.state.crontab;
      }

      if (this.state.chained_from_id) {
        summary['Chained From (ID)'] = this.state.chained_from_id;
      }
      
      summary = _.extend(summary, {
        "Active": this.state.active === undefined ? '' : this.state.active.toString(),
        "Retries": this.state.retries,
        "Updated By": this.state.updated_by
      });
      return <Mettle.components.SummaryTable
          caption="Pipeline Info"
          className={this.props.className}
          id={this.state.id} data={summary}
          action={<Link to="EditPipeline" params={this.getParams()}>Edit</Link>}
        />;
    }
  });

  var EditPipeline = Mettle.components.EditPipeline = React.createClass({
    mixins: [Router.State, Router.Navigation],

    getInitialState: function() {
      return {};
    },

    getData: function(nextProps) {
      var params = this.getParams();
      Mettle.getPipeline(params.serviceName, params.pipelineName, this.onData);
    },

    onData: function(response) {
      if(response.status == 200) {
        console.log(response.body)
        this.setState(response.body);
      }
    },

    handleChange: function(event) {
      var state = this.state;
      if(event.target.type == 'checkbox') {
        state[event.target.name] = event.target.checked;
      }
      else if (event.target.type == 'number') {
        state[event.target.name] = parseFloat(event.target.value);
      }
      else {
        state[event.target.name] = event.target.value;
      }
      this.setState(state);
    },

    handleSubmit: function(event) {
      event.preventDefault();
      var params = this.getParams();
      Mettle.updatePipeline(params.serviceName, params.pipelineName, this.state, this.onSuccess);
    },

    onSuccess: function(response) {
      this.transitionTo('Pipeline', this.getParams());
    },

    componentDidMount: function() {
      this.getData();
    },

    render: function() {
      return (
        <form onSubmit={this.handleSubmit} className={"pure-form pure-form-stacked gridform pure-u-1 " + this.props.className}>
          <fieldset>
            <legend>{this.props.caption}</legend>
            <Mettle.components.FormInput name="active" type="checkbox" value={this.state.active} onChange={this.handleChange} />
            <div className="pure-control-group">
              <label htmlFor="chained_from">Chained from ID</label>
              <select id="chained_from_id" name="chained_from_id" ref="chained_from_id">
                <option>-- default --</option>
                <option value="1">value</option>
              </select>
            </div>
            <Mettle.components.FormInput name="crontab" type="text" value={this.state.crontab} onChange={this.handleChange} />
            <Mettle.components.FormInput name="retries" type="number" value={this.state.retries} onChange={this.handleChange} />
            
            <div className="pure-controls">
              <button type="submit" className="pure-button button-secondary">Submit</button>
            </div>
          </fieldset>
        </form>
      );
    }
  });
})();
