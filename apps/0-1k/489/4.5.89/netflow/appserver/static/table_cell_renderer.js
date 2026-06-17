define(function(require, exports, module) {

    var _ = require('underscore');
    var mvc = require('splunkjs/mvc');
    var $ = require('jquery');

    var BaseCellRenderer = require('views/shared/results_table/renderers/BaseCellRenderer');
    var right_aligned_columns = [
        "% of Local Resets",
        "% of Total Resets",
        "% of Total",
        "% of Usage Both",
        "Average Bits/s Both",
        "Average Bits/s Both",
        "Average Bits/s received",
        "Average Bits/s sent",
        "Average Bits/s",
        "Average Packets/s received",
        "Average Packets/s sent",
        "Average Packets/s",
        "Average Resp. Time ms",
        "Bytes",
        "Created flows",
        "Denied flows",
        "Flow Count",
        "Max Bits/s",
        "Max Bytes",
        "Min Bits/s",
        "Min Bytes",
        "Num. of Flows",
        "Reset Count",
        "Standard Deviation Bits/s",
        "Total Connections",
        "Total Packets received",
        "Total Packets sent",
        "Total Packets",
        "Total Traffic Bytes received",
        "Total Traffic Bytes sent",
        "Total Traffic Bytes",
        "Traffic Bytes"
    ];

    var table_cell_renderer = BaseCellRenderer.extend({
        canRender: function(cell) {
            return ($.inArray(cell.field, right_aligned_columns) >= 0);
        },
        render: function($td, cell) {
            if ( $.inArray(cell.field, right_aligned_columns) >= 0 ) {
                $td.addClass("numeric");
            }
            $td.html( cell.value );
        }
    });
    return table_cell_renderer;
});