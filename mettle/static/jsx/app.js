
var pizzaGraph = {
  "flour": [],
  "water": [],
  "yeast": [],
  "sugar": [],
  "salt": [],
  "olive oil": [],
  "mix": ["flour", "water", "yeast", "sugar", "salt", "olive oil"],
  "raise": ["mix"],
  "roll": ["raise"],
  "sauce": ["roll"],
  "cheese": ["sauce"],
  "pepperoni": ["sauce"],
  "bake": ["cheese", "pepperoni"],
  "box": ["bake"],
  "deliver": ["box"],
  "eat": ["deliver"]
};

var nodeSize = 30;

var layoutGraph = function(graphData) {
// Given a JS object where each key is a node and each value is a list of nodes
// that that item depends on, return a Dagre graph.
  var g = new dagre.graphlib.Graph();
  g.setGraph({
      'rankdir': 'TB',
      'nodesep': '20',
      'ranksep': 20,
    });
  g.setDefaultEdgeLabel(function() { return {}; });
  _.forOwn(graphData, function(val, key, obj) {
      g.setNode(key, { label:key,  width: nodeSize, height: nodeSize });
  });


  _.forOwn(graphData, function(val, key, obj) {
      _.each(val, function(i) {
        g.setEdge(i, key);
      });
  });
  dagre.layout(g);
  return g;
};

var PipelineGraph = React.createClass({
    render: function() {
        var graph = this.props.graph;
        var graphNodes = this.props.graph.nodes().map(function (nodename) {
          var node = graph.node(nodename);
          return (<PipelineNode node={node} key={nodename}/>);
        });

        var graphEdges = this.props.graph.edges().map(function (e) {
          var edge = graph.edge(e);
          var from = graph.node(e.v);
          var offset = {x: from.width / 2, y: from.height / 2};
//          // offset the points by the node size
          var offsetPoints = _.map(edge.points, function(p) {
              return {x: p.x + offset.x, y: p.y + offset.y};
          });
          return (<PipelineEdge points={offsetPoints} key={e.v + "-" + e.w} />);
        });

        var width = parseInt(this.props.graph.graph().width, 10) + parseInt(this.props.extra, 10);
        var height = parseInt(this.props.graph.graph().height, 10) + parseInt(this.props.extra, 10);
        return (
            <svg width={width} height={height}>
              {graphNodes}
              {graphEdges}
            </svg>
        );
    }
});

var PipelineNode = React.createClass({
  render: function() {
    return (
      <rect class={this.props.state} x={this.props.node.x} y={this.props.node.y} width={this.props.node.width} height={this.props.node.height} stroke-width="1" stroke="#ccc" fill="transparent"/>
    );
  }
});

var PipelineEdge = React.createClass({
  render: function() {
    var pointsToD = function(points) {
      var d = "";
      for (var j=0;j<points.length;j++) {
        p = points[j];

        if (j===0) {
          d += "M ";
        } else {
          d += "L ";
        }
        d += p.x + " " + p.y + " ";
      }
      return d;
    }

    return (
      <path d={pointsToD(this.props.points)} fill="transparent" stroke-width="1" stroke="#ccc" />
    );
  }
});

var graph = layoutGraph(pizzaGraph);

React.render(
  <PipelineGraph graph={graph} extra={nodeSize} />,
  document.getElementById('content')
);


