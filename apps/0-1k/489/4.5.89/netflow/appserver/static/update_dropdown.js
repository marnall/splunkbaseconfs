require(['jquery', 'splunkjs/mvc/searchmanager', 'splunkjs/mvc/simplexml/ready!'], function($, SearchManager) {
 
    var update_exporters_search = new SearchManager({
        id: 'save_exporters_with_nfo',
        autostart: false,
        cache: false,
        earliest_time: '-30m@m',
        latest_time: 'now',
        search: '| savedsearch "save_exporters_with_nfo" '
    });

    var update_snmp_devices_search = new SearchManager({
        id: 'save_snmp_devices',
        autostart: false,
        cache: false,
        earliest_time: '-30m@m',
        latest_time: 'now',
        search: '| savedsearch "save_snmp_devices" '
    });

    var update_save_vpcs_with_nfo_search = new SearchManager({
        id: 'save_vpcs_with_nfo',
        autostart: false,
        cache: false,
        earliest_time: '-30m@m',
        latest_time: 'now',
        search: '| savedsearch "save_vpcs_with_nfo" '
    });

    var update_save_gcp_project_vpc_subnets_with_nfo_search = new SearchManager({
        id: 'save_gcp_project_vpc_subnets_with_nfo',
        autostart: false,
        cache: false,
        earliest_time: '-30m@m',
        latest_time: 'now',
        search: '| savedsearch "save_gcp_project_vpc_subnets_with_nfo" '
    });

    var update_save_nsg_vnets_with_nfo_search = new SearchManager({
        id: 'save_nsg_vnets_with_nfo',
        autostart: false,
        cache: false,
        earliest_time: '-30m@m',
        latest_time: 'now',
        search: '| savedsearch "save_nsg_vnets_with_nfo" '
    });


    var update_exporters = function(event) {
        update_exporters_search.startSearch();
        update_snmp_devices_search.startSearch();
        update_save_vpcs_with_nfo_search.startSearch();
        update_save_gcp_project_vpc_subnets_with_nfo_search.startSearch();
        update_save_nsg_vnets_with_nfo_search.startSearch();
        event.preventDefault();
        return;
    };
 
    $(document).ready(function() {
        $('.dashboard-row1').removeClass('dashboard-row');
        $('#updateexp').submit(update_exporters);
        update_exporters_search.on('search:start', function() {
           $('#updateexp_text').html('&nbsp;&nbsp;Updating device list...');
        });
        update_exporters_search.on('search:failed', function() {
           $('#updateexp_text').html('&nbsp;&nbsp;Failed to update device list');
        });
        update_exporters_search.on('search:done', function() {
           $('#updateexp_text').html('&nbsp;&nbsp;Device list successfuly updated');
           window.location.reload(true);
        });
    });
});