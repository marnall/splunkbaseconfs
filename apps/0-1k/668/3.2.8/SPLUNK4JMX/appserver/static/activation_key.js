require([
    'jquery',
    'splunkjs/mvc/simplexml/ready!'
], function($) {

    var activation_key_div = $(".activation_key_div_input_fields");

    $.ajax({
        type: "GET",
        url: "../../../../en-US/splunkd/__raw/services/ak_jmxmodinput/ak_jmxmodinputsetup/activationkey?output_mode=json",
        success: function(text) {


            var activation_key = text['entry'][0]['content']['activation_key']
            

            $("#activation_key").val(activation_key)  
            

        },
        error: function() {

        }
    });

    var submit_button = $("#activation_key_submit_button");
    var cancel_button = $("#activation_key_cancel_button");


    $(submit_button).click(function(e) {
        e.preventDefault();

        //clear any previous UI state
        clearFormMessage();
        $("input").removeClass("activation_key_required_field_error");

        validated = true;

        var activation_key = encodeURIComponent($("#activation_key").val()) 

        //manadatory fields
        if(activation_key === ""){
                
            validated = false;
            informRequiredField($('#activation_key'))
        }
        

        if(!validated){
          showFormMessage("Ensure that you have entered values for mandatory fields","activation_key_saving_form_error_text");
          return;
        }

        


        $.ajax({
            type: "POST",
            url: "../../../../en-US/splunkd/__raw/services/ak_jmxmodinput/ak_jmxmodinputsetup/activationkey",
            data: "activation_key=" + activation_key,
            success: function(text) {

                window.location.href = '../SPLUNK4JMX/landing_page';

            },
            error: function() {

            }
        });

        showFormMessage("Saving Settings...","activation_key_saving_form_message_text");

    });

    function informRequiredField(inputField){

        inputField.addClass("activation_key_required_field_error");

    }

    function clearFormMessage(){

        $("#saving_form_msg").remove();
    }

    function showFormMessage(message,textClass){

        $(".activation_key_div_input_fields").append('<div id="saving_form_msg" name="saving_form_msg" class="activation_key_saving_form_message_div"><p class="'+textClass+'">'+message+'</p></div>');

    }


    $(cancel_button).click(function(e) {
        e.preventDefault();
        window.location.href = '../SPLUNK4JMX/landing_page';

    });

   

});