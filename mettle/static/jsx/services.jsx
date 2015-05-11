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
      var notifications = this.state.notifications;
      var services = _.map(this.state.services, function(service) {
        if(!service.pipeline_names) service.pipeline_names = [];
        return (
        <div className={Object.size(notifications[service.name])==0 ? 'service pure-g' : 'service pure-g warning'} key={'service-'+service.name}>          
          <div className="pure-u-1-24"><Link to="Service" params={{serviceName: service.name}}><div className="circle"></div></Link></div>
          <div className="pure-u-12-24"><Link to="Service" params={{serviceName: service.name}}>{service.name}</Link></div>
          <div className="pure-u-6-24"><Link to="Service" params={{serviceName: service.name}}>{service.updated_by}</Link></div>
          <div className="pure-u-2-24"><Link to="Service" params={{serviceName: service.name}}>{service.pipeline_names ? service.pipeline_names.length : 0}</Link></div>
          <div className="pure-u-3-24 notifications"><Link to="ServiceNotifications" params={{serviceName: service.name}} className="badge">{Object.size(notifications[service.name])}</Link></div>
        </div>
        );
      });
      return (
      <div className="pure-u-1">
        <h1 className="page-header">Services</h1>
        <table className="table">
          <thead>
            <tr className="pure-g">
              <th className="pure-u-1-24"></th>
              <th className="pure-u-12-24">Name</th>
              <th className="pure-u-6-24">Updated By</th>
              <th className="pure-u-2-24">Pipelines</th>
              <th className="pure-u-3-24">Notifications</th>
            </tr>
          </thead>
        </table>
        {services}
      </div>
      );
    }
  });

  var Service = Mettle.components.Service = React.createClass({
    mixins: [Router.State],
    render: function() {
      var inside;
      if(/notifications/g.test(this.getPath())) {
        inside = <Mettle.components.Notifications serviceName={this.getParams().serviceName} />
      } else {
        inside = this.getParams().pipelineName ? <RouteHandler /> : <Mettle.components.PipelinesList serviceName={this.getParams().serviceName} />;
      }
      return (
        <div className="pure-u-1">
        {inside}
        </div>
        );
    }
  });

})();
