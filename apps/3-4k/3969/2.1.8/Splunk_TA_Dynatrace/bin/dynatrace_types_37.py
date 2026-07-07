from typing import NewType, Union, List, Dict, Set, Any
from typing_extensions import TypedDict

MetricKey = NewType('MetricKey', str)
MetricSelector = NewType('MetricSelector', str)
APIToken = NewType('APIToken', str)
Tenant = NewType('Tenant', str)
EntityID = NewType('EntityID', str)
CollectionInterval = NewType('CollectionInterval', int)
WrittenSinceParam = NewType('WrittenSince', dict)
StartTime = NewType('StartTime', int)
EndTime = NewType('EndTime', int)
URL = NewType('URL', str)
Params = NewType('Params', dict)
ResponseSelector = NewType('ResponseSelector', str)
Dimension = NewType('Dimension', Union[EntityID, str])
DimensionType = NewType('DimensionType', str)
MetricId = NewType('MetricId', str)
LocationId = NewType('locationId', str)
ExecutionId = NewType('executionId', str)
PathParam = NewType('PathParam', str)


class Filter:
    referenceInvocation: dict
    targetDimension: str
    targetDimensions: List[str]
    referenceString: str
    rollup: str
    referenceValue: float
    operands: List[dict]
    type: str


class AppliedFilter(TypedDict):
    appliedTo: List[str]
    filter: Filter


class Entity(TypedDict):
    lastSeenTms: int
    firstSeenTms: int
    entityId: str
    managementZones: List[Dict]
    toRelationships: Dict
    fromRelationships: Dict
    tags: List[Dict]
    icon: Dict
    displayName: str
    properties: Dict
    type: str


class MetricDescriptorCollection(TypedDict):
    totalCount: int
    nextPageKey: str
    warnings: List[str]
    metrics: List[Dict]


class MetricDescriptor(TypedDict):
    dduBillable: bool
    billable: bool
    lastWritten: int
    impactRelevant: bool
    minimumValue: float
    maximumValue: float
    latency: int
    resolutionInfSupported: bool
    unitDisplayFormat: str
    dimensionCardinalities: List[Dict]
    defaultAggregation: str
    rootCauseRelevant: bool
    dimensionDefinitions: List[Dict]
    entityType: List[str]
    metricId: MetricId
    metricSelector: MetricSelector
    scalar: bool
    aggregationTypes: List[str]
    metricValueType: str
    created: int
    transformations: List[str]
    unit: str
    warnings: List[str]
    tags: List[str]
    displayName: str
    description: str


class DimensionMap(TypedDict):
    dimensionType: DimensionType
    dimension: Dimension


class DataPoint(TypedDict):
    "Splunk type"
    dimensionMap: DimensionMap
    timestamp: str
    value: Any
    resolution: str


class MetricSeries(TypedDict):
    dimensionMap: DimensionMap
    timestamps: List[str]
    values: List[Any]
    dimensions: Set[Dict]


class MetricSeriesCollection(TypedDict):
    dataPointCountRatio: float
    dimensionCountRatio: float
    appliedOptionalFilters: List[Dict]
    metricId: MetricId
    warnings: List[str]
    data: List[Dict]


class MetricData(TypedDict):
    resolution: str
    totalCount: int
    nextPageKey: str
    warnings: List[str]
    result: List[Dict]


class SyntheticLocation(TypedDict):
    capabilities: List[str]
    cloudPlatform: str
    endpoint: str
    entityId: str
    geoLocationId: str
    ips: List[str]
    name: str
    stage: str
    status: str
    type: str


class SyntheticOnDemandExecution(TypedDict):
    batchId: str
    executionId: str
    executionStage: str
    schedulingTimestamp: int
    executionTimestamp: int
    dataDeliveryTimestamp: int
    monitorId: str
    locationId: str
    nextExecutionId: int
    userId: str
    metadata: dict
    source: str
    processingMode: str
    customizedScript: dict
    simpleResults: dict
    fullResults: dict



class Problem(TypedDict):
    json: str


class Metric(TypedDict):
    "Splunk type"
    "TODO Probably want to change this"
    metric_name: str
    resolution: str
    unit: str
    timestamp: str
    value: str
    dynatraceTenant: str
    metricSelector: MetricSelector


class LocationExecutionResults(TypedDict):
    locationId: LocationId
    executionId: ExecutionId
    requestResults: List[Dict]


class MonitorExecutionResults(TypedDict):
    locationExecutionResults: List[Dict]
    monitorId: str


class SyntheticExecution(TypedDict):
    json: str


class SyntheticMonitor(TypedDict):
    json: str


class EntitiesList(TypedDict):
    totalCount: int
    pageSize: int
    nextPageKey: str
    entities: List[Dict]


class MetricDimensionCardinality(TypedDict):
    relative: float
    estimate: int
    key: str


class MetricDefaultAggregation(TypedDict):
    parameter: float
    type: str


class MetricDimensionDefinition(TypedDict):
    displayName: str
    name: str
    key: str
    type: str
    index: int


class MetricValueType(TypedDict):
    type: str


