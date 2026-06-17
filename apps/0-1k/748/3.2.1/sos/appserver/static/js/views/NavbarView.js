define([
    "jquery",
    "underscore",
    "backbone",
    "bootstrap.modal",
    "text!app/templates/NavBar.html",
    "text!app/templates/NewViewModal.html",
    "text!app/templates/OpenViewModal.html",
    "text!app/templates/SaveAsModal.html",
    "text!app/templates/PreviewModal.html",
    "text!app/templates/PatternNameModal.html",
    "text!app/templates/OverwriteViewModal.html",
    "text!app/templates/ViewsByApp.html",
    "app/models/Group"
], function(
    $,
    _,
    Backbone,
    modal,
    Template,
    NewViewModalTemplate,
    OpenViewModalTemplate,
    SaveAsModalTemplate,
    PreviewModalTemplate,
    PatternNameModalTemplate,
    OverwriteViewModalTemplate,
    ViewsByAppTemplate,
    Group
) {
    return Backbone.View.extend({
        id: "navBar",
        initialize: function() {
            this.app = this.options.app;
            this.openViewModal = _.template(OpenViewModalTemplate);
            this.newViewModal = _.template(NewViewModalTemplate);
            this.saveAsModal = _.template(SaveAsModalTemplate);
            this.previewModal = _.template(PreviewModalTemplate);
            this.patternNameModal = _.template(PatternNameModalTemplate, {name: ""});
            this.overwriteViewModal = _.template(OverwriteViewModalTemplate);
            this.apps = {};

            var that = this;
            this.app.mediator.subscribe("app:setViewXML:success", function(view_name, targetApp) {
                that.appendNewView(view_name, targetApp, that.$openViewModal.find("select"));
            });
            this.app.mediator.subscribe("groupList:editGroup", function(groupView) {
                that.editGroup(groupView);
            });
            // hit splunk:
            $.getJSON("/en-US/splunkd/servicesNS/nobody/-/data/ui/views?count=0&output_mode=json", function(data) {
                var name;
                data.entry = _.sortBy(data.entry, function(entry) {
                    name = entry.name;
                    if(_.isUndefined(that.apps[entry.acl.app])) {
                        that.apps[entry.acl.app] = {name: true};
                    } else {
                        that.apps[entry.acl.app][name] = true;
                    }
                    return entry.acl.app;
                });
                that.splunkData = data;
                that.populateAppNamesList(that.$newViewModal.find("#target_app0"));
                that.populateAppNamesList(that.$saveAsModal.find("#target_app1"));
                that.populateViewsLists(that.$openViewModal.find(".viewsByApp"));

                that.setupEvents();
            });
        },
        render: function() {
            this.$el.html(_.template(Template));
            $("#modals").append(this.newViewModal);
            $("#modals").append(this.openViewModal);
            $("#modals").append(this.saveAsModal);
            $("#modals").append(this.previewModal);
            $("#modals").append(this.patternNameModal);
            $("#modals").append(this.overwriteViewModal);
            this.$newViewModal = $("#modals").find("#newViewModal");
            this.$openViewModal = $("#modals").find("#openViewModal");
            this.$saveAsModal = $("#modals").find("#saveAsModal");
            this.$previewModal = $("#modals").find("#previewModal");
            this.$patternNameModal = $("#modals").find("#patternNameModal");
            this.$overwriteViewModal = $("#modals").find("#overwriteViewModal");

            

            return this;
        },
        setupEvents: function() {
            // modal events
            this.$newViewModal.find(".createView").click(_.bind(this.createNewView, this));
            this.$openViewModal.find(".viewName").click(_.bind(this.openExistingView, this));
            this.$openViewModal.find(".toggleViews").click(_.bind(this.toggleViews, this));
            this.$openViewModal.find(".viewName").mouseover(_.bind(this.mouseoverView, this));
            this.$saveAsModal.find(".saveAsView").click(_.bind(this.saveAsNewView, this));
            this.$patternNameModal.find("#renamePatternName").click(_.bind(this.renamePatternName, this));
            
            this.$openViewModal.on("hidden", _.bind(this.clearIFrame, this));
        },
        setupIFrame: function() {
            // set up the iframe in openViewModal, that gives previews of views.
            var width = this.$openViewModal.find(".modal-body").width(),
                leftWidth = this.$openViewModal.find(".viewsByApp").width(),
                rightWidth = width - leftWidth - 50,
                height = this.$openViewModal.height(),
                topHeight = this.$openViewModal.find(".modal-header").height(),
                rightHeight = height - topHeight - 50;
            this.$openViewModal.find(".previewIframe").width(rightWidth);
            this.$openViewModal.find("iframe").width(rightWidth);
            this.$openViewModal.find("iframe").height(rightHeight);
            this.$openViewModal.find(".modal-body").height(rightHeight);
        },
        clearIFrame: function() {
            this.$openViewModal.find("iframe").attr("src", "");
        },
        events: {
            "click #new": "newView",
            "click #open": "open",
            "click #save": "save",
            "click #saveAs": "saveAs",
            "click #preview": "preview",
            "click #saveGroup": "saveGroup"
        },
        newView: function() {
            this.$newViewModal.modal("show");
        },
        open: function() {
            this.$openViewModal.modal("show");
            this.setupIFrame();
        },
        save: function(e) {
            if (!$(e.target).hasClass("disabled")) {
                this.app.spinner.spin();
                this.app.mediator.publish("navbar:saveAsCurrentView");
            }
        },
        saveAs: function() {
            this.$saveAsModal.modal("show");
        },
        preview: function(e) {
            if (!$(e.target).hasClass("disabled")) {
                var $target = $(e.target),
                    height = $(window).height()*0.85,
                    width  = $(window).width()*0.9;

                e.preventDefault();

                this.$previewModal.width(width)
                    .height(height)
                    .css({
                        'left': '25%',
                        'overflow': 'none',
                        'top': '40%'
                    });

                this.$previewModal.find(".modal-body")
                    .css('max-height', height*0.8);

                this.$previewModal.find(".preview_view_name")
                    .text($target.attr('view_name'));

                this.$previewModal.find("iframe")
                    .attr("width", "100%") 
                    .attr("height", height*0.8)
                    .attr("src", $target.attr("href")); 

                this.$previewModal.modal("show");
            }
        },
        patternName: function() {
            this.$patternNameModal.modal("show");
        },
        editGroup: function(groupView) {
            this.$("#patternName").text(groupView.name);
            this.$patternNameModal.find("input#editPatternName").val(groupView.name);
        },
        saveGroup: function() {
            this.app.mediator.publish("navbar:saveGroup");
        },
        /*
        modal events
        */
        createNewView: function() {
            var view_name = this.$newViewModal.find('input.view_name').val(),
                targetApp = this.$newViewModal.find("select").val(),
                read_perms = this.$newViewModal.find(':checked[name="perms_read"]').map(function() {
                    return this.value;
                }).get(),
                write_perms = this.$newViewModal.find(':checked[name="perms_write"]').map(function() {

                    return this.value;
                }).get(),
                create = true;

            if (view_name && targetApp) {
                if (!this.checkViewExist(this.$newViewModal, view_name, targetApp, read_perms, write_perms)) {  
                // fill navbar 
                    this.app.spinner.spin();
                    this.app.mediator.publish("navbar:createNewView", view_name, targetApp, read_perms, write_perms, create);

                    this.updateViewName(view_name);
                    this.enableDisabledButtons();

                }
            }

            
        },
        openView: function(view_name, targetApp) {
            this.app.mediator.publish("navbar:openExistingView", view_name, targetApp);
            this.updateViewName(view_name);
            this.enableDisabledButtons();
        },
        openExistingView: function(e) {
            var view_name = $(e.target).text(),
                targetApp = $(e.target).parents(".targetApp").find(".appName").text();

            if (view_name && targetApp) {
                this.app.spinner.spin();
                this.$openViewModal.modal("hide");  // TODO: move this to after the view loads successfully?
                this.openView(view_name, targetApp);

                this.app.prevURL = window.location.pathname;
                window.history.replaceState({app: targetApp, view: view_name}, "", 
                    "/custom/splunk_app_shared_components/visual_editor/"
                    + targetApp + "/render/" + view_name);

            }
        },
        saveAsNewView: function() {
            var view_name = this.$saveAsModal.find('input.view_name').val(),
                targetApp = this.$saveAsModal.find('select').val(),
                read_perms = this.$saveAsModal.find(':checked[name="perms_read"]').map(function() {
                    return this.value;
                }).get(),
                write_perms = this.$saveAsModal.find(':checked[name="perms_write"]').map(function() {
                    return this.value;
                }).get(),
                create = true;

            if (view_name && targetApp) {
                if (!this.checkViewExist(this.$saveAsModal, view_name, targetApp, read_perms, write_perms)) {
                    this.app.spinner.spin();
                    this.app.mediator.publish("navbar:saveAsNewView", view_name, targetApp, read_perms, write_perms, create);

                    this.updateViewName(view_name);
                    this.enableDisabledButtons();

                }
            }
        },
        toggleViews: function(e) {
            var $target = $(e.target),
                $childrenViews = $target.parents(".targetApp").find(".childrenViews");
            if ($target.hasClass("open")) {
                $target.removeClass("open");
                $target.removeClass("icon-triangle-down-small");
                $target.addClass("icon-triangle-right-small");
                $childrenViews.hide();
            } else {
                $target.addClass("open");
                $target.addClass("icon-triangle-down-small");
                $target.removeClass("icon-triangle-right-small");
                $childrenViews.show();
            }
        },
        mouseoverView: function(e) {
            var viewName = $(e.target).text(),
                appName = $(e.target).parents(".targetApp").find(".appName").text(),
                src = "/app/" + appName + "/" + viewName,
                text = appName + ":" + viewName;
            // this.$openViewModal.find(".previewName").text(text);
            this.$openViewModal.find("iframe").attr("src", src);

            this.$openViewModal.find(".viewName").removeClass("hover");
            $(e.target).addClass("hover");

        },
        renamePatternName: function() {
            var input = this.$patternNameModal.find('input#editPatternName');
            this.$("#patternName").text(input.val());
            this.group.set("name", input.val());
        },
        togglePattern: function() {
            this.$el.addClass("editing");
            this.$("#viewItems").hide();
            this.$("#patternItems").show();
            
        },
        toggleWorkspace: function() {
            this.$el.removeClass("editing");
            this.$("#patternItems").hide();
            this.$("#viewItems").show();
        },
        /* helper functions for hitting splunkd */
        populateAppNamesList: function($target) {
            var that = this;
            _.each(that.apps, function(v, k) {
                var $option = $("<option></option>")
                    .val(k)
                    .text(k)
                    .attr('target_app', k);
                $target.append($option);
            });
        },
        populateViewsLists: function($target) {
            var data = this.splunkData,
                that = this;

            data = _.groupBy(data.entry, function(view) {
                return view.acl.app;
            });
            console.log(data);
            $target.html(_.template(ViewsByAppTemplate, {data: data}));
            // _.each(data.entry, function(entry) {
            //     that.appendNewView(entry.name, entry.acl.app, $target);
            // });
        },
        /* helper functions */
        updateViewName: function(view_name) {
            this.$("#viewName").text(view_name);
        },
        enableDisabledButtons: function() {
            this.$("#save, #viewName").removeClass("disabled");
        },
        appendNewView: function(view_name, targetApp, $target) {
            var $option = $("<option></option>")
                .val(view_name)
                .text(targetApp + ": " + view_name)
                .attr('target_app', targetApp);
            $target.append($option);
        },
        checkViewExist: function($modal, view_name, targetApp, read_perms, write_perms) {
            if (this.apps[targetApp][view_name]) {
                // already exists
                $modal.modal("hide");
                this.$overwriteViewModal.modal("show");

                var that = this,
                    create = false;
                this.$overwriteViewModal.find(".overwriteView").one("click", function() {
                    if ($modal === that.$newViewModal) {
                        that.app.mediator.publish("navbar:createNewView", view_name, targetApp, read_perms, write_perms, create);   
                    } else {
                        that.app.mediator.publish("navbar:saveAsNewView", view_name, targetApp, read_perms, write_perms, create);
                    }
                    that.updateViewName(view_name);
                    that.enableDisabledButtons();
                    that.$overwriteViewModal.modal("hide");
                });

                return true;
            } else {
                return false;
            }
        }
 
    });
});
