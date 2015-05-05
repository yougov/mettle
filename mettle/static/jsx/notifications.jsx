(function() {
  var Router = ReactRouter;
  var Route = Router.Route;

  Notifications =  React.createClass({
    mixins: [Router.State],

    getInitialState: function() {
      return {'notifications': {}};
    },

    render: function() {

    }
  });
})();
