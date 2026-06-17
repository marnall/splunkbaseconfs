require(['jquery', 'splunkjs/mvc/searchmanager', 'splunkjs/mvc/simplexml/ready!'], function($, SearchManager) {

    var import_sampling_search = new SearchManager({
        id: 'import_sampling',
        autostart: false,
        cache: false,
        earliest_time: '-30m@m',
        latest_time: 'now',
        search: '| savedsearch "import_sampling" '
    });
    var import_interfaces_20003_search = new SearchManager({
        id: 'import_interfaces_20003',
        autostart: false,
        cache: false,
        earliest_time: '-30m@m',
        latest_time: 'now',
        search: '| savedsearch "import_interfaces_20003" '
    });

    var import_mgmt_ip_search = new SearchManager({
        id: 'import_mgmt_ip',
        autostart: false,
        cache: false,
        earliest_time: '-30m@m',
        latest_time: 'now',
        search: '| savedsearch "import_mgmt_ip" '
    });


    var import_nfo_exp_group_exp_search = new SearchManager({
        id: 'import_nfo_exp-group_exp',
        autostart: false,
        cache: false,
        earliest_time: '-30m@m',
        latest_time: 'now',
        search: '| savedsearch "import_nfo_exp-group_exp" '
    });


    var import_nfo_vpc_exp_search = new SearchManager({
        id: 'import_nfo_vpc_exp',
        autostart: false,
        cache: false,
        earliest_time: '-30m@m',
        latest_time: 'now',
        search: '| savedsearch "import_nfo_vpc_exp" '
    });


    var import_nfo_gcp_project_vpc_subnet_search = new SearchManager({
        id: 'import_nfo_gcp_project_vpc_subnet',
        autostart: false,
        cache: false,
        earliest_time: '-30m@m',
        latest_time: 'now',
        search: '| savedsearch "import_nfo_gcp_project_vpc_subnet" '
    });






//inputlookup exporters-devices.csv | outputlookup exporters_devices_lookup
 
    var import_csv_lookups = function(event) {
        import_sampling_search.startSearch();
        import_interfaces_20003_search.startSearch();
        import_mgmt_ip_search.startSearch();
        import_nfo_exp_group_exp_search.startSearch();
        import_nfo_vpc_exp_search.startSearch();
        import_nfo_gcp_project_vpc_subnet_search.startSearch();
        event.preventDefault();
        return;
    };
    $(document).ready(function() {
        $('.dashboard-row1').removeClass('dashboard-row');
        $('#importcsv').submit(import_csv_lookups);
        import_sampling_search.on('search:start', function() {
           $('#import_sampling_csv_text').html('&nbsp;&nbsp;Importing sampling.csv...');
        });
        import_sampling_search.on('search:failed', function() {
           $('#import_sampling_csv_text').html('&nbsp;&nbsp;Failed to import sampling.csv');
        });
        import_sampling_search.on('search:done', function() {
           $('#import_sampling_csv_text').html('&nbsp;&nbsp;Imported sampling.csv');
        });
        import_interfaces_20003_search.on('search:start', function() {
           $('#import_interfaces_20003_csv_text').html('&nbsp;&nbsp;Importing interfaces_20003.csv...');
        });
        import_interfaces_20003_search.on('search:failed', function() {
           $('#import_interfaces_20003_csv_text').html('&nbsp;&nbsp;Failed to import interfaces_20003.csv');
        });
        import_interfaces_20003_search.on('search:done', function() {
           $('#import_interfaces_20003_csv_text').html('&nbsp;&nbsp;Imported interfaces_20003.csv');
        });
        import_mgmt_ip_search.on('search:start', function() {
           $('#import_mgmt_ip_csv_text').html('&nbsp;&nbsp;Importing mgmt_ip.csv...');
        });
        import_mgmt_ip_search.on('search:failed', function() {
           $('#import_mgmt_ip_csv_text').html('&nbsp;&nbsp;Failed to import mgmt_ip.csv');
        });
        import_mgmt_ip_search.on('search:done', function() {
           $('#import_mgmt_ip_csv_text').html('&nbsp;&nbsp;Imported mgmt_ip.csv');
        });


        import_nfo_exp_group_exp_search.on('search:start', function() {
           $('#import_nfo_exp-group_exp_csv_text').html('&nbsp;&nbsp;Importing nfo_exp-group_exp.csv...');
        });
        import_nfo_exp_group_exp_search.on('search:failed', function() {
           $('#import_nfo_exp-group_exp_csv_text').html('&nbsp;&nbsp;Failed to import nfo_exp-group_exp.csv');
        });
        import_nfo_exp_group_exp_search.on('search:done', function() {
           $('#import_nfo_exp-group_exp_csv_text').html('&nbsp;&nbsp;Imported nfo_exp-group_exp.csv');
        });

        import_nfo_vpc_exp_search.on('search:start', function() {
           $('#import_nfo_vpc_exp_csv_text').html('&nbsp;&nbsp;Importing nfo_vpc_exp.csv...');
        });
        import_nfo_vpc_exp_search.on('search:failed', function() {
           $('#import_nfo_vpc_exp_csv_text').html('&nbsp;&nbsp;Failed to import nfo_vpc_exp.csv');
        });
        import_nfo_vpc_exp_search.on('search:done', function() {
           $('#import_nfo_vpc_exp_csv_text').html('&nbsp;&nbsp;Imported nfo_vpc_exp.csv');
        });

        import_nfo_gcp_project_vpc_subnet_search.on('search:start', function() {
           $('#import_nfo_gcp_project_vpc_subnet_csv_text').html('&nbsp;&nbsp;Importing nfo_gcp_project_vpc_subnet.csv...');
        });
        import_nfo_gcp_project_vpc_subnet_search.on('search:failed', function() {
           $('#import_nfo_gcp_project_vpc_subnet_csv_text').html('&nbsp;&nbsp;Failed to import nfo_gcp_project_vpc_subnet.csv');
        });
        import_nfo_gcp_project_vpc_subnet_search.on('search:done', function() {
           $('#import_nfo_gcp_project_vpc_subnet_csv_text').html('&nbsp;&nbsp;Imported nfo_gcp_project_vpc_subnet.csv');
        });






    });
});