(function() {
  var Router = ReactRouter;
  var Route = Router.Route;
  var NotFoundRoute = Router.NotFoundRoute;
  var RouteHandler = Router.RouteHandler;
  var Link = Router.Link;

  var NotFound = Mettle.components.NotFound = React.createClass({
    render: function() {
      return (<p>That page cannot be found.</p>);
    }
  });

  App = React.createClass({
    mixins: [Router.State],
    render: function () {
      var inside = this.getParams().serviceName ? <RouteHandler /> : <Mettle.components.ServicesList />;
      return (
        <div>
          <header>
            <ul>
              <li><Link to="App">Home</Link></li>
              <li><Link to="PipelineRun" params={{serviceName: "pizza", pipelineName: "pepperoni", runId: "1"}}>PR 1</Link></li>
              <li><Link to="PipelineRun" params={{serviceName: "foo", pipelineName: "bar", runId: "2"}}>PR 2</Link></li>
            </ul>
            Logged in as Jane
          </header>

          {inside} 
        </div>
      );
    }
  });

  var routes = (
    <Route name="App" path="/" handler={App}>
      <Route name="Service" path="services/:serviceName/" handler={Mettle.components.Service}>
        <Route name="Pipeline" path="pipelines/:pipelineName/" handler={Mettle.components.Pipeline}>
          <Route name="PipelineRun" path="runs/:runId/" handler={Mettle.components.PipelineRun} />
        </Route>
      </Route>
      <NotFoundRoute handler={Mettle.components.NotFound} />
    </Route>
  );

  Router.run(routes, function (Handler) {
    React.render(<Handler/>, document.getElementById('content'));
  });
})();
