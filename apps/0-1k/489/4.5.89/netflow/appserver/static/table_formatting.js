require.config({
    paths: {
        table_cell_renderer: '../app/netflow/table_cell_renderer'
    }
});

require([
    'jquery',
    'splunkjs/mvc', 
    '../../app/netflow/table_cell_renderer', 
    'splunkjs/mvc/simplexml/ready!'
], function($, mvc, table_cell_renderer){
    var table_ids = [ "table", "table_1_1", "table_1_2", "table_2_1", "table_2_2", "table_3_1", "table_4_1" ];

    $.each(table_ids, function( index, value ) {
        var formattedTable = mvc.Components.get(String(value));
        if (!$.isEmptyObject(formattedTable)){
            formattedTable.getVisualization(function(tableView){
                tableView.table.addCellRenderer(new table_cell_renderer());
                tableView.table.render();
            });
        }
    });
});