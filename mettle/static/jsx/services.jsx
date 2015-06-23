 (function() {
  var Router = ReactRouter;
  var Link = Router.Link;
  var RouteHandler = Router.RouteHandler;

  var ServicesList = Mettle.components.ServicesList = React.createClass({
    mixins: [Router.State],
    getInitialState: function() {
      return {'services': {}, 'notifications': {}};
    },

    componentDidMount: function() {
      this.cleanup();
      this.request = Mettle.getServices(this.onServicesData);
      this.ws = Mettle.getServicesStream();
      this.ws.onmessage = this.onServicesStreamData;

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

    onServicesData: function(err, data) {
      if (data) {
        this.setState({'services': data.body.objects.reduce(function(services, svc) {
          services[svc.name] = svc;
          return services;
        }, {})});
      }
    },

    onServicesStreamData: function(ev) {
      var service = JSON.parse(ev.data);
      var services = this.state.services;
      services[service.name] = service;
      this.setState({
        'services': services
      });
    },

    onNotificationsStreamData: function(ev) {
      var notification = JSON.parse(ev.data);
      var notifications = this.state.notifications;
      if(notifications[notification.service_name] === undefined) {
        notifications[notification.service_name] = {};        
      }
      notifications[notification.service_name][notification.id] = notification;
      this.setState({
        'notifications': notifications
      });
    },

    render: function () {

      var headers = {
        'Name': 'name',
        'Updated By': 'updated_by',
        'Pipelines': 'pipeline_count',
        'Notifications': 'notification_count'
      };

      var rows = _.map(this.state.services, function(svc) {
        if(!svc.pipeline_names) svc.pipeline_names = [];
        svc.pipeline_count = svc.pipeline_names.length;
        svc.notifications = Object.size(this.state.notifications[svc.name]);
        svc.serviceName = svc.name; // for url creation
        return svc;
      }, this);

      return <Mettle.components.EntityTable
            className={this.props.className}
            caption="Services"
            headers={headers}
            rows={rows}
            linkTo="Service"
            idKey="id"
          />;
    }
  });

  var Service = Mettle.components.Service = React.createClass({
    mixins: [Router.State],
    getInitialState: function() {
      return {
        pipeline_names: []
      };
    },

    componentDidMount: function() {
      this.cleanup();
      this.ws = Mettle.getServiceStream(this.getParams().serviceName);
      this.ws.onmessage = this.onServiceData;
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

    onServiceData: function(ev) {
      this.setState(JSON.parse(ev.data));
    },

    render: function() {
      if(/notifications/g.test(this.getPath())) {
        return <Mettle.components.Notifications serviceName={this.getParams().serviceName} />;
      }

      if (this.getParams().pipelineName) {
        return <RouteHandler />;
      }

      var summary = {
        "Name": this.state.name,
        "Updated By": this.state.updated_by,
        "Provides": this.state.pipeline_names.join(", ")
      };
      
      return (
        <div className={"pure-u-1 pure-g l-box " + this.props.className}>

          <Mettle.components.SummaryTable 
            className="pure-u-1-4 gutter"
            caption="Info"
            data={summary}
            subText={this.state.description}
          />

          <Mettle.components.PipelinesList
            serviceName={this.getParams().serviceName}
            className="pure-u-3-4"
          />
        </div>
      );
    }
  });

})();
