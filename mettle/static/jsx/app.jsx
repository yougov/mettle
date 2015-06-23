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

  CurrentUser = React.createClass({
    getCookie: function (sKey) {
      if (!sKey) { return null; }
      return decodeURIComponent(document.cookie.replace(new RegExp("(?:(?:^|.*;)\\s*" + encodeURIComponent(sKey).replace(/[\-\.\+\*]/g, "\\$&") + "\\s*\\=\\s*([^;]*).*$)|^.*$"), "$1")) || null;
  },

    render: function() {
      var username =  this.getCookie('display_name');
      return (<div className="current-user">Logged in as {username}. <a href="/logout/">Log out</a></div>)
    }
  });

  Breadcrumbs = React.createClass({
    mixins: [Router.State],
    render: function() {
      var links = [<li key="home"><Link to="App">Home</Link></li>];
      var params = this.getParams();

      if (params.serviceName) {
        links.push(<li key={params.serviceName}>
          <Link to="Service" params={params}>Service: {params.serviceName}</Link>
          </li>);
        if (params.pipelineName) {
          links.push(<li key={params.pipelineName}>
            <Link to="Pipeline" params={params}>Pipeline: {params.pipelineName}</Link>
            </li>);
          if (params.runId) {
            links.push(<li key={"run-" + params.runId}>
              <Link to="PipelineRun" params={params}> Run ID: {params.runId}</Link>
              </li>);
            if (params.target) {
              links.push(<li key={params.target}>
                <Link to="Target" params={params}>Target: {params.target}</Link>
                </li>);
              if (params.jobId) {
                links.push(<li key={"job-" + params.jobId}>
                    <Link to="Job" params={params}>Job ID: {params.jobId}</Link>
                    </li>);
              }
            }
          }
        }
      }
      return (<h1 className={"breadcrumbs " + this.props.className}><ul className={"list-inline "}>{links}</ul></h1>);
    }
  });

  App = React.createClass({
    mixins: [Router.State],
    render: function () {
      var inside = this.getParams().serviceName ? <RouteHandler /> : <Mettle.components.ServicesList className="pure-u-1 l-box" />;
      return (
        <div className="pure-g">
          <header className="pure-u-1 l-box">
            <h1 className="title"><Link to="App">Mettle</Link></h1>
            <CurrentUser />
          </header>
          <Breadcrumbs className="pure-u-1 l-box" />
          {inside} 
        </div>
      );
    }
  });

  var routes = (
    <Route name="App" path="/" handler={App}>
      <Route name="Service" path="services/:serviceName/" handler={Mettle.components.Service}>
        <Route name="ServiceNotifications" path="notifications/"
          handler={Mettle.components.Notifications} />
        <Route name="Pipeline" path="pipelines/:pipelineName/"
          handler={Mettle.components.Pipeline}>
          <Route name="PipelineNotifications" path="notifications/"
            handler={Mettle.components.Notifications} />
          <Route name="EditPipeline" path="edit/" handler={Mettle.components.EditPipeline} />
          <Route name="NewRun" path="runs/new/" handler={Mettle.components.NewRun} />
          <Route name="PipelineRun" path="runs/:runId/" handler={Mettle.components.PipelineRun}>
            <Route name="PipelineRunNotifications" path="notifications/"
              handler={Mettle.components.Notifications} />
            <Route name="Target" path="targets/:target/" handler={Mettle.components.Target}>
              <Route name="Job" path="jobs/:jobId/" handler={Mettle.components.Job} />
            </Route>
          </Route>
        </Route>
      </Route>
      <NotFoundRoute handler={Mettle.components.NotFound} />
    </Route>
  );

  Router.run(routes, function (Handler) {
    React.render(<Handler/>, document.getElementById('content'));
  });
})();
