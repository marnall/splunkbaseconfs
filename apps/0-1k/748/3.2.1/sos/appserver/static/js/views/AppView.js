define([
    "jquery",
    "underscore",
    "backbone",
    "d3",
    "xml2json",
    "app/utils/formatXML",
    "app/models/Module",
    "app/models/View",
    "app/collections/Modules",
    "text!app/templates/App.html",
    "text!app/templates/RemoveGroupModal.html",
    "app/views/NavbarView",
    "app/views/ToolbarView",
    "app/views/WorkspaceView",
    "app/views/PatternView",
    "app/views/ViewAttrView",
    "app/views/GroupListView",
    "app/views/NotificationsView",
    "app/views/NotificationView"
], function(
    $,
    _,
    Backbone,
    d3,
    X2JS,
    formatXML,
    Module,
    View,
    Modules,
    Template,
    RemoveGroupModalTemplate,
    NavbarView,
    ToolbarView,
    WorkspaceView,
    PatternView,
    ViewAttrView,
    GroupListView,
    NotificationsView,
    NotificationView    
) {
    return Backbone.View.extend({
        el: "#appContainer",
        initialize: function() {
            this.app = this.options.app;
            this.d3 = {};
            this.x2js = new X2JS();
            this.view_json = {};
            this.viewModel = new View();
            this.app.roots = this.viewModel.get("modules");

            // subviews
            this.navbarView = new NavbarView({app: this.app});
            this.toolbarView = new ToolbarView({app: this.app});
            this.viewAttrView = new ViewAttrView({app: this.app, model: this.viewModel});
            this.notificationsView = new NotificationsView({app: this.app});

            // events
            var that = this;
            this.app.mediator.subscribe("navbar:createNewView", function(view_name, targetApp, read_perms, write_perms, create) {
                that.createNewView(view_name, targetApp, read_perms, write_perms, create);
            });
            this.app.mediator.subscribe("navbar:openExistingView", function(view_name, targetApp) {
                that.openExistingView(view_name, targetApp);
            });
            this.app.mediator.subscribe("navbar:saveAsCurrentView", _.bind(this.saveAsCurrentView, this));
            this.app.mediator.subscribe("toolbar:shiftSVG", function(left) {
                that.shiftSVG(left);
            });
            this.app.mediator.subscribe("navbar:saveAsNewView", function(view_name, targetApp, read_perms, write_perms, create) {
                that.saveAsNewView(view_name, targetApp, read_perms, write_perms, create);
            });
            this.app.mediator.subscribe("workspace:saveGroup", function(name, data) {
                that.addNewGroup(name, data, "create");
            });
            this.app.mediator.subscribe("workspace:overwriteGroup", function(name, data) {
                that.overwriteGroup(name, data);
            });
            this.app.mediator.subscribe("groupList:addGroup", function(data) {
                that.addGroup(data);
            });
            this.app.mediator.subscribe("groupList:editGroup", function(groupView, data) {
                that.editGroup(groupView);
            });
            this.app.mediator.subscribe("groupList:removeGroup", function(view) {
                that.$removeGroupModal.modal("show");
                that.app.patternToDelete = view;
            });
            this.app.mediator.subscribe("pattern:saveGroup", function(groupObject) {
                that.setPatternsJSON(groupObject.name, groupObject.data);
            });
        },
        render: function() {
            this.$el.html(_.template(Template));

            this.workspaceView = new WorkspaceView({app: this.app});
            this.patternView = new PatternView({app: this.app});
            this.patternView.hide();

            this.$el.append(this.notificationsView.render().el);
            this.$el.append(this.navbarView.render().el);
            this.$el.append(this.toolbarView.render().el);
            this.$el.append(this.viewAttrView.render().el);


            this.$removeGroupModal = $(RemoveGroupModalTemplate).appendTo('#modals');
            this.$removeGroupModal.find(".removeGroup").click(_.bind(this.deletePatternsJSON, this));

            // position svg's
            this.positionSVG(0, this.toolbarView.$el.offset().top);

            // get and render groups
            this.getPatternsJSON();

            return this;
        },
        positionSVG: function(left, top) {
            $("svg").css("left", left).css("top", top);
        },
        shiftSVG: function(left) {
            $("svg").css("left", left);
        },
        events: {
            "click .navItem#pattern": "togglePattern",
            "click .navItem#workspace": "toggleWorkspace",
            "click #viewName": "openViewAttrModal",
            "click #cancelGroup": "toggleWorkspace",
            "click .cleanUp": "cleanUp",
            "click .close[data-dismiss='modal']": "closeModal"
        },
        togglePattern: function() {
            this.app.view = "pattern";
            this.app.parent = false;
            this.patternView.show();
            this.workspaceView.hide();

            this.navbarView.togglePattern();
            this.toolbarView.togglePattern();
        },
        toggleWorkspace: function() {
            this.app.view = "workspace";
            this.app.parent = false;
            this.workspaceView.show();
            this.patternView.hide();
            this.patternView.clear();

            this.navbarView.toggleWorkspace();
            this.toolbarView.toggleWorkspace();

            var tempPrev = window.location.pathname;
            window.history.pushState({}, "", this.app.prevURL);
            this.app.prevURL = tempPrev;
        },
        openViewAttrModal: function(e) {
            if (!$(e.target).hasClass("disabled")) {
                this.viewAttrView.open();
            }
        },
        cleanUp: function() {
            if (this.app.view === "pattern") {
                this.patternView.cleanUp();
            } else if (this.app.view === "workspace") {
                this.workspaceView.cleanUp();
            }
        },
        closeModal: function(e) {
            console.log($(e.target).parents(".modal"));
            var $parent = $(e.target).parents(".modal");
            $parent.modal("hide");
        },
        /* mediator functions passed up from toolbar/navbar */
        createNewView: function(view_name, targetApp, read_perms, write_perms, create) {
            this.clearWorkspace();
            this.getNewViewJSON(view_name, targetApp, read_perms, write_perms, create);
            this.saveAsCurrentView();
        },
        openExistingView: function(view_name, targetApp) {
            this.clearWorkspace();
            this.getExistingViewJSON(view_name, targetApp);
            this.$(".navItem#preview")
                .removeClass("disabled")
                    .attr(
                        'view_name',
                         view_name
                    )
                    .attr(
                        'href', 
                         this.getPreviewUrl(
                            targetApp,
                            view_name
                        )
                    );

        },
        saveAsCurrentView: function() {
            this.view_json._fromXML.view = this.viewAttrView.model.toSplunk();
            this.setViewXML({create: this.view_json.create}, function(response) {
                this.$(".navItem#preview")
                    .removeClass("disabled")
                    .attr(
                        'view_name',
                         this.view_json.name
                    )
                    .attr(
                        'href', 
                         this.getPreviewUrl(
                            this.view_json.acl.app, 
                            this.view_json.name
                        )
                    );
            }.bind(this));
        },
        getPreviewUrl: function(app, view) {
            return '/app/' + app + '/' + view;
        },
        saveAsNewView: function(view_name, targetApp, read_perms, write_perms, create) {
            if (this.view_json.content === undefined) {
                this.getNewViewJSON(view_name, targetApp, read_perms, write_perms);
            }
            this.view_json.name = view_name;
            this.view_json.content.name = view_name;
            this.view_json.acl.app = targetApp;
            this.view_json.content["eai:appName"] = targetApp;
            this.view_json.acl.perms.read = read_perms;
            this.view_json.acl.perms.write = write_perms;
            this.view_json.create = create;

            var that = this;
            this.view_json._fromXML.view = this.viewAttrView.model.toSplunk();
            this.setViewXML({create: this.view_json.create}, function(response) {
                // TODO: Switch out underlying workspace view with new one
                // TODO: Error handling
                that.$(".navItem#preview")
                    .removeClass("disabled")
                    .attr(
                        'view_name',
                        this.view_json.name
                    )
                    .attr(
                        'href', 
                         this.getPreviewUrl(
                            this.view_json.acl.app, 
                            this.view_json.name
                        )
                    );
            }.bind(this));
        },
        addNewGroup: function(name, data, action, isDefault) {
            console.log(name, isDefault, typeof isDefault);
            var groupView = new GroupListView({
                app: this.app, 
                name: name, 
                data: data,
                isDefault: isDefault
            });
            this.toolbarView.$groupList.append(groupView.render().el);
            this.app.patterns[name] = groupView;

            if (action === "create") {
                this.setPatternsJSON(name, data, "_new");
            }
        },
        overwriteGroup: function(name, data) {
            var groupView = this.app.patterns[name];
            groupView.model.set("data", data);

            this.setPatternsJSON(name, data);
        },
        addGroup: function(data) {
            this.workspaceView.addGroup(data);
        },
        editGroup: function(groupView) {

            this.togglePattern();

            var app = window.location.pathname.split('/')[4],
                pattern = groupView.name;

            /* if a user went directly to editing a pattern
             upon leaving editGroup, the URL should still switch to a render
             */
            if ($("body").attr('s:pattern')) {
                this.app.prevURL = "/custom/splunk_app_shared_components/visual_editor/-/render";
            } else {
                this.app.prevURL = window.location.pathname;
            }

            window.history.pushState({app: app, name: pattern}, "", 
                "/custom/splunk_app_shared_components/visual_editor/"
                + app + "/pattern/" + pattern);
        },
        /* functions that hit splunk */
        getNewViewJSON: function(view_name, targetApp, read_perms, write_perms, create) {
            var that = this;
            $.ajax({
                dataType: "json",
                url: "/en-US/splunkd/servicesNS/admin/"+targetApp+"/data/ui/views/_new",
                data: {'output_mode': 'json'},
                async: false,
                success: function(data) {
                    that.$("#newViewModal").modal("hide");
                    that.view_json = data.entry[0];
                    that.view_json.name = view_name;
                    that.view_json.content.name = view_name;
                    that.view_json.acl.app = targetApp;
                    that.view_json.content["eai:appName"] = targetApp;
                    that.view_json.acl.perms.read = read_perms;
                    that.view_json.acl.perms.write = write_perms;
                    that.view_json.create = create;

                    that.view_json._fromXML = {
                        view: {}
                    };

                    that.populateViewModal(view_name, targetApp);

                    that.app.spinner.stop();
                }
            });
        },
        getExistingViewJSON: function(view_name, targetApp) {

            var that = this;
            $.ajax({
                dataType: "json",
                url: "/en-US/splunkd/servicesNS/admin/"+targetApp+"/data/ui/views/" + view_name,
                data: {'output_mode': 'json'},
                async: false,
                success: function(data) {
                    that.view_json = data.entry[0];
                    that.prepViewContent();
                    that.view_json._fromXML = that.x2js.xml_str2json(that.view_json.content['eai:data']);
                    that.view_json.create = false;
                    that.populateViewModal(view_name, targetApp);

                    if (!that.view_json._fromXML.view.module_asArray) {
                        that.view_json._fromXML.view.module = [];
                    } else {
                        that.workspaceView.renderExistingView(that.view_json);            
                    }

                    that.app.spinner.stop();
                }
            });
        },
        setViewXML: function(options, callback) {
            
            // TODO: add new view to list of views
            // TODO: error checking for if a view already exists
            var view_name = this.view_json.name,
                view_data = this.x2js.json2xml_str(this.view_json._fromXML),
                targetApp = this.view_json.content["eai:appName"],
                perms = this.view_json.acl.perms,
                csrf_key = $('input[name=splunk_form_key]').val(),
                create = options && options.create,
                url = Splunk.util.make_url("/custom/splunk_app_shared_components/visual_editor/" + 
                    targetApp + "/" + ((create) ? "create_view" : "update_view")),
                that = this;

            view_data = formatXML(view_data);

            // TODO: Add error handler
            $.ajax({
                type: "POST",
                url: url,
                headers: {
                    'X-Splunk-Form-Key': csrf_key
                },
                data: {
                    'name': view_name,
                    'data': view_data,
                    'read_perms': perms.read,
                    'write_perms': perms.write
                },
                success: function(data) {
                    var message, notification, type;
                    if (data.success === "true") {
                        type = "success";
                        if (create) {
                            that.view_json.create = false;
                            that.app.mediator.publish("app:setViewXML:success", view_name, targetApp);
                            message = "success: created new view <strong>" + view_name + "</strong> in app <strong>" + targetApp + "</strong>";
                        } else {
                            message = "success: updated view <strong>" + view_name + "</strong> in app <strong>" + targetApp + "</strong>";
                        }

                        if (_.isFunction(callback)) {
                            callback(data);  
                        }

                        that.app.prevURL = window.location.pathname;
                        window.history.pushState({app: targetApp, view: view_name}, "", 
                            "/custom/splunk_app_shared_components/visual_editor/"
                            + targetApp + "/render/" + view_name);
                    } else if (data.success === "false") {
                        type = "error";
                        message = "error saving view <strong>" + view_name + "</strong> in app <strong>" + targetApp + "</strong>: " + data.error;
                    }
                    that.$("#saveAsModal").modal("hide");
                    notification = new NotificationView({app: that.app, message: message, closeable: true, type: type});
                    that.app.mediator.publish("add:notifications", notification);
                    
                    that.app.spinner.stop();
                    
                }
            });
        },
        getPatternsJSON: function() {
            var that = this;
            $.get("/en-US/custom/splunk_app_shared_components/visual_editor/splunk_app_shared_components/get_groups", function(data) {
                _.each(data, function(pattern) {
                    that.addNewGroup(pattern.name, $.parseJSON(pattern.data), "", pattern.isDefault);
                });

                that.app.mediator.publish("app:getPatternsJSON:finished");
            });


        },
        setPatternsJSON: function(name, data, isNew) {
            var csrf_key = $('input[name=splunk_form_key]').val(),
                that = this;
                data = JSON.stringify(data);
            $.ajax({
                type: "POST",
                url: "/en-US/custom/splunk_app_shared_components/visual_editor/splunk_app_shared_components/save_group",
                data: {
                    'key': isNew, 
                    'name': name, 
                    'data': data},
                headers: {
                    'X-Splunk-Form-Key': csrf_key
                },
                error: function(resp) {
                    console.log(name, data);
                    var message = "error saving pattern <strong>" + name + "</strong>",
                        notification = new NotificationView({app: that.app, message: message, closeable: true, type: "error"});
                    that.app.mediator.publish("add:notifications", notification);
                },
                success: function(resp) {
                    //TODO: success message
                    var message = "success saving pattern <strong>" + name + "</strong>",
                        notification = new NotificationView({app: that.app, message: message, closeable: true, type: "success"});
                    that.app.mediator.publish("add:notifications", notification);
                    that.toggleWorkspace();
                }
            });
        },
        /*
        deletePatternsJSON: delete the pattern that has been passed.
        view: an instance of GroupListView.
        */
        deletePatternsJSON: function() {
            var view = this.app.patternToDelete,
                name = view.name,
                csrf_key = $('input[name=splunk_form_key]').val(),
                that = this;

            this.$removeGroupModal.modal("hide");
            $.ajax({
                type: "POST",
                url: "/en-US/custom/splunk_app_shared_components/visual_editor/splunk_app_shared_components/remove_group",
                data: {
                    'name': name
                },
                headers: {
                    'X-Splunk-Form-Key': csrf_key
                },
                error: function(resp) {
                    var message = "error deleting pattern <strong>" + name + "</strong>",
                        notification = new NotificationView({app: that.app, message: message, closeable: true, type: "error"});
                    that.app.mediator.publish("add:notifications", notification);

                    that.app.patternToDelete = undefined;
                },
                success: function(resp) {
                    var message, notification, type;
                    if (resp.success === "true") {
                        message = "success deleting pattern <strong>" + name + "</strong>";
                        type = "success";

                        // make sure there's no more references to this pattern.
                        delete that.app.patterns[name];
                        // remove the pattern name from the pattern list
                        view.remove();
                    } else {
                        message = "error deleting pattern <strong>" + name + "</strong>";
                        type = "error";
                    }
                    notification = new NotificationView({app: that.app, message: message, closeable: true, type: type});
                    that.app.mediator.publish("add:notifications", notification);
                    
                    that.app.patternToDelete = undefined;
                }
            });
        },
        /* helper functions */
        clearWorkspace: function() {
            // TODO: don't empty the cancelChild layer
            this.workspaceView.clear();
            this.notificationsView.clear();
            this.$("#editList").empty();
            this.view_json = {};
            this.viewModel.clear();
        },
        prepViewContent: function() {
            this.view_json.content['eai:data'] = $.trim(this.view_json.content['eai:data']);

            // when there are comments
            if(this.view_json.content['eai:data'][1] === "!"){
                var commentRe = /<\!--[^]*?([^]*?)[^]*?-->/img,
                    endRe = /-->/img;
                if(this.view_json.content['eai:data'].search(commentRe) > -1){
                    var res = this.view_json.content['eai:data'].search(endRe);
                    this.view_json.content['eai:data'] = this.view_json.content['eai:data'].slice(res+3, this.view_json.content['eai:data'].length);
                }
            }
        },
        populateViewModal: function(view_name, targetApp) {
            // TODO
            var label,
                attrs = {},
                that = this;
            $.each(this.view_json._fromXML.view, function(key, val) {
                if (key.match(/^_[^_].*/)) {
                    attrs[key] = val;
                } else if (key === "label") {
                    label = val;
                } else if (key === "#comment" || key === "#comment_asArray") {
                    delete that.view_json._fromXML.view[key];
                }
            });

            this.viewModel.set({label: label, attrs: attrs, view_name: view_name, targetApp: targetApp});
        }
    });
});
