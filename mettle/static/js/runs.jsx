(function() {
  var Router = ReactRouter;
  var Link = Router.Link;
  var RouteHandler = Router.RouteHandler;

  var layoutGraph = function(graphData, nodeSize) {
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

  var PipelineRun = Mettle.components.PipelineRun = React.createClass({
      mixins: [Router.State],
      nodeSize: 30,

      getInitialState: function() {
        return {
          runId: null,

          // key is a target, value is an object, with job_id as key
          targetJobs: {},

          pipeline: {},

          // fake version of the graph object returned by dagre.
          graph: {
            nodes: function() {return [];},
            edges: function() {return [];},
            graph: function() {return {width: 0, height: 0};}
          },
        };
      },

      componentDidMount: function() {
        var params = this.getParams();
        Mettle.getRun(params.serviceName,
                      params.pipelineName,
                      params.runId,
                      this.onPipelineData);

        var jobStream = Mettle.getJobsStream(params.serviceName,
                                             params.pipelineName,
                                             params.runId);
        jobStream.onmessage = this.onJobMessage;
      },    

      onPipelineData: function(data) {
        var targetJobs = this.state.targetJobs;
        _.each(data.jobs, function(job) {
          targetJobs = this.updateTargetJobs(job, targetJobs);
        }.bind(this));
          
          
        this.setState({
          runId: data.id,
          graph: layoutGraph(data.targets, this.nodeSize),
          targetJobs: targetJobs,
          pipeline: data.pipeline
        });
      },

      onJobMessage: function(ev) {
        this.setState({
          targetJobs: this.updateTargetJobs(JSON.parse(ev.data), this.state.targetJobs)
        });
      },

      updateTargetJobs: function(job, targetJobs) {
        // given a job record, and our targetJobs store, see whether the job is
        // already present in the store.
        //
        // If so, just update it.
        //
        // If not, then add it.
        //
        // Return the store object.
        if (targetJobs[job.target] === undefined) {
          targetJobs[job.target] = {};
        }

        targetJobs[job.target][job.id] = job;
        return targetJobs;
      },

      render: function() {
        var key = 'run_' + this.getParams().runId
        return (
            <div>
              <h4>Run: {this.getParams().runId}</h4>
              <PipelineGraph graph={this.state.graph} targetJobs={this.state.targetJobs} pipeline={this.state.pipeline} nodeSize={this.nodeSize} key={key} />
              <RouteHandler />
            </div>
        );
      }
  });

  var PipelineGraph = React.createClass({
      mixins: [Router.State],

      render: function() {
          var graph = this.props.graph;
          var graphNodes = graph.nodes().map(function (nodename) {
            var node = graph.node(nodename);
            return (<PipelineNode node={node} key={nodename} jobs={this.props.targetJobs[nodename]} retries={this.props.pipeline.retries} target={nodename} />);
          }, this);

          var graphEdges = graph.edges().map(function (e) {
            var edge = graph.edge(e);
            var from = graph.node(e.v);
            var offset = {x: from.width / 2, y: from.height / 2};
  //          // offset the points by the node size
            var offsetPoints = _.map(edge.points, function(p) {
                return {x: p.x + offset.x, y: p.y + offset.y};
            });
            return (<PipelineEdge points={offsetPoints} key={e.v + "-" + e.w} />);
          }, this);

          var width = parseInt(graph.graph().width, 10) + this.props.nodeSize;
          var height = parseInt(graph.graph().height, 10) + this.props.nodeSize;
          return (
              <div>
                <svg width={width} height={height}>
                  {graphNodes}
                  {graphEdges}
                </svg>
              </div>
          );
      }
  });

  var PipelineNode = React.createClass({
    getStatus: function() {
      // return unstarted, started, succeeded, failed or unknown

      var targetIsUnstarted = function(jobs) {
        if (jobs===undefined) {
          return true;
        } else if (_.keys(jobs).length === 0) {
          return true;
        } else if (_.all(jobs, function(job) {job.start_time===null})) {
          return true;
        }
      }
      
      var jobIsActive = function(job) {
        return job.start_time!==null && job.end_time===null;
      };

      var jobIsSucceeded = function(job) {
        return job.succeeded===true;
      };

      var jobIsFailed = function(job) {
        return job.end_time!==null && !job.succeeded;
      };

      // mising state: one or more jobs have failed, and another job is
      // unstarted.

      if (targetIsUnstarted(this.props.jobs)) {
        return 'unstarted';
      } else if (_.any(this.props.jobs, jobIsActive)) {
        return 'running';
      } else if (_.any(this.props.jobs, jobIsSucceeded)) {
        return 'succeeded';
      } else if (_.filter(this.props.jobs, jobIsFailed).length>=this.props.retries) {
        return 'failed';
      } else if (_.any(this.props.jobs, jobIsFailed)) {
        return 'somefails';
      } else {
        return 'unknown';
      }
    },

    render: function() {
      var jobCount = this.props.jobs===undefined ? 0 : _.keys(this.props.jobs).length;
      var status = this.getStatus();
      return (
        <g>
          <rect className={status} x={this.props.node.x} y={this.props.node.y} width={this.props.node.width} height={this.props.node.height} rx="1" ry="1" />
          <text x={this.props.node.x} y={this.props.node.y}>{jobCount}</text>
        </g>
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

  var RunsList = Mettle.components.RunsList = React.createClass({
    mixins: [Router.State],
    render: function() {
      var nodes = _.map(this.props.runs, function(data) {
        var params = {
          serviceName: this.getParams().serviceName,
          pipelineName: this.getParams().pipelineName,
          runId: data.id
        };
        return (
          <li key={"run-link-" + data.name}>
            <Link to="PipelineRun" params={params}>{data.id}</Link>
          </li>);
      }, this);
      return (<ul>{nodes}</ul>);
    }
  });

})();
