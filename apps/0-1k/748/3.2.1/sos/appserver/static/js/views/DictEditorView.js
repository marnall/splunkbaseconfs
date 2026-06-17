define([
    "jquery",
    "underscore",
    "backbone",
    "bootstrap.button",
    "text!app/templates/DictEditorControls.html"
], function(
    $,
    _,
    Backbone,
    button,
    controlsTemplate
){

    (function($) {
        // http://stackoverflow.com/questions/8961770/similar-to-jquery-closest-but-traversing-descedents
        $.fn.closestDescendent = function(filter) {
            var $found = $(),
                $currentSet = this;
            while ($currentSet.length) {
                $found = $currentSet.filter(filter);
                if ($found.length) { break; }
                // Get all children of the current set
                $currentSet = $currentSet.children();
            }
            return $found.first(); // Return first match of the collection
        };
    })(jQuery);


    /*
    DictEditorView
    Creates child versions of itself. Dict and List children invoke the creation of a new
    DictEditorView. However, non-dict/lists are on the same level and are simply appended
    to the current view. 

    Closures are used to associate data with the individual controls.

    There are a few inconsistencies that should be delegated to the children:
        - children should set up their own controls, but they currently do not

    Also it would probably be nice if the view was completely separate from the hierarchy part
    */

    var DictEditorView = Backbone.View.extend({
        id: _.uniqueId("dictEditorView-"),
        className: "dictEditor depthWrapper",
        initialize: function(opt){
            this.app = this.options.app;
            this.data = this.options.data;
            this.depth = this.options.depth || 0;
            this.parent = this.options.parent || null;
            this.name = this.options.name || "";
            this.children = [];
            this.$el = $(this.el);
            

            
            this.render();
        },
        render: function() {
            if(this.parent !== null){
                this.parent.$el.closestDescendent('.childContainer').append(this.$el);
            }

            this.setup();
            
            if(this.options.$parentKey !== undefined){
                this.$el.find('.controlButtons').prepend(this.options.$parentKey);
            }

            if(this.options.$closeBracket !== undefined){
                this.$el.find('.depthContainer').append(this.options.$closeBracket);
            }
            this.appendData();
        },
        setData: function(data) {
            this.data = data;
        },
        setup: function(){
            var $current, 
                self = this;

            this.$currentDepth = this.insertNewDepth(this.$el, this.data, this.depth);
            this.$el.append(this.$currentDepth);
            this.setupEvents();
        },

        // Cannot use events because they delegate downwards to children
        // this causes the children to fire events on the parent as well!
        setupEvents: function(){
            var self = this, data;

            this.$currentDepth.find('.insertString').on('click', function(){
                data = self.insertNewStringData();
                self.insertString(data.k, data.v);
            });

            this.$currentDepth.find('.insertDict').on('click', function(){
                data = self.insertNewChildData('dict');
                self.insertChild('dict', data.childData, data.parentKey);
            });

            this.$currentDepth.find('.insertList').on('click', function(){
                data = self.insertNewChildData('list');
                self.insertChild('list', data.childData, data.parentKey);
            });
            this.$currentDepth.find('.removeDictList').on('click', function(){
                self.clear();
                if (self.depth === 0) {
                    self.$el.trigger("removeDictList", [self.name]);
                }
               
            });
        },

        insertNewDepth: function($container, data, depth){
            var $depth, $controlButtons, $childContainer,
                $openBracket, $closeBracket,
                openBracket, closeBracket;

            $depth = $("<div class='depthContainer depth"+depth+"'></div>"); //todo: use template
            $controlButtons = $("<div class='controlButtons'></div>"); // todo: use template
            $childContainer = $("<div class='childContainer'></div>");


            $depth.append($controlButtons);
            this.appendInsertButtons($controlButtons);
            $depth.append($childContainer);

            // Bracket indicators if this is the first depth
            if (depth === 0) {
                if (_.isArray(data)) {
                    openBracket ="["; 
                    closeBracket = "]";
                } else if (_.isObject(data)) {
                    openBracket ="{"; 
                    closeBracket = "}";
                }
                $openBracket = $("<div class='dictKeyMarkers openBracket'>"+openBracket+"</div>");
                $closeBracket = $("<div class='dictKeyMarkers closeBracket'>"+closeBracket+"</div>");

                $depth.prepend($openBracket);
                $depth.append($closeBracket);
            }

            $childContainer.css({'margin-left': 35, 'margin-top': 7, 'margin-bottom': 7});
            
            return $depth;
        },

        appendInsertButtons: function($container){
            var buttons;

            buttons = _.template(controlsTemplate);
            $container.append(buttons);
            $(buttons).button(); // bootstrap button setup
        },

        insertChild: function(type, newData, k){
            var child, 
                $key,
                self = this,
                openBracket, closeBracket,
                $closeBracket,
                $keyInput,
                clone;

            if(type === 'dict'){ 
                openBracket ="{"; 
                closeBracket = "}";
            } else {
                openBracket ="["; 
                closeBracket = "]";
            }

            if(_.isArray(this.data)){
                $key = $("<div class='arrKey'>"+k+"</div><div class='dictKeyMarkers openBracket'>: "+openBracket+"</div>");
            } else {
                $key = $("<input class='dictKeyInput' type='text'/><div class='dictKeyMarkers openBracket'>: "+openBracket+"</div>");
                $key.focusout(function() {
                    var newKey = $(this).val();
                    if (newKey === '') {
                        newKey = '__';
                    }
                    self.data[newKey] = _.clone(self.data[k]);
                    delete self.data[k];
                    k = newKey;
                });
                $key.val(k);
            }

            $closeBracket = $("<div class='dictKeyMarkers closeBracket'>"+closeBracket+"</div>");

            child = new DictEditorView({
                app: this.app,
                data: newData,
                depth: this.depth+1,
                parent: this,
                $parentKey: $key,
                $closeBracket: $closeBracket
            });
            
            this.children.push(child); // not used right now
        },

        insertNewChildData: function(type, k, v){
            var childData;

            if(type === 'dict'){ 
                childData = {};
            } else {
                childData = [];
            }

            if(_.isArray(this.data)){
                this.data.push(childData);
                if(k === undefined){
                    k = this.data.length-1;
                }
            } else {
                this.data[k] = childData;
                if(k === undefined){
                    k = _.uniqueId('newKey');
                }
            }

            /* The parent key is simply the key that links from parent to child
            a: {
                childK: 1
            }
            in that case "a" is the parentKey
            */
            return {
                childData: childData,
                parentKey: k
            };
        },

        insertNewStringData: function(k, v){
            if(k === undefined && v === undefined){
                if(_.isArray(this.data)){
                    v = "arrVal";
                    k = this.data.length;
                } else {
                    k = _.uniqueId('newKey');
                    v = "newVal";
                }    
            }

            if(_.isArray(this.data)){
                this.data.push(v); // check if successful on backbone model
            } else {
                this.data[k] = v; // check if successful on backbone model
            }

            return {
                k: k,
                v: v
            };
        },

        insertString: function(k, v){
        // insertString: function(data, k, v){
            var $data, $v, $remove, $k,
                self = this;

            $data = $("<div class='data'></div>");
            $v = $("<input class='changeData valKeyInput' type='text'>");
            $v.val(v);

            $v.focusout(function(){
                v = $(this).val();
                self.data[k] = v;
            });
            if(_.isNumber(k)){
                $data.append("<span class='key'>"+k+"</span>", "<span class='separator'> : </span>", $v);
            } else {
                $k = $("<input class='changeData stringKeyInput' type='text'>");
                $k.val(k);
                $data.append($k, "<span class='separator'>  : </span>", $v);

                $k.focusout(function() {
                    var newK = $(this).val();
                    if (newK === "") {
                        newK = "__";
                    }
                    self.data[newK] = v;
                    delete self.data[k];
                    k = newK;
                });
            }

            $remove = $("<span class='icon-x remove' />");
            $data.append($remove);
            $remove.on('click', function(){
                if(_.isNumber(k)){
                    //todo: can we do this with self.data
                    // data.remove(k);
                    self.data.remove(k);
                } else {
                    // delete data[k];
                    delete self.data[k];
                }
                $data.remove();
            });


            this.$currentDepth.children('.childContainer').append($data);
        },

        // inserts the key corresponding to the sub-data
        prependKey: function($container, k){
            var $k = $("<span class='bold'>"+k+"</span>");
            $k.insertBefore($container);
        },

        /*
        Constructs a tree from data given to the root.
        This method will create the appropriate UI for every 
        piece of data at the current level of the tree.
        */
        appendData: function(){
            var self = this;
            
            _.each(this.data, function(v, k){
                if(_.isArray(v)){
                    self.insertChild('list', v, k);
                } else if(_.isObject(v)){
                    self.insertChild('dict', v, k);
                } else {
                    self.insertString(k, v);
                }
            });
        },
        toJSON: function() {
            return _.clone(this.data);
        },
        clear: function() {
            _.each(this.children, function(child) {
                child.clear();
            });
            this.children = [];
            this.$(".childContainer").empty();
            this.$el.empty();

            if (_.isArray(this.data)) {
                this.data = [];
            } else if (_.isObject(this.data)) {
                this.data = {};
            }
        }

    });

    return DictEditorView;
});