//put Module in the namespace if it isnt already there.
Splunk.namespace("Module");

Splunk.Module.searchbuilderAnalyzer = $.klass(Splunk.Module, {
    initialize: function($super, container){
        $super(container);

    },

    onContextChange: function($super){
        $super();
        this.getResults();
    },
    getResultParams: function($super){
        var context = this.getContext(),
            search = context.get('search');
        return {search: search.toString()};
    },
    onResultsRendered: function(){
        $('.miniSearch', this.container).bind('click', $.bind(this.startMiniSearch, this));
        $('.hider', this.container).bind('click',$.bind(this.hideHelp, this));
$('.SearchBar fieldset').bind('keyup keypress blur', function()
{

        var highlighter = $('.SearchBar textarea').val();
        var highlighterkv = new RegExp("(\\w+)=(\\w+)","gi");
        var highlightercommands = new RegExp("\\|(\\w+)","gi");
        var kvpair  = highlighter.replace(highlighterkv, "<span class='field' style='color:darkblue'>$1</span><span>=</span><span class='value' style='color:darkred'>$2</span>");
        var commands = kvpair.replace(highlightercommands, "<span>|</span><span class='command' style='color:darkgreen'>$1 </span>");
        
      
 
    $('.mirrored')[0].innerHTML=commands;
});

    },
    startMiniSearch: function(evt){
        var $target = $(evt.target),
            searchString = unescape($target.data('search')),
            context = this.getContext(),
            search = context.get('search');
        search.setBaseSearch(searchString);
        context.set('search', search);
        this.pushContextToChildren(context);
    },
    hideHelp: function(){

        if ($('.commander')[0]['attributes']['style'].nodeValue=="display: none;") {
        $('.commander').css("display","table-cell");
        $('.searcher').css("max-width","200px");

        }else{
        $('.commander').css("display","none");
        $('.searcher').css("max-width","400px");
        }
    }


});
