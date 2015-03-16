(function() {
  var Router = ReactRouter;
  var Link = Router.Link;
  var RouteHandler = Router.RouteHandler;

  var Service = Mettle.components.Service = React.createClass({
    mixins: [Router.State],
    getInitialState: function() {
      return {'pipelines': []};
    },

    componentDidMount: function() {
      Mettle.getPipelines(this.getParams().serviceName, this.onPipelinesData);
    },

    onPipelinesData: function(data) {
      this.setState({'pipelines': data.objects});
    },

    render: function() {
      var inside = this.getParams().pipelineName ? <RouteHandler /> : <Mettle.components.PipelinesList pipelines={this.state.pipelines} />;
      return (
        <div>
        <h2>Service: {this.getParams().serviceName}</h2>
        {inside}
        </div>
        );
    }
  });

  var ServicesList = Mettle.components.ServicesList = React.createClass({
    mixins: [Router.State],
    getInitialState: function() {
      return {'services': []};
    },

    componentDidMount: function() {
      Mettle.getServices(this.onServicesData);
    },

    onServicesData: function(data) {
      this.setState({'services': data.objects});
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

})();
