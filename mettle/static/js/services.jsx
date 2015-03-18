(function() {
  var Router = ReactRouter;
  var Link = Router.Link;
  var RouteHandler = Router.RouteHandler;

  var ServicesList = Mettle.components.ServicesList = React.createClass({
    mixins: [Router.State],
    getInitialState: function() {
      return {'services': {}};
    },

    componentDidMount: function() {
      this.request = Mettle.getServices(this.onServicesData);
      this.ws = Mettle.getServicesStream();
      this.ws.onmessage = this.onServicesStreamData;
    },

    componentWillUnmount: function () {
      this.request.abort();
      this.ws.close();
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

    render: function () {
      var services = _.map(this.state.services, function(service) {
        return (
        <div key={'service-'+service.name}>
          <Link to="Service" params={{serviceName: service.name}}>{service.name}</Link>
        </div>
        );
      });
      return (<div>{services}</div>);
    }
  });

  var Service = Mettle.components.Service = React.createClass({
    mixins: [Router.State],
    render: function() {
      var inside = this.getParams().pipelineName ? <RouteHandler /> : <Mettle.components.PipelinesList serviceName={this.getParams().serviceName} />;
      return (
        <div>
        <h2>Service: {this.getParams().serviceName}</h2>
        {inside}
        </div>
        );
    }
  });

})();
