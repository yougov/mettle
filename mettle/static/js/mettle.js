(function(global) {

  var debug = true;
  var log = function(txt) {
    if (debug) {
      console.log(txt);
    }
  };

  var Mettle = global.Mettle = {'components': {}};

  var WSPREFIX = function() {
    var loc = window.location, newUri;
    if (loc.protocol === "https:") {
        newUri = "wss:";
    } else {
        newUri = "ws:";
    }
    newUri += "//" + loc.host;
    return newUri;
  }();

  var API_ROOT = '/api';

  var getServicesURL = function() {
    return API_ROOT + '/services/';
  };

  var getServiceURL = function(serviceName) {
    return getServicesURL() + serviceName + '/';
  };

  var getPipelinesURL = function(serviceName) {
    return getServiceURL(serviceName) + 'pipelines/';
  };

  var getPipelineURL = function(serviceName, pipelineName) {
    return getPipelinesURL(serviceName) + pipelineName + '/';
  };

  var getRunsURL = function(serviceName, pipelineName) {
    return getPipelineURL(serviceName, pipelineName) + 'runs/';
  };

  var getRunURL = function(serviceName, pipelineName, runId) {
    return getRunsURL(serviceName, pipelineName) + runId + '/';
  };

  var getJobsURL = function(serviceName, pipelineName, runId) {
    return getRunURL(serviceName, pipelineName, runId) + 'jobs/';
  };

  Mettle.getServices = function (cb) {
    $.getJSON(getServicesURL(), cb);
  };

  Mettle.getPipelines = function (serviceName, cb) {
    $.getJSON(getPipelinesURL(serviceName), cb);
  };

  Mettle.getRuns = function (serviceName, pipelineName, cb) {
    $.getJSON(getRunsURL(serviceName, pipelineName), cb);
  };

  Mettle.getRun = function (serviceName, pipelineName, runId, cb) {
    $.getJSON(getRunURL(serviceName, pipelineName, runId), cb);
  };

  Mettle.getRunStream = function (serviceName, pipelineName, runId) {
    return new ReconnectingWebSocket(getRunURL(serviceName, pipelineName, runId));
  };

  Mettle.getJobs = function (serviceName, pipelineName, runId, cb) {
    $.getJSON(getJobsURL(serviceName, pipelineName, runId), cb);
  };

  Mettle.getJobsStream = function (serviceName, pipelineName, runId) {
    return new ReconnectingWebSocket(WSPREFIX + getJobsURL(serviceName, pipelineName, runId));
  };

})(window);
