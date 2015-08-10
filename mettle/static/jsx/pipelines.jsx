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
    
    getData: function(nextProps) {
      var params = this.getParams();
      Mettle.getPipeline(params.serviceName, params.pipelineName, this.onData);
    },

    onData: function(response) {
      if(response.status == 200) {
        this.setState(response.body);
      }
    },

    handleSubmit: function(event) {
      event.preventDefault();
      var params = this.getParams();
      if(this.state.scheduleType === 'chained' && this._renderedComponent.state) {
        payload = this._renderedComponent.state; // this may be a hack, not sure, but it works
      } else {
        payload = this.state;
      }
      Mettle.updatePipeline(params.serviceName, params.pipelineName, payload, this.onSuccess);
    },

    onSuccess: function(response) {
      this.transitionTo('Pipeline', this.getParams());
    },

    componentDidMount: function() {
      this.getData();
    },

    render: function() {
      if (this.state === null) {
        return <div />;
      }
      return <PipelineForm 
        className={this.props.className}
        handleSubmit={this.handleSubmit}
        caption={this.props.caption}
        pipelineData={this.state}
      />
    }
  });

  var PipelineForm = Mettle.components.PipelineForm = React.createClass({

    getInitialState: function() {
      var data = this.props.pipelineData || {};

      if (data.crontab) {
        data.scheduleType = 'crontab';
      } else {
        data.scheduleType = 'chained';
      }
      return data;
    },

    handleChange: function(event) {
      var state = this.state;
      if(event.target.type == 'checkbox') {
        state[event.target.name] = event.target.checked;
      }
      else if (event.target.type == 'number') {
        state[event.target.name] = parseFloat(event.target.value);
      }
      else if (event.target.name == 'chained_from_id') {
        state['crontab'] = null;
        state[event.target.name] = parseFloat(event.target.value);
      }
      else if (event.target.name == 'crontab') {
        state['chained_from_id'] = null;
        state[event.target.name] = event.target.value;
      }
      else {
        state[event.target.name] = event.target.value;
      }
      this.setState(state);
    },

    onPipelinesListData: function(response) {
      if(response.status == 200) {
        if(!this.state.services) {
          var services = {};

          if(response.body.objects) {
            _.map(response.body.objects, function(pipeline) {
              if(!services[pipeline.service_name]) {
                services[pipeline.service_name] = []
                services[pipeline.service_name].push(pipeline)
              } else {
                services[pipeline.service_name].push(pipeline)
              }
            })

            this.setState({'services': services})
          }
        } else {
          if(response.body.service_name && !this.state.pipelines) {
            this.state.chained_service_name = response.body.service_name
            this.setState({'pipelines': this.state.services[response.body.service_name]})
          }
        }
      }
    },

    handleSelectService: function(event) {
      this.state.chained_service_name = event.target.value
      this.setState({'pipelines': this.state.services[event.target.value]})
    },
    
    getScheduleComponent: function() {
      if (this.state.scheduleType === 'crontab') {
        return <Mettle.components.FormInput
            label="Crontab"
            name="crontab"
            type="text"
            value={this.state.crontab}
            onChange={this.handleChange}
          />;
      } else if (this.state.scheduleType === 'chained') {
        // build our service and pipeline dropdowns
        Mettle.getPipelinesList(this.onPipelinesListData);

        if(this.state.chained_from_id && !this.state.pipelines) {
          // pre-select our populated dropdowns with predefined data
          Mettle.getPipelineById(this.state.chained_from_id, this.onPipelinesListData);
        }

        var services_ddl = _.map(this.state.services, function(service, key) {
          return (
            <option key={'service-ddl-id-'+key} value={key}>{key}</option>
          );
        }.bind(this));

        var pipelines_ddl = _.map(this.state.pipelines, function(pipeline) {
          return (
            <option key={'pipeline-ddl-id-'+pipeline.id} value={pipeline.id}>{pipeline.name}</option>
          );
        }.bind(this));

        return ( 
          <div>
            <div className="pure-control-group">
              <label htmlFor="service">Service</label>
              <select id="chained_service_name" name="chained_service_name" ref="chained_service_name" onChange={this.handleSelectService} value={this.state.chained_service_name}>
                <option>---------</option>
                {services_ddl}
              </select>
            </div>
            <div className="pure-control-group">
              <label htmlFor="chained_from">Pipeline</label>
              <select id="chained_from_id" name="chained_from_id" ref="chained_from_id" onChange={this.handleChange} value={this.state.chained_from_id}>
                <option>---------</option>
                {pipelines_ddl}
              </select>
            </div>
          </div>
        );
      }
    },

    render: function() {
      return (
        <form onSubmit={this.props.handleSubmit}
          className={"pure-form pure-form-stacked gridform pure-u-1 " + this.props.className}>
          <fieldset>
            <legend>{this.props.caption}</legend>
            
            <div className="pure-control-group">
              <label htmlFor="scheduleType">Schedule Type</label>
              <select id="scheduleType"
                name="scheduleType"
                ref="scheduleType"
                value={this.state.scheduleType} 
                onChange={this.handleChange}>
                <option value="crontab">Crontab</option>
                <option value="chained">Chained</option>
              </select>
            </div>
            
            {this.getScheduleComponent()}
            
            <Mettle.components.FormInput
              label="Retries"
              name="retries"
              type="number"
              value={this.state.retries}
              onChange={this.handleChange}
            />
            
            <Mettle.components.FormInput
              label="Active"
              name="active"
              type="checkbox"
              value={this.state.active}
              onChange={this.handleChange}
            />

            <div className="pure-controls">
              <button type="submit" className="pure-button button-secondary">Submit</button>
            </div>
          </fieldset>
        </form>
      );
    }
  });
})();
