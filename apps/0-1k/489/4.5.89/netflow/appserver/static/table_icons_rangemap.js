require.config({
  paths: {
    theme_utils: '../app/netflow/theme_utils'
  }
});
require([
    'underscore',
    'jquery',
    'splunkjs/mvc',
    'splunkjs/mvc/tableview',
    'theme_utils',
    'splunkjs/mvc/simplexml/ready!'
], function(_, $, mvc, TableView, themeUtils) {
    // Translations from rangemap results to CSS class
    var ICONS = {
        Critical: 'alert-circle',
        Warning: 'alert',
        Normal: 'check-circle'
    };
    var RangeMapIconRenderer = TableView.BaseCellRenderer.extend({
        canRender: function(cell) {
            // Only use the cell renderer for the range field
            return cell.field === 'Status';
        },
        render: function($td, cell) {
            var icon = '';
            var isDarkTheme = themeUtils.getCurrentTheme && themeUtils.getCurrentTheme() === 'dark';
            // Fetch the icon for the value
            if (ICONS.hasOwnProperty(cell.value)) {
                icon = ICONS[cell.value];
            }
            // Create the icon element and add it to the table cell
            $td.addClass('icon').html(_.template('<i class="icon-<%-icon%> <%- range %> <%- isDarkTheme %>" title="<%- range %>"></i>', {
                icon: icon,
                range: cell.value,
                isDarkTheme: isDarkTheme ? 'dark' : ''
            }));
        }
    });
    var tableElement = mvc.Components.get("table_interfaces");
    tableElement.getVisualization(function(tableView){
//    mvc.Components.get('table_interfaces').getVisualization(function(tableView){
        // Register custom cell renderer, the table will re-render automatically
        tableView.addCellRenderer(new RangeMapIconRenderer());
    });
});