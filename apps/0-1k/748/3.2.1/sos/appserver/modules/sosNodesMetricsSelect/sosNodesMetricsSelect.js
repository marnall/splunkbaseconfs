Splunk.Module.sosNodesMetricsSelect = $.klass(Splunk.Module, {

    initialize: function($super, container) {
        $super(container);

        this.default_option = this.getParam('default_option');
        this.namespace = this.getParam('namespace');
        this.options = this.getParam('options');
        this.options_obj = this.buildObjFromList(this.options);
        this.select = $('select', this.container);
        this.selected = this.default_option;
        this.token = this.getParam('token');
        this.width = this.getParam('outer_width');

        this.addOptions();

        if ($.multiselect === undefined) {
            $script(Splunk.util.make_url('/static/app/sos/js/contrib/jquery-ui/jquery.multiselect.js'),
                'mselect');
            $script.ready(['mselect'], this.initMultiSelect.bind(this));
        } else {
            this.initMultiSelect();
        }
    },
    
    /*
     * add the specified options to the module's select 
     */
    addOptions: function() {
       var i, opt, $opt;
       for (i=0; i < this.options.length; i++) {
           // get the first (and only) key name
           opt = Object.keys(this.options[i])[0].toString();
           $opt = $('<option>')
               .attr('value', opt)
               .text(opt);
           if (this.default_option === opt) {
               $opt.attr('selected', 'selected');
           }
           this.select.append($opt);
       }
    },
   
    buildObjFromList: function(list) {
        var output = {},
            i, key;
        for (i=0; i < list.length; i++) {
            key = Object.keys(list[i])[0];
            output[key] = list[i][key];
        }
        return output;
    },

    /*
     * intialize the multiselect
     */ 
    initMultiSelect: function() {
        var that = this;

        this.select.multiselect({
            multiple: false,
            close: function(event, ui) {
                      $('.ui-multiselect', that.container).css('border-radius', '4px 4px 4px 4px')
                          .css('border-bottom', '1px solid #9F9F9F');
                      that.menu.children('ul').first()
                          .children().first().show();
                      that.menu.hide()
                   },
            minWidth: that.width,
            open: function(event, ui) {
                    $('.ui-multiselect', that.container).css('border-radius', '4px 4px 0 0')
                          .css('border-bottom', 'none');
                    that.menu.children('ul').first().css('height', '100%')
                             .children().first().hide();
                    that.menu.show();
                  },
            selectedList: 1
        });
        // select header and menu
        this.header = $('#ui-multiselect-header_' + this.moduleId).hide();
        this.menu = $('#ui-multiselect-menu_' + this.moduleId);

        // bind input checkbox click
        this.menu.bind('click', this.onSelect.bind(this));

        // in case a selected mandate has been given
        this.selectSelected(this.selected);

        // resize inner menu and checkboxes
        this.menu.css('width', this.width)
                 .css('height', 'auto');
    },

    /*
     * override
     * put selected in the form namespace
     */
    getModifiedContext: function() {
        var context = this.getContext(),
            form = context.get('form') || {};

        form[this.token] = this.selected;
        context.set('form', form);
        context.set(this.namespace, this.options_obj[this.selected]);
        return context;
    },

    /*
     * override
     * we don't have any intentions, just a namespace 
     */
    getToken: function() {
        return this.token;
    },

    onContextChange: function() {
        var context = this.getContext(),
            form = context.get('form') || {},
            selected = form[this.token] || null;
        if (selected !== null) {
            this.selected = selected;
        }
    },

    /*
     * select callback
     */
    onSelect: function(event) {
        var $target = $(event.target),
            val = $target.val();
        if ($target.is('input')) {
            this.selectSelected(val);
        }
    },

    /*
     * check the checkbox corresponding to the selected value
     */
    selectSelected: function(val) {
        this.select.children().attr('selected', false);
        this.select.children('option[value="' + val + '"]')
            .attr('selected', 'selected')
            .prependTo(this.select);
        this.selected = val;
        this.select.multiselect('close');
        this.select.multiselect('refresh');
         
        this.pushContextToChildren();
           $(".Jprogressor").hide()

    }

});
