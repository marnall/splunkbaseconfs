require([
    'underscore',
    'jquery',
    'splunkjs/mvc',
    'splunkjs/mvc/simplexml/ready!',
    'splunkjs/ready!'
], function(_, $, mvc) {

    $("#search_btn").on("click", function() {
        
        var browserUrl = $(location).attr('search').substring(1);
        
        setTimeout(function () {
            
            var urlTokenModel = mvc.Components.getInstance('url');
            var filterUrl = $.param(urlTokenModel.attributes);
            
            //If the user has not changed the timepicker, then we use forced page reload
            if(filterUrl == browserUrl) {
                window.location.href = window.location.href;
            }
        }, 1000); 
    });
});