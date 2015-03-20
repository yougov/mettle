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
      this.cleanup();
      this.request = Mettle.getServices(this.onServicesData);
      this.ws = Mettle.getServicesStream();
      this.ws.onmessage = this.onServicesStreamData;
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
        <tr key={'service-'+service.name}>
          <td><Link to="Service" params={{serviceName: service.name}}>{service.name}</Link></td>
          <td>{service.updated_by}</td>
        </tr>
        );
      });
      return (<table className="pure-u-1" >{services}</table>);
    }
  });

  var Service = Mettle.components.Service = React.createClass({
    mixins: [Router.State],
    render: function() {
      var inside = this.getParams().pipelineName ? <RouteHandler /> : <Mettle.components.PipelinesList serviceName={this.getParams().serviceName} />;
      return (
        <div className="pure-u-1-3">
        {inside}
        </div>
        );
    }
  });

})();
