Splunk.Module.MultiSelect = $.klass(Splunk.Module.AbstractSearchLister, {

    initialize: function($super, container) {
        $super(container);
        $('select', this.container).bind('change', this.onUserAction.bind(this));
    },

    isDisabled: function() {
        return $('select', this.container).prop('disabled');
    },

    getListValue: function() {
	return $('select', this.container).val();
    },

    getTokenValues: function() {
        var selected = $('select', this.container);
        var option = $('select option:selected', this.container);
        return { 
            'value': selected.val(),
            'key': option.attr('key'),
            'label': option.text()
        };
    },
    
    /**
     * Select the selected option fool!
     */
    selectSelected: function() {
        var selected = this.getParam('selected');
	if (selected) {
            try {
                $('option',this.container).filter(function() {return $(this).val() == selected;}).prop('selected', true);
            } catch(ex) {
                console.debug('ie6 is lagging to select a dropdown value');
            }
        }
    },

    onInternalJobDispatched: function() {
        if ($('select', this.container).prop('disabled')) return;
        $('select', this.container).empty().prop('disabled', true);
        $('select', this.container).append($('<option>Loading...</option>'));
    },

    renderResults: function($super, html) {
        $('select', this.container).empty();
        $('select', this.container).append(html);
        this.selectSelected();
        $('select', this.container).prop('disabled', false);
	set(this.container);
	$super(html);
    },

    onContextChange: function($super) {
        var context = this.getContext();
        var formValue = context.get('form.'+this.token);
	if (formValue) {
            this.setParam('selected', formValue);
            this.selectSelected();
        }
        $super();
    },

    resetUI: function() {
	if (this.getParam('selected')) {
            this.selectSelected();
        } else {
            var select = $('select', this.container);
            select.val($('option:first', select).val());
        }
    }

});

function set(e){
	var $mod_id = $(e).attr("id")+"_";
	var $sel_id = '#' + $mod_id+"chooser";
	var $div_id = '#' + $mod_id +"div";
	var $see_id = '#' + $mod_id +"see";
	var links = {};
	$($see_id).click(function(){
	    $($div_id).empty();
	    $($div_id).toggleClass("MultiSelectChoosen MultiSelectChoosen_hide");
	    if($($div_id).attr("class") == "MultiSelectChoosen"){
		$("#"+$mod_id+"id > option").each(function(){
			if($(this).prop("selected"))
				$($div_id).append($("<span></span>").text($(this).val()).append($("<br/>")));
		});
	    };
	});
	$($sel_id).empty();
	$("#"+$mod_id+"id").change(function(){
	    $($see_id).click();
	    $($see_id).click();
	});
	$("#"+$mod_id+"id >option").each(function(){
	    var $this_ref = $(this);
	    links[$this_ref.val()] = $this_ref;
	    $($sel_id).append(
		    $("<option></option>").text($this_ref.val()));
					    /*
					    .mousedown(function(e){
					e.preventDefault();
					$(this).prop("selected",true);
					if($this_ref.prop("selected")){
					    $this_ref.prop("selected",false);
					}else{
					    $this_ref.prop("selected",true);
					}
					$this_ref.change();
	    }));*/
	});
	$($sel_id).click(function(e){
	    if($(this).data("clicks") == 1){
		$changed_element = links[$(this).children(":selected").val()];
		if($changed_element.prop("selected")){
		    $changed_element.prop("selected",false); 
		}else{
		    $changed_element.prop("selected", true);
		}
		$changed_element.change();
		$(this).data("clicks",0);
	    }else{
		$(this).data("clicks",1);
	    }
	});

	$($sel_id).focusout(function(e){
	    $(this).data("clicks",0);
	});
};
