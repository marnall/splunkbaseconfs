Splunk.Module.sosnodes = $.klass(Splunk.Module.DispatchingModule, {

    DEFAULT_GRADIENT_LIST: [
        ['node_up_fill', '#F8FBEF', '#EBEEE2'],
        ['node_down_fill', '#111111', '#111111'],
        ['node_stroke', '#E0E0E0', '#A3A3A3'],
        ['rack_fwd', '#E87722', '#E87722'],
        ['rack_idx', '#005f86', '#005f86'],
        ['rack_sh', '#73a550', '#73a550'],
        ['service_stroke', '#BDBEB9', '#9C9D98'],
        ['rack_fill', '#f1f1f1', '#e1e1e1'],
        ['rack_stroke', '#D4D4D4', '#D4D4D4']
    ],

    SERVICE_MAP: {
        'namenode': 'NN', 
        'jobtracker': 'JT',
        'balancer': 'BL', 
        'secondarynamenode': 'SN'
    },
 
    initialize: function($super, container) {
        $super(container);

        // internal search things
        this.getInternalResultsRetryCounter = 0;
        this.getInternalResultsXHRObject = null;

        this.drilldown_name = this.getParam("drilldown_name") || "host";
        this.heatmap_lookback = this.getParam("heatmap_lookback");
        this.heatmap_namespace = this.getParam("heatmap_namespace");
        this.radius_factor = this.getParam("radius_factor") || 8;
        this.node_radius = this.getParam("node_radius") || this.autoNodeRadius(this.radius_factor);
        this.text_fill = this.getParam("text_fill") || "#888B86";
        this.rack_height = d3.round(this.node_radius*1.3, 1);
         
        this.clicked = null;
        this.data = null;
        this.downed = {};
        this.heatmap_config = null;
        this.heatmap_enabled = false;
        this.internal_search = null;
        this.racks = null;
        this.render_complete = false;

        // initialize the canvas
        this.svg = d3.select(container).append("svg:svg")
            .attr("width", "100%")
            .attr("height", "100%");

        // initialize the master group
        this.master_group = this.svg.append("svg:g")
            .attr("width", "100%")
            .attr("height", "100%"); 

        // initialize the rack container
        this.racks = this.master_group.append("svg:g")
            .attr("class", "rack_container");

        // apply the fill and stroke gradients
        this.applyGradients();

        // apply the drop shadow filters
        this.applyFilters();

        // bind body resize to callback
        $(window).resize(this.onWindowResize.bind(this));
    },

    /*
     * override 
     * receive charting and heatmap options
     */
    onContextChange: function($super) {
        var context = this.getContext(),
            chart = context.get("chart") || null,
            heatmap = context.get(this.heatmap_namespace) || null,
            radius = parseInt(this.node_radius),
            search = context.get('search'),
            job = search['job'];

        // look for node_size in context.chart
        if (chart !== null 
          && chart['node_size'] !== undefined
          && chart['node_size'] !== null) { 
            radius = parseInt(chart['node_size']);
        }

        // reset the node width/height if changed
        if (this.node_radius !== radius) {
            this.node_radius = radius;
            this.rack_height = d3.round(this.node_radius*1.3, 1);

            // if we have rendered, let's re-render
            if (this.render_complete === true) {
                this.destroyRacks();
                this.appendRacks();
            }
        }

        // cancel and abandon internal heatmap search
        if (this.internal_search !== null && this.internal_search.job !== null
          && this.internal_search.job.getSID() !== null) {
            this.internal_search.job.cancel();
            this.internal_search.abandonJob();
            this.abortGetInternalResults();
        }

        // look for heatmap in the context
        if (heatmap !== undefined && heatmap !== null) {
            this.heatmap_enabled = true;
            this.heatmap_config = heatmap;
            this.dispatchInternalSearch();
        } else {
            this.heatmap_enabled = false;
            this.heatmap_config = null;
        } 

        $super();
    },
    
    /*
     * abort the internal get results call
     */
    abortGetInternalResults: function() {
        if (this.getInternalResultsXHRObject && this.getInternalResultsXHRObject.readyState < 4) {
            this.getInternalResultsXHRObject.abort();
        }
    },

    /*
     * handle dispatch of internal heatmap search
     */
    dispatchInternalSearch: function() {
        this.internal_search = new Splunk.Search(this.heatmap_config['search'],
                                   new Splunk.TimeRange(this.heatmap_lookback, 'rt')
                               );
        this.internal_search.dispatchJob(
            this.onInternalDispatchSuccess.bind(this), this.onInternalDispatchFailure.bind(this)
        );
        this.internal_search.job.setAsAutoCancellable(true);
    },

    /* 
     * the default implementation freaks out in the case that the internal sid != context sid
     * so let's use our own function to deal with getting internal results from same controller
     */ 
    getInternalResults: function() {
        if (this.getInternalResultsXHRObject) {
            if (this.getInternalResultsXHRObject.readyState < 4) {
                var job = this.internal_search.job;
                if (job && !job.isDone() && this.getInternalResultsRetryCounter < this.getResultsRetryPolicy) {
                    this.getInternalResultsRetryCounter++;
                    return;
                } else {
                    this.abortGetInternalResults(); 
                    this.resetInternalXHRStatus();
                }
            } else {
                this.resetInternalXHRStatus();
            }
        }
        var params = this.getInternalResultParams();
        this._previousResultParams = $.extend(true, {}, params);
        if (Splunk._testHarnessMode) {
            return false;
        }
        var resultUrl = this.getResultURL(params);
        var callingModule = this.moduleType;
        this.getInternalResultsXHRObject = $.ajax({
            type: "GET",
            cache: ($.browser.msie ? false : true),
            url: resultUrl,
            beforeSend: function(xhr) {
                xhr.setRequestHeader('X-Splunk-Module', callingModule);
            },
            success: function(htmlFragment, textStatus, xhr) {
                if (xhr.status==0) {
                    return;
                }
                this.renderInternalResults(htmlFragment);
                this.resetInternalXHRStatus();
            }.bind(this),
            complete: this.getInternalResultsCompleteHandler.bind(this),
            error: this.getInternalResultsErrorHandler.bind(this)
        });
    },

    /*
     * internal get results error handler
     */
    getInternalResultsErrorHandler: function(xhr, textStatus, errorThrown) {
        this.resetInternalXHRStatus();
        if (textStatus == 'abort') {
            this.logger.debug(this.moduleType, '.getInternalResults() aborted');
        } else {
            this.logger.warn(this.moduleType, 
                '.getInternalResults() error; textStatus=' + textStatus + ' errorThrown=' + errorThrown);
        }
    },

    /*
     * internal get results complete handler
     */
    getInternalResultsCompleteHandler: function(xhr, textStatus) {
        this.resetInternalXHRStatus();
    },

    /*
     * callback for internal search failure
     */
    onInternalDispatchFailure: function() {
        console.error('internal search dispatch failed!');
    },

    /*
     * internal job success handler
     */
    onInternalDispatchSuccess: function() {
        $(document).bind('jobProgress', function(event, progJob) {
            if (this.internal_search.job !== null
              && this.internal_search.job.getSearchId() == progJob.getSearchId()) {
                this.onInternalJobProgress(event);
            }
        }.bind(this));
    },

    /*
     * get results for internal search
     */
    onInternalJobProgress: function(event) {
        this.getInternalResults();
    },

    /*
     * reset internal XHR
     */
    resetInternalXHRStatus: function() {
        this.getInternalResultsXHRObject = null;
        this.getInternalResultsRetryCounter = 0;
    },

    /*
     * window resize callback
     */ 
    onWindowResize: function() {
        if (this.render_complete === false) {
            return;
        } else {
            // redraw the racks
            this.destroyRacks();
            this.appendRacks();
        }
    },

    /*
     * destroy all racks
     */
    destroyRacks: function() {
        this.racks.selectAll("g.rack").remove();
    },
 
    /*
     * will guess a node radius based on the document height/width 
     */ 
    autoNodeRadius: function(factor) {
        var p_width = this.container.parent().width();
        return d3.round(p_width/factor);
    },

    /*
     * given [id, color1, color2]
     * append a gradient def to the master group
     */
    appendGradientDef: function(l) {
        var tmp = this.master_group.append("svg:defs")
            .append("svg:linearGradient")
            .attr("id", l[0])
            .attr("x1", "0%")
            .attr("y1", "0%")
            .attr("x2", "0%")
            .attr("y2", "100%")
            .attr("spreadMethod", "pad");

        tmp.append("svg:stop")
            .attr("offset", "0%")
            .attr("stop-color", l[1])
            .attr("stop-opacity", 1);

        tmp.append("svg:stop")
            .attr("offset", "100%")
            .attr("stop-color", l[2])
            .attr("stop-opacity", 1);
    },

    /*
     * appl the default filter defs
     */
    applyFilters: function() {
        var dropShadowFilter = this.master_group.select("defs")
            .append('svg:filter')
            .attr('id', 'dropShadow');
        dropShadowFilter.append('svg:feOffset')
            .attr('in', 'SourceGraphic')
            .attr('dx', 0)
            .attr('dy', 1)
            .attr('result', 'offset');
        dropShadowFilter.append('svg:feColorMatrix')
            .attr('in', 'offset')
            .attr('type', 'saturate')
            .attr('values', 0.4)
            .attr('result', 'coloroffset');
        dropShadowFilter.append('svg:feGaussianBlur')
            .attr('in', 'coloroffset')
            .attr('stdDeviation', 1.3)
            .attr('result', 'blur');
        dropShadowFilter.append('svg:feBlend')
            .attr('in', 'SourceGraphic')
            .attr('in2', 'blur')
            .attr('mode', 'normal');
    },

    /*
     * apply the default gradient defs
     */  
    applyGradients: function() {
        for (var i=0; i < this.DEFAULT_GRADIENT_LIST.length; i++) {
            this.appendGradientDef(this.DEFAULT_GRADIENT_LIST[i]);
        }
    },

    /*
     *  Given an object that reflects one or more racks, each containing
     *  a series of hosts which contain a list of service names, append
     *  the given hosts to the containing rack element
     */
    appendHosts: function(rack_obj, racks, downed) {
        var pad = d3.round(this.node_radius*.15, 1),
            pad_radius = d3.round(this.node_radius+pad, 1),
            rack_height = this.rack_height,
            ypad = d3.round(rack_height*.2, 1),
            that = this,
            xpos = pad, 
            ypos = d3.round(ypad*1.6, 1),
            row_count = 1,
            total_height = ypad,
            j = 0,
            classes, hosts, rack, services, 
            max_hosts, max_width, max_height,
            host_count, rows, i, k, w, x, y, z; 

        for (k=0; k<racks.length; k++) {

            host_count = 0;
            rack = racks[k];

            // get host list
	    hosts = this.arrFromVal(rack_obj[rack]);

	    // dimensions are calculated based on host count and parent container size
	    max_hosts = Math.floor(parseInt(this.container.parent().width() - pad*6)/pad_radius); 
            rows = Math.ceil(hosts.length/max_hosts);
            max_width = d3.round((max_hosts*pad_radius) + pad);
            max_height = d3.round((rows*rack_height));

            // keep track of the total height for resizing later
            total_height += max_height;
            
            // reset rack grouping dimensions
            this.racks.select('g[rack_id="' + rack + '"]')
                .attr("width", function(d) {
                    w = Math.min(d3.select(this).select("rect.rack").attr("width"), d3.round(max_width));
                    return w;
                })
                .attr("height", d3.round(max_height))
                .attr("y", function() {
                    y = parseInt(d3.select(this).attr("y"));
                    z = 0;
                    if (k > 0) {
                        z = d3.round((row_count-1)*rack_height);
                    }
                    y += parseInt(z);
                    return y;
                })
                .each(function() {
                    var tmp = d3.select(this); 
                    tmp.select("rect.rack")
                        .attr("width", w)
                        .attr("y", function() {
                            y = parseInt(d3.select(this).attr("y"));
                            z = 0;
                            if (k > 0) {
                                z = d3.round((row_count-1)*rack_height);
                            }
                            y += parseInt(z);
                            return y;
                        })
                        .attr("height", max_height);
                    tmp.select("text.rack_text")
                        .attr("y", parseInt(y-2));
                })

            // create the grouping, rect, and title
            this.racks.select('g[rack_id="' + rack + '"]')
                .selectAll("g.node")
                .data(hosts)
              .enter()
                .append("g")
                .attr("class", "node")
                .attr("node_id", function(d) { return d; })
                .attr("y", ypos)
                .attr("x", xpos)
                .attr("class", function(d) {
                    classes = that.getClasses(rack_obj[rack][d]);
                    classes.push('node');
                    return classes.join(' ');
                })
                .on("click", function() {
                    that.onNodeClick(this);
                })
                .each(function(selection) {
                    services = rack_obj[rack][selection];
                    d3.select(this).append("rect")
                        .attr("class", "node")
                        .attr("fill", function(s) {
                            if (downed.hasOwnProperty(s)) {
                                return "url(#node_down_fill)"
                            } else {
                               if (classes[0].toString() === "SH") {
                                  return "url(#rack_sh)"
                               } else if (classes[0].toString() === "IDX"){
                                  return "url(#rack_idx)"
                               } else if (classes[0].toString() === "FWD"){
                                  return "url(#rack_fwd)"
                               } else {
                                  return "url(#node_up_fill)"
                               }
                            }
                        })
                        .attr("stroke", "url(#node_stroke)")
                        .attr("stroke-width", 1)
                        .attr("filter", "url(#dropShadow)")
                        .attr("width", that.node_radius)
                        .attr("height", that.node_radius)
                        .attr("y", function() {
                            if (host_count >= max_hosts) {
                                ypos = ypos+rack_height;
                            } 
                            return ypos;
                        })
                        .attr("x", function() {
                            host_count++;
                            if (host_count > max_hosts) {
                                xpos = pad;
                                row_count++;
                                host_count = 1;
                            } 
                            return xpos;
                        })
                        .attr("rx", 7)
                        .attr("ry", 7)
                        .append("title")
                           .text(function(d) { return d; } );
                   d3.select(this).append("svg:image")
                       .attr("xlink:href", function(s) {
                          if (classes[0].toString() === "SH") {
                            return  "/static/app/sos/images/Searchhead_green.png"
                          } else if (classes[0].toString() === "IDX"){
                            return "/static/app/sos/images/Indexer_blue.png"
                          } else if (classes[0].toString() === "FWD"){
                            return "/static/app/sos/images/Forwarder_orange.png"
                          }
                       })
                       .attr("width", that.node_radius)
                       .attr("height", that.node_radius)
                       .attr("y", ypos)
                       .attr("x", xpos)
                       .attr("rx", 7)
                       .attr("ry", 7)
                       .attr("preserveAspectRatio", "none")
                       .append("title")
                          .text(function(d) { return d; } );
                    that.appendServices(this, services, xpos, ypos);
                    if (that.clicked === selection) {
                        that.toggleClicked(d3.select(this));
                    }
                    xpos += pad_radius;
                });
            // offset for next rack
            xpos = pad;
            ypos += rack_height + ypad;
        }
 
        // resize canvas 
        this.svg.attr("width", max_width);
        this.svg.attr("height", d3.round(total_height+(ypad*racks.length)));

        // resize container
        this.container.width(max_width);
        this.container.height(d3.round(total_height+(ypad*racks.length)));

        // trigger resize in case anyone outside of us cares about our size
        this.container.trigger('resize');
    },

    /*
     * Given an object full of racks, append each rack to the rack 
     * container and then make each rack draw its own nodes
     */ 
    appendRacks: function() {
        var downed = this.data['downed'],
            rack_obj = this.data['racks'],
            racks = this.arrFromVal(rack_obj),
            that = this,
            pad = d3.round(this.node_radius*.15, 1),
            pad_radius = d3.round(this.node_radius+pad, 1),
            rack_height = this.rack_height,
            ypad = d3.round(rack_height*.2, 1),
            xpos = 0, 
            ypos = ypad,
            i = 0,
            j = 0,
            rack_dim, y, z;

        this.downed = downed;
        this.render_complete = false;

        // create racks 
        this.racks.selectAll("g.rack")
            .data(racks)
          .enter()
            // individual rack grouping
            .append("g")
              .attr("rack_id", function(d) { return d; })
              .attr("class", "rack")
              .attr("x", xpos)
              .attr("y", function() {
                  y = d3.round(ypos+(i *(rack_height+ypad)), 1);
                  i++;
                  return y;
              })
              // rack labels
              .each(function(d) {
                  d3.select(this)
                      .append("text")
                      .attr("fill", "grey")
                      .attr("x", 10)
                      .attr("y", function() {
                          z = d3.round(ypos+(j*(rack_height+ypad)), 1)-2;
                          j++;
                          return z;
                      })
                      .attr("class", "rack_text")
                      .style("font-size", that.node_radius*.15+ 'px')
                      .text(function(d) { return d; });
              })
              // shaded rack container
              .append("rect")
                .attr("fill", "url(#rack_fill)")
                .attr("stroke", "url(#rack_stroke)")
                .attr("strokewidth", 1)
                .attr("x", xpos)
                .attr("y", function() { 
                    y = ypos; 
                    ypos += d3.round(rack_height+ypad, 1); 
                    return y; 
                })
                .attr("width", function(d) {
                    return d3.round((pad_radius*that.arrFromVal(rack_obj[d]).length)+pad, 1);
                })
                .attr("height", rack_height)
                .attr("rx", 6)
                .attr("ry", 6)
                .attr("class", "rack");

        // append a rack's host to the given rack element
        this.appendHosts(rack_obj, racks, downed);
   
        this.render_complete = true;
    },

    /*
     * given a node grouping 's' and coordinates
     * append decoractions for any known services
     * append service status decorations  
     */ 
    appendServices: function(s, services, xpos, ypos) {
        var selection = d3.select(s),
            height = d3.round(this.node_radius*.35, 1),
            width = height,
            half = parseInt(height/2),
            third = parseInt(height/3),
            pad = d3.round(this.node_radius * .13, 1),
            text_fill = this.text_fill,
            service_down = false,
            x = xpos,
            y = ypos,
            j = 0,
            cls, fill, i, stat;
        
        for (i=0; i < services.length; i++) { 

            // get the class and status
            for (cls in services[i]) {
                stat = parseInt(services[i][cls]);
                break;
            }

            if (cls in this.SERVICE_MAP) {

                // service decoration placement
                if (j === 0) {
                    x += pad;
                    y += pad;
                } else if (j === 1) {
                    x += pad*3;
                } else if (j == 2) {
                    x -= pad*3;
                    y += pad*3;
                } 

                // service decoration counter
                j++;

                // service decoration container
                selection.append("svg:rect")
                    .attr("fill", function() {
                        if (stat === 0) {
                            return "black";
                        } else {
                            return "transparent";
                        }
                    })
                    .attr("stroke", function() {
                        if (stat === 0) {
                            return "none";
                        } else {
                            return "url(#service_stroke)";
                        }
                    })
                    .attr("class", "service")
                    .attr("width", width)
                    .attr("height", height)
                    .attr("x", x)
                    .attr("y", y)
                    .attr("rx", 2)
                    .attr("ry", 2);

                // service decoration text
                selection.append("text")
                    .attr("x", d3.round(x + width * .15, 1))
                    .attr("y", d3.round(y + height * .70, 1))
                    .style("font-size", width * .5 + 'px')
                    .attr("fill", function() {
                        fill = text_fill;
                        if (stat === 0) {
                            fill = "white";
                        }
                        return fill;
                    })
                    .attr("stroke", function() {
                        if (stat === 0) {
                            return "white";
                        } else {
                            return "none"; 
                        }
                    })
                    .text(this.SERVICE_MAP[cls]);

            }
            // downed service decoration
            if (stat === 0 && service_down === false) {
                xpos += parseInt(pad*4.5);
                ypos += parseInt(pad*4.5);
                selection.append("svg:rect")
                    .attr("height", half)
                    .attr("width", third)
                    .attr("fill", "white")
                    .attr("x", xpos + third)
                    .attr("y", ypos);
                ypos += half;
                selection.append('path')
                   .attr('d', function(d) { 
                       return 'M ' + xpos +' '+ ypos + ' l ' + half +' ' + half +' l '+ half + ' '+ (0-half) + ' z';
                   })
                   .attr("fill", "white");
                service_down = true;
            }
        }
    },

    /*
     * send the sid, endpoint, and internal boolean to the controller
     */
    getResultParams: function($super) {
        var params = $super();

        params['sid'] = this.getContext()
            .get('search')
            .job.getSearchId();
        params['endpoint'] = 'results';
        params['internal'] = false;

        return params;
    },
    
    /*
     * send the internal sid, endpoint, and internal boolean to the controller 
     */
    getInternalResultParams: function() {
        var params = this.getResultParams();

        params['sid'] = this.internal_search.job.getSearchId();
        params['endpoint'] = 'results_preview';
        params['internal'] = true;

        return params;
    },

    /*
     * make a list from the values in object 'o'
     */ 
    arrFromVal: function(o, reverse) {
        var ret = $.map(o, function(v, i) { return i; }).sort();
        reverse=true;
        if (reverse === true) {
            ret.reverse();
        }
        return ret;
    },

    /*
     * given a list of objects
     * return a list containing all the keys 
     */ 
    getClasses: function(l) {
        var classes = [],
            i;
        for (i=0; i < l.length; i++) {
            classes.push(this.arrFromVal(l[i]));
        }
        return classes;
    },

    /*
     * get results
     */ 
    onJobDone: function() {
        this.getResults();
    },
 
    /* 
     * override
     * send over the node name
     */
    getModifiedContext: function() {
        var context = this.getContext(),
            form = context.get("form") || {};
            search = context.get('search');

       
        if (this.clicked !== null) {
            // true is our signal to reset the drilldown
            if (this.clicked === true) {
                form[this.drilldown_name] = null;
                context.set("form", form);
            } else {
                form[this.drilldown_name] = this.clicked;
                context.set("form", form);
                context.set("click", this.moduleId);
            }
        }
        return context;
    },
 
    /*
     * node click callback
     */
    onNodeClick: function(selection) {
        var s = d3.select(selection);
        this.clicked = this.toggleClicked(s);
        this.pushContextToChildren();
    },

    /*
     * override
     * only drilldown if click has occurred
     */
    isReadyForContextPush: function($super) {
        if (this.clicked === null) {
            return Splunk.Module.CANCEL;
        } 
        return Splunk.Module.CONTINUE;
    },

    /*
     * given a clicked g element 's'
     * add or remove class and rect indicating selection via click
     */ 
    toggleClicked: function(s) {
        var rect = s.select("rect"),
            width = rect.attr("width"),
            height = rect.attr("height"),
            xpos = d3.round(rect.attr("x"), 1) + d3.round(width/20, 1),
            ypos = d3.round(rect.attr("y"), 1) + d3.round(height/20, 1),
            clicked = s.attr("node_id");

        if (s.classed("click") === true) {
            // we were previously clicked
            s.classed("click", false);
            s.select("rect.clicked").remove();
            clicked = true;
        } else { 
            // remove any previous click decoration
            this.racks.selectAll("g.rack")
                .selectAll("g.node.click")
                .classed("click", false)
                .select("rect.clicked")
                .remove();

            // add the click class
            s.classed("click", true);

            // add the click decoration
            s.append("rect")
                .attr("class", "clicked")
                .attr("stroke", "#598ECB")
                .attr("stroke-width", 4)
                .attr("fill", "transparent")
                .attr("rx", 6)
                .attr("ry", 6)
                .attr("x", xpos-2)
                .attr("y", ypos-2)
                .attr("height", d3.round(height*.95, 1))
                .attr("width", d3.round(width*.95, 1));
        }
        return clicked;
    },

    /*
     * find the appropriate fill givent the metric and heatmap config 
     */
    getHeatmapFillStroke: function(metric, default_fill, default_stroke) {
       var fill = default_fill,
           met = parseFloat(metric),
           stroke = default_stroke,
           i, low, high, range;

       // traverse the current rangemap looking for the correct fill
       for (i=0; i < this.heatmap_config.rangemap.length ; i++) {
           range = this.heatmap_config.rangemap[i];
           low = range.low || 0;
           high = range.high || Infinity;

           if (low < met && high > met) {
               fill = range.node_fill; 
               stroke = range.stroke_fill;
               break;
           } 
       }

       if (fill === 'default') {
           fill = default_fill;
       }
       if (stroke === 'default') {
           stroke = default_stroke;
       }

       return [fill, stroke];
    },

    /*
     * given a heatmap obj host=metric
     * change the fill and stroke of the node
     */
    updateHeatmap: function(heatmap) {
        var fill_stroke, host, i, node, r, racks;

        // iterate through hosts that we have heatmap metrics for
        for (host in heatmap) {
            node = null;

            // find all the racks
            racks = this.racks.selectAll('g.rack')
                .selectAll('g[node_id="' + host + '"]');

            // find the host amidst all the racks
            for (i=0; i < racks.length; i++) {
               if (racks[i].length > 0) {
                   node = racks[i][0];
                   break;
               }
            }

            if (node !== null) { 
                // get the group's rect that represents the node
                r = d3.select(node).selectAll('rect.node');
                
                // downed always trumps heatmap
                if (this.downed.hasOwnProperty(host) === true) {
                    r.attr('fill', "url(#node_down_fill)");
                } else {
                    // get fill and stroke
                    fill_stroke = this.getHeatmapFillStroke(
                      heatmap[host], 
                      "url(#node_up_fill)",
                      "url(#service_stroke)"
                    );
                    // apply heatmap fill
                    r.attr('fill', fill_stroke[0]); 
                    // apply service decoration stroke
                    d3.select(node)
                      .select('text')
                        .attr('stroke', fill_stroke[1]); 
                }
            }
        } 
    },

    /*
     * render heatmap
     */
    renderInternalResults: function(data) {
        if (data !== null && data !== undefined 
          && data.heatmap !== null && data.heatmap !== undefined) {
            this.updateHeatmap(data.heatmap);
        }
    },

    /*
     * override
     * send valid data to d3
     */ 
    renderResults: function(data) {
        if (data !== undefined && data !== null 
          && data.racks !== null && data !== undefined) {
            this.destroyRacks();
            this.data = data;
            this.appendRacks();
        } else {
            console.error('invalid response from controller');
        }
    }

});
