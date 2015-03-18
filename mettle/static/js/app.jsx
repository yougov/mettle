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

  Breadcrumbs = React.createClass({
    mixins: [Router.State],
    render: function() {
      var links = [<li><Link to="App" className="title">Mettle</Link></li>];
      var params = this.getParams();

      if (params.serviceName) {
        links.push(<li><Link to="Service" params={params}>{params.serviceName}</Link></li>);
        if (params.pipelineName) {
          links.push(<li><Link to="Pipeline" params={params}>{params.pipelineName}</Link></li>);
          if (params.runId) {
            links.push(<li><Link to="PipelineRun" params={params}>{params.runId}</Link></li>);
          };
        };
      };
      return (<ul className="nav">{links}</ul>);
    }
  });

  App = React.createClass({
    mixins: [Router.State],
    render: function () {
      var inside = this.getParams().serviceName ? <RouteHandler /> : <Mettle.components.ServicesList />;
      return (
        <div>
          <header>
            <Breadcrumbs />
            <div className="user">Logged in as Jane</div>
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
