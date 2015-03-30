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
        <div className={service.errors.length==0 ? 'service pure-g' : 'service pure-g danger'} key={'service-'+service.name}>
          <div className="pure-u-1-24"><div className="circle"></div></div>
          <div className="pure-u-12-24"><Link to="Service" params={{serviceName: service.name}}>{service.name}</Link></div>
          <div className="pure-u-7-24">{service.updated_by}</div>
          <div className="pure-u-2-24">{service.pipeline_names.length}</div>
          <div className="pure-u-2-24">{service.errors.length}</div>
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
              <th className="pure-u-7-24">Updated By</th>
              <th className="pure-u-2-24">Pipelines</th>
              <th className="pure-u-2-24">Errors</th>
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
      var inside = this.getParams().pipelineName ? <RouteHandler /> : <Mettle.components.PipelinesList serviceName={this.getParams().serviceName} />;
      return (
        <div className="pure-u-1">
        {inside}
        </div>
        );
    }
  });

})();
