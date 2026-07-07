# Copyright (C) 2005-2026 Splunk Inc. All Rights Reserved.
import ite_path_inject  # noqa

APP_NAME = 'it_essentials_learn'

MATURITY_STAGES = ['Descriptive', 'Diagnostic', 'Predictive', 'Prescriptive']

FEATURE_FLAGS = set(['edit_mode'])
FEATURE_FLAGS_CONF = 'ite_feature_flags'
ITE_EDIT_OBJECTS_CAPABILITY = 'ite_edit_objects'

# This variable is used in object metadata to represent the source of modifications in a JSON-serializable way.
REQ_SOURCE_UNKNOWN = 'UNKNOWN'
REQ_SOURCE_DATA_LOADER = 'DATA_LOADER'
REQ_SOURCE_REST_API = 'REST_API'
REQ_SOURCE_CONTENT_GEN = 'CONTENT_GEN'
