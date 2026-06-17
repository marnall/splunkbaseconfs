Splunk.Module.FlashParticlesBeta = $.klass(Splunk.Module.FlashWrapper, {


    /* with multiple orthogonal ways in which something can be visible or invisible
     * every mechanism that shows/hides modules has to provide a unique key.
     * We take the following and append the moduleId.
     */
    DRILLDOWN_VISIBILITY_KEY : "FlashChartInteractionValidity",

    PARTICLES_NS: "particles",

    CONTROLS_NS: "controls",

    initialize: function($super, container){
        $super(container);
        this.logger = Splunk.Logger.getLogger("FlashParticlesBeta.js");

        // strings that flash may ask to be localized
        _("Open as image");
        _("Full screen");
        _("Results Error:");
    },

    initializeBridge: function($super) {
        $super();
        this.bridge.addMethod("readProperties", this.readControlsProperties.bind(this));
        this.bridge.addMethod("writeProperties", this.writeControlsProperties.bind(this));
    },

    readControlsProperties: function() {
        return this.readProperties(this.CONTROLS_NS);
    },

    writeControlsProperties: function(properties) {
        this.writeProperties(properties, this.CONTROLS_NS);
    },

    readProperties: function(ns) {
        var properties = {};

        var prefix = ns ? ns + "." : "";
        var prefixLength = prefix.length;
        var params = this._params;
        var paramName;
        var paramValue;

        for (paramName in params) {
            if (!params.hasOwnProperty(paramName))
                continue;

            if (prefix && (paramName.substring(0, prefixLength) != prefix))
                continue;

            paramValue = Splunk.util.trim(params[paramName]);
            if (!paramValue)
                continue;

            paramName = paramName.substring(prefixLength, paramName.length);
            if (!paramName)
                continue;

            properties[paramName] = this.formatSpecialParam(paramName, paramValue);
        }

        return properties;
    },

    writeProperties: function(properties, ns) {
        var params = {};

        var prefix = ns ? ns + "." : "";
        var propertyName;
        var propertyValue;

        for (propertyName in properties) {
            if (!properties.hasOwnProperty(propertyName))
                continue;

            propertyValue = properties[propertyName];
            propertyName = prefix + propertyName;

            params[propertyName] = propertyValue ? propertyValue : "";
        }

        this.setParams(params, { validate: false });
    },


    /**
     * processes select parameter values that flash does not
     */
    formatSpecialParam: function(paramName, paramValue) {
        if (paramName === 'imagePath') {
            return Splunk.util.make_url(paramValue) + '/'; // make_url strips
        }
        return paramValue;
    },


    setParams: function(kv, options) {
        var defaultOptions = {validate: true, isSessionOnly: false};
        var data = {};
        options = $.extend(defaultOptions, options || {});
        for (var k in kv) {
            if (kv.hasOwnProperty(k)) {
                this._params[k] = kv[k];
                if (options.validate && $.inArray(k, this._stickyParamList) == -1) {
                    this.logger.info('setParams - skipping param write: "' + k + '" is not sticky');
                    continue;
                }
                if (!options.isSessionOnly) {
                    var v = kv[k];
                    if (!(typeof(v) == 'string') && !(typeof(v) == 'boolean') && isNaN(v)) {
                        this.logger.debug(
                            'setParams - Cannot persist non-primitive value: key='
                            + k + ' type=' + typeof(v));
                    } else {
                        data[this._buildParamName(k)] = v;
                    }
                }
            }
        }
        if (this.getContext().get("viewStateId")) {
            this.logger.debug('setParam - skipping param write; inside viewstate');
            return;
        }
        if (!options.isSessionOnly) {
            $.ajax({
                type: 'POST',
                url: this._buildParamUri(),
                data: data,
                dataType: 'json',
                success: this._setParamCallback.bind(this),
                error: this._setParamErrorback.bind(this)
            });
        }
    },


    /**
     * TODO: remove this?
     */
    onLoadStatusChange: function($super,statusInt) {
        $super(statusInt);
        if (statusInt == Splunk.util.moduleLoadStates.WAITING_FOR_HIERARCHY) {
            this.hideDescendants(this.DRILLDOWN_VISIBILITY_KEY + "_" + this.moduleId)
        }
    },


    /**
     * We assume that FlashParticlesBeta always require transformed results
     * see comments on this function in DispatchingModule.js for more details.
     */
    requiresTransformedResults: function() {return true;},


    /**
     * need access to events in real-time searches
     */
    onBeforeJobDispatched: function(search) {
        search.setMinimumStatusBuckets(1);
        search.setRequiredFields(["*"]);
    },


    onContextChange: function() {

        if (!this._isBridgeConnected) {
            this.logger.debug("bridge is not connected onContextChange. Exiting. onContextChange will fire onConnect.");
            return;
        }

        var context = this.getContext();
        var search  = context.get("search");

        // if the job is already done there will be no progress events, and right here the jobId assignment
        // will trigger the final render.
        // In order for PageStatus to be notified of these renders, we have to set up a monitor here.
        if (search.job.isDone()) {
            if (!this.renderMonitor) {
                this.renderMonitor = Splunk.Globals['PageStatus'].register(
                    this.moduleType + ' - rendering final data - ' + this.container.attr('id')
                );
            }
        }

        this.callBridgeMethod("setValues", this.readProperties(this.PARTICLES_NS));
        this.callBridgeMethod("setValue", "rootEmitter.jobID", search.job.getSearchId());

        this.update();
    }

});
