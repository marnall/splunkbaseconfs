require([
    'underscore',
    'jquery',
    'splunkjs/mvc',
    'splunkjs/mvc/simplexml/ready!',
    'splunkjs/ready!'
], function(_, $, mvc) {
    setInterval(function () {
        $("div.shared-map[data-view='views/shared/Map']").attr("style", "").css({
            width: "100%",
            height: "400px"
        });
    }, 3000);
});