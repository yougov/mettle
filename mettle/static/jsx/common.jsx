(function() {

  var Router = ReactRouter;
  var Link = Router.Link;

  Mettle.components.SummaryTable = React.createClass({
    render: function() {
      var rows = _.map(this.props.data, function(val, key) {
        return (<tr key={key}><th>{key}</th><td>{val}</td></tr>);
      });
      return (
        <div className={"pure-g gridblock summary " + this.props.className}>
          <table className="pure-u-1 pure-table">
            <thead>
              <caption>
                {this.props.caption}
                <span className="action">{this.props.action}</span>
              </caption>
            </thead>
            <tbody>
            {rows}
            </tbody>
          </table>
          <p className="subtext">{this.props.subText}</p>
        </div>
      )
    }
  });

  Mettle.components.EntityTable = React.createClass({
    render: function () {
      var headers = _.map(this.props.headers, function(val, key) {
        return <th key={val}>{key}</th>;
      });

      var rows = _.map(this.props.rows, function(data) {
        var cells = _.map(this.props.headers, function(dataKey, name) {
          return <td key={name}><Link to={this.props.linkTo} params={data}>{data[dataKey]}</Link></td>
        }, this);
        return <tr key={data[this.props.idKey]}>{cells}</tr>
      }, this);

      return (
        <div className={"pure-g gridblock " + this.props.className}>
          <table className="pure-u-1 pure-table entity-table">
            <caption>
              {this.props.caption}
              <span className="action">{this.props.action}</span>
            </caption>
            <thead>
              <tr>{headers}</tr>
            </thead>
            <tbody>
              {rows}
            </tbody>
          </table>
        </div>
      );
    }
  });

  Mettle.components.FormInput = React.createClass({
    render: function() {
      return <div className="pure-control-group">
        <label htmlFor={this.props.name}>{this.props.label}
        <input name={this.props.name} id={this.props.name} type={this.props.type} ref={this.props.name} value={this.props.value} onChange={this.props.onChange} checked={this.props.value} /></label>
      </div>;
    }
  })

  Mettle.components.TextBlock = React.createClass({
    render: function() {
      return <div className={"gridblock text-block " + this.props.className}>
        <div className="gridhead">{this.props.caption}</div>
        <p>{this.props.text}</p>
      </div>;
    }
  });

  Mettle.components.StatusLight = React.createClass({
    render: function() {
      var statusClass
      return <div key={this.props.key} className={"status-light " + this.props.status} />
    }
  });

  Mettle.components.Log = React.createClass({
    render: function() {
      // this.props.lines should be an array of objects with 'line_num' and
      // 'msg' attributes.
      var rows = _.map(this.props.lines, function(line) {
        return <tr key={line.line_num}><td className="line-num">{line.line_num}</td><td>{line.msg}</td></tr>;
      });
      return <div className={"gridblock " + this.props.className}>
        <div className="gridhead">{this.props.caption}</div>
        <table className="log">{rows}</table>
      </div>;
    }
  });
})();
