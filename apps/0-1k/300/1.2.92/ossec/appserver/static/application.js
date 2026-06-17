
function setManageAgentsFields() {
    // Hide fields that are not relevent for a given agent management command
    AgentName     = jQuery('div#ExtendedFieldSearch_0_5_0');
    AgentIP       = jQuery('div#ExtendedFieldSearch_1_6_0');
    AgentID       = jQuery('div#ExtendedFieldSearch_2_7_0');
    AgentNameText = jQuery('div#ExtendedFieldSearch_0_5_0>form>div>input');
    AgentIPText   = jQuery('div#ExtendedFieldSearch_1_6_0>form>div>input');
    AgentIDText   = jQuery('div#ExtendedFieldSearch_2_7_0>form>div>input');
    Button        = jQuery(":button").children();

    try {
        selection = $('#StaticSelect_0_3_0').children()[1].value;
    } catch(err) {
        selection = ''
    }


    if (selection == 'listagents') {
        AgentIPText.val('');
        AgentIDText.val('');
        AgentName.hide();
        AgentIP.hide();
        AgentID.hide();
        Button.text("List Agents");

    } else if (selection == 'removeagent') {
        AgentIDText.val('');
        AgentName.hide();
        AgentIP.hide();
        AgentID.show();
        Button.text("Remove Agent");

    } else if (selection == 'extractagentkey') {
        AgentIPText.val('');
        AgentName.show();
        AgentIP.hide();
        AgentID.show();
        Button.text("Extract Key");

    } else if (selection == 'addagent') {
        AgentIDText.val('');
        AgentName.show();
        AgentIP.show();
        AgentID.show();
        Button.text("Add Agent");

    } else {
	// Unknown, enable all fields
        AgentName.show();
        AgentIP.show();
        AgentID.show();
        Button.text("Add/Remove Agent");
    };
    Button.removeClass('greyedOut');
}


$(document).ready(function() {
    if (document.title.substr(0,22) == 'OSSEC Agent Management') {
        // For well-behaved browers
        $('#StaticSelect_0_3_0').bind("change", setManageAgentsFields);
        $('#StaticSelect_0_3_0').bind("keyup", setManageAgentsFields);

        // IE does not handle onChange properly...
        if ($.browser.msie) {
            $('#StaticSelect_0_3_0').bind("click", setManageAgentsFields);
        }

        setManageAgentsFields();
	};
});
