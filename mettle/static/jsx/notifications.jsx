(function() {
  var Router = ReactRouter;
  var Link = Router.Link;
  var Route = Router.Route;

  var Notifications = Mettle.components.Notifications = React.createClass({
    mixins: [Router.State],
    getInitialState: function() {
      return {'notifications': {}};
    },

    componentDidMount: function() {
      var params = this.getParams();
      this.cleanup();
      this.ws_notifications = Mettle.getNotificationStream(false, params.serviceName, params.pipelineName, params.runId);
      this.ws_notifications.onmessage = this.onNotificationsStreamData;
    },

    cleanup: function() {
      if (this.ws_notifications) {
        this.ws_notifications.close();
        this.ws_notifications = undefined;
      }
    },

    componentWillUnmount: function () {
      this.cleanup();
    },

    onNotificationsStreamData: function(ev) {
      var notification = JSON.parse(ev.data);
      var notifications = this.state.notifications;
      if(notifications[notification.id] === undefined) {
        notifications[notification.id] = {};        
      }
      notifications[notification.id] = notification;
      console.log(notifications)
      this.setState({
        'notifications': notifications
      });
    },

    handleCheckAll: function() {
      console.log('check all', this.state.notifications)      
    },

    render: function() {
      var notifications = _.map(this.state.notifications, function(notification) {
        var params = {
          created_time: new Date(notification.created_time).toLocaleString()
        }
        var update = function(e) {
          e.preventDefault();
          Mettle.acknowledgeNotification(notification.id)
            .end(function(err, res) {
              if(!err) {
                console.log(res);
              }
            });
        }
        var handleChecked = function(e) {
          console.log(e)
        }
        return (
        <div className={notification.acknowledged_time ? 'pure-g notification acknowledged' : 'pure-g notification'} key={'notification-id-'+notification.id}>          
          <div className="pure-u-1-24"><input type="checkbox" className="notification-checkbox" onChange={handleChecked} checked={notification.acknowledged_time ? 'checked': false} /></div>
          <div className="pure-u-2-24"><Link to="Pipeline" params={{serviceName: notification.service_name, pipelineName: notification.pipeline_name}}>{notification.service_name}</Link></div>
          <div className="pure-u-4-24"><Link to="Pipeline" params={{serviceName: notification.service_name, pipelineName: notification.pipeline_name}}>{notification.pipeline_name}</Link></div>
          <div className="pure-u-2-24"><Link to="Pipeline" params={{serviceName: notification.service_name, pipelineName: notification.pipeline_name}}>{notification.pipeline_run_id}</Link></div>
          <div className="pure-u-10-24"><Link to="Pipeline" params={{serviceName: notification.service_name, pipelineName: notification.pipeline_name}}><pre>{notification.message}</pre></Link></div>
          <div className="pure-u-3-24"><Link to="Pipeline" params={{serviceName: notification.service_name, pipelineName: notification.pipeline_name}}>{params.created_time}</Link></div>
          <div className="pure-u-2-24">
            <form onSubmit={update}>
              <button style={{marginTop: "12px"}} type="submit">Mark as read</button>
            </form>            
          </div>
        </div>
        );
      });
      return (
      <div className="pure-u-1">
        <h1 className="page-header"><Link to="App">Home</Link><Breadcrumbs /><span>Notifications</span></h1>
        <table className="table">
          <thead>
            <tr className="pure-g">
              <th className="pure-u-1-24"><input type="checkbox" style={{margin: "0 auto", display: "block"}} onChange={this.handleCheckAll} /></th>
              <th className="pure-u-2-24">Service</th>
              <th className="pure-u-4-24">Pipeline</th>
              <th className="pure-u-2-24">Run ID</th>
              <th className="pure-u-10-24">Message</th>
              <th className="pure-u-3-24">Created Time</th>
              <th className="pure-u-2-24"></th>
            </tr>
          </thead>
        </table>
        {notifications}
      </div>
      );
    }
  });
})();
