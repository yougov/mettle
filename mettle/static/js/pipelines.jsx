(function() {
  var Router = ReactRouter;
  var Link = Router.Link;
  var RouteHandler = Router.RouteHandler;

  var PipelinesList = Mettle.components.PipelinesList = React.createClass({
    mixins: [Router.State],
    render: function() {
      var nodes = _.map(this.props.pipelines, function(data) {
        return (
          <li key={"pipeline-link-" + data.name}>
            <Link to="Pipeline" params={{serviceName: this.getParams().serviceName, pipelineName: data.name}}>{data.name}</Link>
          </li>);
      }, this);
      return (<ul>{nodes}</ul>);
    }
  });

  var Pipeline = Mettle.components.Pipeline = React.createClass({
    mixins: [Router.State],

    getInitialState: function () {
      return {'runs': []};
    },

    componentDidMount: function() {
      Mettle.getRuns(this.getParams().serviceName, this.getParams().pipelineName, this.onRunsData);
    },

    onRunsData: function(data) {
      this.setState({'runs': data.objects});
    },

    render: function() {
      var inside = this.getParams().runId ? <RouteHandler /> : <Mettle.components.RunsList runs={this.state.runs} />;
      return (
        <div>
          <h3>Pipeline: {this.getParams().pipelineName}</h3>
          {inside}
        </div>
      );
    }
  });
})();
