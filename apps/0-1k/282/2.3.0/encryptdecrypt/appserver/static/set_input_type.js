require(["jquery", "splunkjs/mvc/simplexml/ready!"], function($) {

        $("[id^=decrypt_key]")
            .find("input")
            .attr('type','password')
	    });