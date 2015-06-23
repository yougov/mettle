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
      this.setState({
        'notifications': notifications
      });
    },

    handleCheckAll: function() {
      var notifications = this.state.notifications;
      for(var key in notifications) {
        if(notifications.hasOwnProperty(key)) {
          notifications[key].checked = this.refs.checkAll.getDOMNode().checked;
        }
      }
      this.setState({
        'notifications': notifications
      });
    },

    handleCheck: function(notification_id) {
      var notifications = this.state.notifications;
      notifications[notification_id].checked = !notifications[notification_id].checked;
      this.setState({
        'notifications': notifications
      });
    },

    acknowledge: function(notification_id) {
      Mettle.acknowledgeNotification(notification_id)
        .end(function(err, res) {
          if(!err) {
            // optional callback actions here
          }
        });
    },

    acknowledgeSelected: function(e) {
      e.preventDefault();
      var notifications = this.state.notifications;
      for(var key in notifications) {
        if(notifications.hasOwnProperty(key)) {
          if(notifications[key].checked) {
            this.acknowledge(key);
          }
        }
      }
      // reset our 'check all' input
      this.refs.checkAll.getDOMNode().checked = false;
    },

    render: function() {
      var notifications = _.map(this.state.notifications, function(notification) {
        var params = {
          created_time: new Date(notification.created_time).toLocaleString()
        }
        return (
        <div className={notification.acknowledged_time ? 'pure-g notification acknowledged' : 'pure-g notification'} key={'notification-id-'+notification.id}>          
          <div className="pure-u-1-24"><input type="checkbox" className="notification-checkbox" onChange={this.handleCheck.bind(this, notification.id)} checked={notification.checked} /></div>
          <div className="pure-u-2-24"><Link to="Pipeline" params={{serviceName: notification.service_name, pipelineName: notification.pipeline_name}}>{notification.service_name}</Link></div>
          <div className="pure-u-4-24"><Link to="Pipeline" params={{serviceName: notification.service_name, pipelineName: notification.pipeline_name}}>{notification.pipeline_name}</Link></div>
          <div className="pure-u-2-24"><Link to="Pipeline" params={{serviceName: notification.service_name, pipelineName: notification.pipeline_name}}>{notification.pipeline_run_id}</Link></div>
          <div className="pure-u-10-24"><Link to="Pipeline" params={{serviceName: notification.service_name, pipelineName: notification.pipeline_name}}><pre>{notification.message}</pre></Link></div>
          <div className="pure-u-3-24"><Link to="Pipeline" params={{serviceName: notification.service_name, pipelineName: notification.pipeline_name}}>{params.created_time}</Link></div>
          <div className="pure-u-2-24">
            <button className="button-xsmall pure-button" style={{marginTop: "12px"}} type="button" onClick={this.acknowledge.bind(this, notification.id)}>Mark as read</button>
          </div>
        </div>
        );
      }.bind(this));
      return (
      <div className="pure-u-1">
        <table className="table">
          <thead>
            <tr className="pure-g">
              <th className="pure-u-1-24"><input type="checkbox" style={{margin: "0 auto", display: "block"}} onChange={this.handleCheckAll} ref="checkAll" /></th>
              <th className="pure-u-2-24">Service</th>
              <th className="pure-u-4-24">Pipeline</th>
              <th className="pure-u-2-24">Run ID</th>
              <th className="pure-u-10-24">Message</th>
              <th className="pure-u-3-24">Created Time</th>
              <th className="pure-u-2-24">
                <form onSubmit={this.acknowledgeSelected}>
                  <button className="button-xsmall pure-button" type="submit">Mark selected</button>
                </form>
              </th>
            </tr>
          </thead>
        </table>
        {notifications}
      </div>
      );
    }
  });
})();
