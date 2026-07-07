class ContentType(object):
    CORRELATION_SEARCH = 'correlation_searches'
    DEEP_DIVE = 'deep_dives'
    ENTITY_TYPE = 'entity_types'
    EVENT_MANAGEMENT_STATE = 'event_management_states'
    GLASS_TABLE = 'glass_tables'
    GLASS_TABLE_ICON = 'glass_table_icons'
    GLASS_TABLE_IMAGE = 'glass_table_images'
    KPI_BASE_SEARCH = 'kpi_base_searches'
    KPI_THRESHOLD_TEMPLATE = 'kpi_threshold_templates'
    NOTABLE_EVENT_AGGREGATION_POLICY = 'notable_event_aggregation_policies'
    SERVICE_ANALYZER = 'service_analyzers'
    SERVICE_TEMPLATE = 'service_templates'
    SERVICE = 'services'


CONTENT_PACK_PREFIX = 'DA-ITSI-CP-'
CONTENT_TYPE_TO_ITOA_TYPE = {
    ContentType.CORRELATION_SEARCH: 'correlation_search',
    ContentType.DEEP_DIVE: 'deep_dive',
    ContentType.ENTITY_TYPE: 'entity_type',
    ContentType.EVENT_MANAGEMENT_STATE: 'event_management_state',
    ContentType.GLASS_TABLE: 'glass_table',
    ContentType.GLASS_TABLE_ICON: 'icon',
    ContentType.GLASS_TABLE_IMAGE: 'image',
    ContentType.KPI_BASE_SEARCH: 'kpi_base_search',
    ContentType.KPI_THRESHOLD_TEMPLATE: 'kpi_threshold_template',
    ContentType.NOTABLE_EVENT_AGGREGATION_POLICY: 'notable_event_aggregation_policy',
    ContentType.SERVICE_ANALYZER: 'home_view',
    ContentType.SERVICE_TEMPLATE: 'base_service_template',
    ContentType.SERVICE: 'service'
}
