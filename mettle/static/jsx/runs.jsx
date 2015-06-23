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
          succeeded: false,

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

    cleanup: function() {
      if (this.request) {
        this.request.abort();
        this.request = undefined;
      }

      if (this.jobStream) {
        this.jobStream.close();
        this.jobStream = undefined;
      }

      if (this.runStream) {
        this.runStream.close();
        this.runStream = undefined;
      }

    },

    componentWillUnmount: function () {
      this.cleanup();
    },

    componentDidMount: function() {
      this.getData();
    },

    componentWillReceiveProps: function(nextProps) {
      this.getData(nextProps);
    },

    getData: function(nextProps) {
      this.cleanup();
      this.setState(this.getInitialState());
      var params = this.getParams();
      this.request = Mettle.getRun(params.serviceName,
                                   params.pipelineName,
                                   params.runId,
                                   this.onPipelineData);

      this.jobStream = Mettle.getRunJobsStream(params.serviceName,
                                     params.pipelineName,
                                     params.runId);
      this.jobStream.onmessage = this.onJobMessage;

      this.runStream = Mettle.getRunStream(params.serviceName,
                                           params.pipelineName,
                                           params.runId)
      this.runStream.onmessage = this.onRunMessage;

      // TODO: Also subscribe to the run's stream to see when its end_time and
      // succeeded fields change.
    },    

    onPipelineData: function(resp) {
      var data = resp.body;

      var newState = {
        runId: data.id,
        targetTime: data.target_time,
        succeeded: data.succeeded,
        createdTime: data.created_time,
        startedBy: data.started_by,
        ackTime: data.ack_time,
        endTime: data.end_time
      };

      if (Object.keys(data.targets).length !== 0) {
        newState.graph = layoutGraph(data.targets, this.nodeSize);
      }

      if (data.pipeline !== undefined) {
        newState.pipeline = data.pipeline;
      }

      if (data.jobs !== undefined) {
        newState.targetJobs = _.reduce(data.jobs, this.updateTargetJobs, this.state.targetJobs, this);
      }
        
      this.setState(newState);
    },

    onRunMessage: function(ev) {
      this.onPipelineData({body: JSON.parse(ev.data)});
    },

    onJobMessage: function(ev) {
      this.setState({
        targetJobs: this.updateTargetJobs(this.state.targetJobs, JSON.parse(ev.data))
      });
    },

    updateTargetJobs: function(targetJobs, job) {
      // given our targetJobs store, and a job record, see whether the job is
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
      var summary = {
        "Target Time": Mettle.formatDate(this.state.targetTime),
        "Succeeded": this.state.succeeded.toString(),
        "Started By": this.state.startedBy,
        "Created Time": Mettle.formatDate(this.state.createdTime),
        "Ack Time": Mettle.formatDate(this.state.ackTime),
        "End Time": Mettle.formatDate(this.state.endTime)
      };
      var inside;

      if (this.getParams().target) {
        return <RouteHandler />;
      }

      return (<div className="pure-u-1 pure-g l-box">
          <Mettle.components.SummaryTable
            data={summary}
            caption="Pipeline Run Info"
            className="pure-u-1-4 gutter"
          />
          <PipelineGraph
            graph={this.state.graph}
            targetJobs={this.state.targetJobs}
            pipeline={this.state.pipeline}
            nodeSize={this.nodeSize}
            key={key}
            caption="Progress Graph"
            className="pure-u-3-4"
          />
      </div>);
    }
  });

  var PipelineGraph = React.createClass({
      mixins: [Router.State],

      render: function() {
          var graph = this.props.graph;
          var graphNodes = graph.nodes().map(function (nodename) {
            var node = graph.node(nodename);
            return (<PipelineTarget node={node} key={nodename} jobs={this.props.targetJobs[nodename]} retries={this.props.pipeline.retries} target={nodename} />);
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
              <div className={"gridblock " + this.props.className}>
                <div className="gridhead">{this.props.caption}</div>
                  <svg width={width} height={height}>
                    {graphNodes}
                    {graphEdges}
                  </svg>
              </div>
          );
      }
  });

  var PipelineTarget = React.createClass({
    mixins: [Router.State],
    getStatus: function() {
      // return unstarted, started, succeeded, failed or unknown

      var targetIsUnstarted = function(jobs) {
        if (jobs===undefined) {
          return true;
        } else if (_.keys(jobs).length === 0) {
          return true;
        } else if (_.all(jobs, function(job) {return job.start_time===null;})) {
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
      var failCount = _.filter(this.props.jobs, function(job) {return job.end_time!==null && job.succeeded===false;}).length || '';
      var status = this.getStatus();

      // React freaks out with SVG namespaced attributes like <a xlink:href="...">.
      // Work around that with dangerouslySetInnerHTML.
      // See https://github.com/facebook/react/issues/2250
      var gProps = {};
      var params = this.getParams();

      // We'd normally use a <Link> component from React Router to generate 
      // <a> tags for us, but since we have to build our own SVG <a> tag, we'll
      // pull the URL from a fake <Link> component rendered onto a throwaway DOM node.
      var dummy = document.createElement('div');
      params.target = encodeURIComponent(this.props.target);
      dummy.innerHTML = React.renderToString(<Link to="Target" params={params} />);
      var url = dummy.getElementsByTagName('a')[0].getAttribute('href');

      var html = '<a xlink:href="' + url + '">';
      html += '<rect '
      html += 'width="' + this.props.node.width + '" ';
      html += 'height="' + this.props.node.height + '" ';
      html += 'x="' + this.props.node.x + '" ';
      html += 'y="' + this.props.node.y + '" ';
      html += 'fill="transparent"></rect></a>';
      gProps.dangerouslySetInnerHTML = {__html: html};
      var linkRect = React.DOM.g(gProps);

      return (
        <g>
          <rect className={status} x={this.props.node.x} y={this.props.node.y} width={this.props.node.width} height={this.props.node.height} rx="1" ry="1" />
          <text className="failCount" x={this.props.node.x + 10} y={this.props.node.y + 20}>{failCount}</text>
          {linkRect}
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
        <path d={pointsToD(this.props.points)} fill="transparent" strokeWidth="1" stroke="#ccc" />
      );
    }
  });

  var NewRun = Mettle.components.NewRun = React.createClass({
    mixins: [Router.State, Router.Navigation],

    onSubmit: function(targetTime) {
      var params = this.getParams();
      Mettle.newRun(params.serviceName, params.pipelineName, targetTime, this.onSuccess);
    },

    onSuccess: function(resp) {
      // succesfully POSTed a new run!  Now redirect the user to the place in
      // the UI where they can watch it.
      var params = this.getParams();
      params['runId'] = resp.body['id'];
      this.transitionTo('PipelineRun', params);
    },

    render: function() {
      var params = this.getParams();
      return (
        <div className="pure-u-1 pure-g l-box">
          <Mettle.components.TextBlock 
            className="pure-u-1-4 gutter"
            caption="New Run"
            text="Enter the date and time for a new run of this pipeline.  All times are UTC."
          />
          <NewRunForm
            serviceName={params.serviceName}
            pipelineName={params.pipelineName}
            onSubmit={this.onSubmit}
            className="gridblock pure-u-3-4"
            caption="Details"
          />
        </div>
      )}
  });

  var NewRunForm = Mettle.components.NewRunForm = React.createClass({
    // Show a form with date and time inputs, populated by default with the
    // current UTC date and time.  You must pass an onSubmit function to this
    // component as a prop.  When the user clicks Submit, that function will be
    // called with the iso8601-formatted datetime string from the form.
    handleSubmit: function(ev, id) {
      ev.preventDefault();
      var date = this.refs.date.getDOMNode().value; 
      var time = this.refs.time.getDOMNode().value; 
      var targetTime = date + "T" + time;
      this.props.onSubmit(targetTime);
    },

    pad: function (num, size) {
      var s = num+"";
      while (s.length < size) s = "0" + s;
      return s;
    },

    render: function() {
      var now = new Date();
      var nowDate = now.getUTCFullYear() + "-" + this.pad(now.getUTCMonth() + 1, 2) + "-" + this.pad(now.getUTCDate(), 2);
      var nowTime = this.pad(now.getUTCHours(), 2) + ":" + this.pad(now.getUTCMinutes(), 2);
      return (
        <form onSubmit={this.handleSubmit} className={"pure-form pure-form-stacked gridform " + this.props.className}>
          <fieldset>
            <legend>{this.props.caption}</legend>
            <div className="pure-control-group">
              <label for="date">Date</label>
              <input id="date" type="date" ref="date" defaultValue={nowDate} />
            </div>
            <div className="pure-control-group">
              <label for="time">Time</label>
              <input id="time" type="time" ref="time" defaultValue={nowTime} />
            </div>

            <div className="pure-controls">
              <button type="submit" className="pure-button button-secondary">Submit</button>
            </div>
          </fieldset>
        </form>
      );
    }
  });

  var RunsList = Mettle.components.RunsList = React.createClass({
    mixins: [Router.State],

    getInitialState: function () {
      return {'runs': {}};
    },

    getData: function(nextProps) {
      this.cleanup();

      var props = nextProps || this.props;
      this.request = Mettle.getRuns(props.serviceName, props.pipelineName, this.onRunsData);
      this.ws = Mettle.getRunsStream(props.serviceName, props.pipelineName);
      this.ws.onmessage = this.onRunsStreamData;
    },

    cleanup: function() {
      if (this.request) {
        this.request.abort();
        this.request = undefined;
      }

      if (this.ws) {
        this.ws.close();
        this.ws = undefined;
      }
    },

    componentWillUnmount: function () {
      this.cleanup();
    },

    componentDidMount: function() {
      this.getData();
    },

    componentWillReceiveProps: function(nextProps) {
      this.getData(nextProps);
    },

    onRunsData: function(resp) {
      var data = resp.body;
      this.setState({
        'runs': _.reduce(data.objects, function (runs, run) {
          runs[run.id] = run;
          return runs;
        }, {})
      });
    },

    onRunsStreamData: function(ev) {
      var run = JSON.parse(ev.data);
      var runs = this.state.runs;
      runs[run.id] = run;
      this.setState({'runs': runs});
    },

    render: function() {
      var headers = {
        "": "status",
        "ID": "runId",
        "Target Time": "targetTime",
        "Created": "createdTime",
        "Ack Time": "ackTime",
        "Ended": "endTime",
        "Started By": "startedBy"
      };

      var rows = _.map(_.sortByOrder(this.state.runs, ['id'], [false]), function(data) {
        var status = 'ok';
        if (data.end_time) {
          if (!data.succeeded) {
            status = 'error';
          }
        } else {
          status = 'pending';
        }

        return {
          serviceName: this.props.serviceName,
          pipelineName: this.props.pipelineName,
          runId: data.id,
          targetTime: Mettle.formatDate(data.target_time),
          createdTime: Mettle.formatDate(data.created_time),
          ackTime: data.ack_time ? Mettle.formatDate(data.ack_time) : '',
          endTime: data.end_time ? Mettle.formatDate(data.end_time) : '',
          startedBy: data.started_by,
          status: <Mettle.components.StatusLight status={status} />
        };
      }, this);

      return <Mettle.components.EntityTable
              className={this.props.className}
              caption="Pipeline Runs"
              action={<Link to="NewRun" params={this.getParams()}>New Run</Link>}
              headers={headers}
              rows={rows}
              linkTo="PipelineRun"
              idKey="runId"
            />;
    }
  });

})();
