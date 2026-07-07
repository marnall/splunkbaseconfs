import sys
import os
import sys

# Add the orchestrator client to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))

from constants import *
from util.timeseries_correlation import transfer_df_to_series_dict, correlations, to_datetime_safe
from typing import List, Dict, Set, Union, Tuple
import pandas as pd
from datetime import datetime
from itertools import product

from util import setup_logging
from util.context_logging import get_context_logger
from collections import defaultdict

logger = setup_logging.get_logger()
logger = get_context_logger(logger)


class ITSISummaryTimeseriesCollector:
    def __init__(self, orchestrator_client):
        # Initialize the collector with the orchestrator client.
        # This client is used to interact with the ITSI summary orchestrator service.
        self.orchestrator_client = orchestrator_client
        
        # Initialize context logger that automatically includes summarization ID
        logger = setup_logging.get_logger()
        self.logger = get_context_logger(logger)

    def collect_timeseries(
        self,
        summarization_id: str
    ) -> Tuple[Dict[str, pd.Series], Dict[str, str], Dict[str, str]]:
        """
        Collect time series data for a given summarization_id.
        This includes KPI and entity-level time series from impacted services and their intermediate and leaf services.
        Returns a tuple of (cleaned_series_dict, kpi_entity_to_service_mapping, kpi_id_name_mapping).
        """
        # Initialize local variables for this specific summarization_id
        time_series_data_collection = {}
        kpi_entity_to_service_mapping = {}
        service_to_depth_mapping = {}
        # Step 1: Get directly impacted service IDs, we do not use the impacted_kpis since all the kpis
        # are already associated in the impacted services, which can be retrieved from get_timeline_spls
        impacted_service_ids, impacted_kpi_info = self.orchestrator_client.get_service_kpi_ids(summarization_id)
        # From the impacted_kpi_info, we parse the kpi_id and kpi_name mapping, 
        # kpi name is more readable than kpi id, which provide richer context for downstream LLM analysis 
        kpi_id_name_mapping = {item["kpiid"]: item["kpi_name"] for item in impacted_kpi_info}
        
        if impacted_service_ids:
            # Step 2: Get service topology and trace back to intermediate and leaf services
            merged_service_ids, service_to_depth_mapping = self._get_merged_service_ids(summarization_id, impacted_service_ids)

            # Step 3: Collect time series data (both KPI and entity) for merged service IDs
            time_series_data_collection, kpi_entity_to_service_mapping = self._collect_kpi_and_entity_timeseries(summarization_id, merged_service_ids)
        else:
            # If no impacted services are found, skip service-level collection
            self.logger.info("No service_id found.")

        # Step 4: get start time and end time from get_episode tool to trim the time series data
        steps_checked_metadata = self.orchestrator_client.steps_checked_manager.get_or_initialize_metadata(summarization_id)
        start_time, end_time = steps_checked_metadata['episode_start_time'], steps_checked_metadata['episode_end_time']

        # Step 5: Clean and transform the collected data
        cleaned_series_dict = ITSISummaryTimeseriesCollector.data_collection_cleaning(time_series_data_collection, start_time, end_time)

        return cleaned_series_dict, kpi_entity_to_service_mapping, kpi_id_name_mapping, service_to_depth_mapping

    def _get_merged_service_ids(self, summarization_id: str, impacted_service_ids: List[str]) -> Tuple[List[str], Dict]:
        """
        Given a list of impacted service IDs, return a merged list including their intermediate and leaf node service IDs
        found via topology tracing.
        """
        # Retrieve the topology of the impacted services
        topology = self.orchestrator_client.get_services_topology(summarization_id, impacted_service_ids)

        if topology:
            # Use topology to find all node services connected upstream
            all_node_service_ids, service_to_depth_mapping = self.find_root_cause_services(impacted_service_ids, topology)
            self.logger.info(f"Found intermediate and leaf services: {all_node_service_ids}")

            # Merge and deduplicate impacted and all node service IDs
            return list(set(impacted_service_ids + all_node_service_ids)), service_to_depth_mapping
        else:
            # If topology is unavailable, return only the original impacted services
            self.logger.info(f"No service topology found for {impacted_service_ids}")
            return impacted_service_ids, {}

    def _collect_kpi_and_entity_timeseries(self, summarization_id: str, service_ids: List[str]) -> Tuple[Dict[str, List[pd.DataFrame]], Dict[str, Set[str]]]:
        """
        Fetch KPI and entity-level time series data for the given list of service IDs.
        Returns the collected data as a tuple of (time_series_data_collection, kpi_entity_to_service_mapping).
        """
        time_series_data_collection, kpi_entity_to_service_mapping = self.orchestrator_client.get_kpi_and_entity_ts(summarization_id, service_ids)
        self.logger.info(f"Collected time series and service/kpi/entity mapping for services: {service_ids}")
        return time_series_data_collection, kpi_entity_to_service_mapping
    
    @staticmethod
    def data_collection_cleaning(
        time_series_data_collection: Dict,
        start_time: Union[str, int, float, datetime],
        end_time: Union[str, int, float, datetime],
        lookback_offset: str = DEFAULT_LOOKBACK_OFFSET
    ) -> Dict[str, pd.Series]:
        """
        Cleans and deduplicates the time series data collection,
        each DataFrame contains multiple kpi and entity time series.
        This function extracts the time series data from the DataFrames and
        organizes them into a dictionary, each df is keyed by the KPI ID or entity name.
        Converts from:
            { "kpi": [df1, df2, ...], "entity": [df3, df4, ...] }
        to:
            { "kpi_id"|"entity_name" : pd.Series, ... }

        Applies time filtering and resampling during transformation.

        Parameters:
            time_series_data_collection: Dictionary containing the time series data
            start_time: the episode start time, used to trim the time series data
            end_time: the episode end time, used to trim the time series data
            lookback_offset: the lookback offset, used to adjust the start time,
                this parameter will make start_time earlier than the actual episode start time,
                so make the time window longer than the actual episode time window, we set it to 24h
                for now, this is a temporary solution, we will experiment with different lookback offsets
        Returns:
            Dict mapping each KPI ID or entity name to a cleaned DataFrame.
        """
        cleaned_data = {}
        # add a lookback offset to the start time as an adjustment to our correlation analysis window
        # this adjustment makes the start time earlier than the actual episode start time, so it includes 
        # the time series data before the episode start time
        # ToDo: experiment with different lookback offsets
        effective_start = to_datetime_safe(start_time) - pd.Timedelta(lookback_offset)
        effective_end = to_datetime_safe(end_time)
        
        # Process KPI DataFrames
        for df in time_series_data_collection.get(KPI_TS_KEY, []):

            kpi_series_dict = transfer_df_to_series_dict(
                df,
                id_column=KPI_GROUP_COLUMN,
                start_time=effective_start,
                end_time=effective_end
            )
            for kpi_id, series in kpi_series_dict.items():
                cleaned_data[kpi_id] = series
        # Process Entity DataFrames
        for df in time_series_data_collection.get(ENTITY_TS_KEY, []):
            entity_series_dict = transfer_df_to_series_dict(
                df,
                id_column=ENTITY_GROUP_COLUMN,
                start_time=effective_start,
                end_time=effective_end
            )
            for entity_name, series in entity_series_dict.items():
                cleaned_data[entity_name] = series

        return cleaned_data

    def find_root_cause_services(self, service_ids: List[str], topology: Dict[str, object]) -> Tuple[List[str], Dict[str, int]]:
        """
        Identify intermediate and leaf node services in a topology graph for given service IDs using a stack-based approach.

        Args:
            service_ids (List[str]): Service IDs to find roots for.
            topology (Dict[str, object]): Topology graph with `edges` as a list of {"source", "target"}.

        Returns:
            Tuple[List[str], Dict[str, int]]:
                - List of unique root cause (include intermediate and leaf node) service IDs.
                - Dict mapping each service ID to its sort value (depth-based).
        """
        if not topology or GRAPHS not in topology:
            return [], {}

        # Merge edges from all graphs
        edges = []
        service_to_depth_mapping = {}
        for graph in topology[GRAPHS]:
            edges.extend(graph.get(EDGES, []))
            for node in graph.get(VERTICES, []):
                service_to_depth_mapping[node[ID]] = node[NODE_DEPTH]

        # Build forward graph: source -> list of targets
        graph = {}
        for edge in edges:
            graph.setdefault(edge[SOURCE_VERTEX], []).append(edge[TARGET_VERTEX])

        roots = list(self._trace_root_cause_iteratively(service_ids, graph))
        return roots, service_to_depth_mapping

    def _trace_root_cause_iteratively(self, service_ids: List[str], graph: Dict[str, List[str]]) -> Set[str]:
        """
        Iteratively traverse the topology graph starting from the given service IDs, collecting all reachable nodes.
        Args:
            service_ids (List[str]): Starting service IDs for traversal.
            graph (Dict[str, List[str]]): Maps each service to its downstream children.

        Returns:
            Set[str]: Set of all visited service IDs (including intermediates and leaves).
        """
        # visited is used to collect intermediate and leaf nodes
        # also to avoid revisiting nodes and handle cycles
        visited = set()   
        # Initialize stack with all current service IDs
        stack = [sid for sid in service_ids]  
        roots = set()  # Collect root nodes
        # Perform traversal to find all reachable nodes and determine intermediate and leaf node services
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)

            children = graph.get(current)
            if children:
                # Add all children to stack for further traversal
                stack.extend(children)

        return visited

    @staticmethod
    def replace_kpi_id_with_name(correlation_info: List[Dict[str, object]], kpi_id_name_mapping: Dict[str, str]) -> None:
        """
        Replace KPI IDs in the 'series' field of correlation results with their corresponding KPI names,
        if available in the mapping. If a name is not found, keep the original ID.

        Args:
            correlation_info (List[Dict[str, object]]): List of correlation result dictionaries,
                each containing a 'series' key with a list of KPI/entity IDs.
            kpi_id_name_mapping (Dict[str, str]): Mapping from KPI IDs to KPI names.
        """        
        for item in correlation_info:
            item["series"] = [kpi_id_name_mapping.get(series_id, series_id) for series_id in item["series"]]

    @staticmethod
    def sorted_correlation_by_service_depth(
        correlation_info: List[Dict[str, object]],
        kpi_entity_to_service_mapping: Dict[str, Set[str]],
        service_to_depth_mapping: Dict[str, int]
    ) -> List[Dict[str, object]]:
        """
        Sorts the correlation results by the maximum depth of the services on service topology.
        The first correlation info should with the deepest depth,
        which is the leaf node (backend-towards) service defined by the service topology.

        Args:
            correlation_info (List[Dict[str, object]]): List of correlation result dictionaries.
            kpi_entity_to_service_mapping (Dict[str, Set[str]]): Mapping from series name to set of service IDs.
            service_to_depth_mapping (Dict[str, int]): Mapping from service IDs to their depth values.

        Returns:
            List[Dict[str, object]]: Sorted list of correlation results.
        """
        if not correlation_info or not service_to_depth_mapping or not kpi_entity_to_service_mapping:
            return correlation_info

        def get_max_depth(series_list):
            depths = []
            for series_name in series_list:
                # in correlation_info, series_name can be a KPI ID or an entity name
                # so we need to map it to service IDs
                service_ids = kpi_entity_to_service_mapping.get(series_name, set())
                if service_ids:
                    # With service_ids, we can get the depth of each service ID
                    # the depth is used to sort the correlation results
                    depths.extend([service_to_depth_mapping.get(sid, float('-inf')) for sid in service_ids])
                else:
                    depths.append(float('-inf'))
            # One entity can map to multiple service IDs, so we take the maximum depth
            return max(depths) if depths else float('-inf')
        # Sort correlation_info by the depth of the services in each series
        # the highest depth (most backend-towards) will be at the beginning of the list
        # This is useful for prioritizing root cause services in the correlation results
        # the reverse order is important, since we need the highest depth first (descending).
        return sorted(correlation_info, key=lambda x: get_max_depth(x["series"]), reverse=True)
    
    def collect_and_compute_correlation(
        self,
        summarization_id: str,
        correlation_threshold: float = DEFAULT_CORRELATION_THRESHOLD,
        max_lag: int = DEFAULT_MAX_LAG,
        time_unit: str = RESAMPLE_INTERVAL,
        model: CorrelationModelSelection = CorrelationModelSelection.PEARSON
    ) -> List[Dict[str, object]]:
        """
        Collects time series data for the given summarization_id and computes pairwise lagged correlations.

        Parameters:
            summarization_id: We need summarization_id to collect time series data.
            correlation_threshold: Minimum absolute correlation to include in the results, 
                see detailed description in the 'correlations' function.
            max_lag: Maximum lag steps to consider for correlation, 0 means no lag, 1 means 1 time_unit lag, etc,
                see detailed description in the 'correlations' function.
            time_unit: Time unit for reporting lags, which is the same as the resample interval, 
                the lagging will be lagging * time_unit, e.g. 2 * 5T = 10 minutes
            model: Correlation model to use (e.g., CorrelationModelSelection.PEARSON).

        Returns:
            A list of dictionaries with keys: 'series', 'correlation', 'lag'.
        """
        # Step 1: Collect time series data using the existing method
        cleaned_series_dict, kpi_entity_to_service_mapping, kpi_id_name_mapping, service_to_depth_mapping = self.collect_timeseries(summarization_id)

        # Step 2: Compute correlations
        if model == CorrelationModelSelection.PEARSON:
            correlation_info = correlations(
                cleaned_series_dict,
                kpi_entity_to_service_mapping,
                correlation_threshold=correlation_threshold,
                max_lag=max_lag,
                time_unit=time_unit
            )
            # sort the correlation results by service depth
            correlation_info = ITSISummaryTimeseriesCollector.sorted_correlation_by_service_depth(
                correlation_info,
                kpi_entity_to_service_mapping,
                service_to_depth_mapping
            )
            # replace KPI IDs with names in the correlation results
            ITSISummaryTimeseriesCollector.replace_kpi_id_with_name(correlation_info, kpi_id_name_mapping)
            return correlation_info
        else:
            self.logger.error(f"Unsupported correlation model: {model}")
            return []

class ServiceAncestorFinder:
    @staticmethod
    def find_common_ancestors(service_ids: List[str], topology: Dict[str, object]) -> List[str]:
        """
        Given a list of service IDs and a topology graph, find the common ancestor service ID(s).
        Covering three cases:
            Case1: If there is only one service in service_ids, return that service_id.
            Case2: If there are multiple service IDs, find the lowest common ancestor service ID in the topology graph.
            Case3: If there are multiple graphs in the topology, find the common ancestor in all graphs, 
            this is very rare case that multiple graphs exist, we need to check all graphs to find the common ancestor.
            and return them all.
        the service_ids and topology are not None or empty
        Args:
            service_ids (List[str]): List of service IDs to find the common ancestor for.
            topology (Dict[str, object]): Topology graph with `edges` as a list of {"source", "target"}.

        Returns:
            List[str]: The list contains common ancestor for multiple graphs.
        """
        if len(service_ids) == 1:
            return service_ids

        def build_child_to_parent_graph(edges):
            # Build ancestor graph from edges
            graph = defaultdict(list)
            for edge in edges:
                graph[edge[TARGET_VERTEX]].append(edge[SOURCE_VERTEX])
            return graph

        all_ancestors = []
        # Iterate through each ancestor graph to find common ancestors
        # if multiple graphs exist, we need to check all graphs
        # In most cases, there is only one graph in the topology
        # but we need to handle the case where multiple graphs exist
        for graph in topology.get(GRAPHS, []):
            child_to_parent_graph = build_child_to_parent_graph(graph.get(EDGES, []))
            vertices = {vertex["id"] for vertex in graph.get(VERTICES, [])}
            # Find the services present in this graph
            present_services = [sid for sid in service_ids if sid in vertices]
            if not present_services:
                # If no services are present in this graph, skip to the next graph
                # this should not happen in normal cases, since ITSI should not return such a graph
                # that has no services present, we need to add it to logger
                logger.error(f"Graph/Topology are given without any service id associated with it, for service_ids: {present_services}")
                continue
            if len(present_services) == 1:
                # if there is only one service in the present_services, we can add it directly
                all_ancestors.append(present_services[0])
            else:
                # If there are multiple services, find the common ancestor in this graph
                ancestor = ServiceAncestorFinder.find_common_ancestor_helper(present_services, child_to_parent_graph)
                if ancestor:
                    # If a common ancestor is found, add it to the list
                    all_ancestors.append(ancestor)
        return all_ancestors

    @staticmethod
    def find_common_ancestor_helper(
        service_ids: List[str],
        child_to_parent_graph: Dict[str, List[str]]
    ) -> List[str]:
        """
        For each service ID, find all possible paths from that service up to a root node (a node with no parent).
        Reverse each path so it runs from root to service. Then, compare these paths in parallel to identify
        the deepest node (closest to the leaves) that appears in all paths at the same position.
        This node is the lowest common ancestor shared by all provided service IDs.
        """
        # find the paths from each service_id to the root
        all_service_paths = []
        for sid in service_ids:
            paths = ServiceAncestorFinder.get_paths_to_root(sid, child_to_parent_graph)
            # Reverse each path so it runs from root to service (leaf)
            all_service_paths.append([path[::-1] for path in paths])
        # Compare all paths in parallel to find the deepest common ancestor.
        # For each position in the paths (from root to leaf), check if all nodes are the same.
        # The last matching node across all paths is the lowest common ancestor.
        # If a mismatch occurs, stop and return the most recent common node.
        common_ancestor = None # Will store the deepest common ancestor found (could be root or a descendant)
        max_depth = -1
        for path_combo in product(*all_service_paths):
            ancestor = None
            for nodes in zip(*path_combo):
                if all(n == nodes[0] for n in nodes):
                    ancestor = nodes[0]
                else:
                    break
            if ancestor is not None:
                depth = path_combo[0].index(ancestor)
                if depth > max_depth:
                    common_ancestor = ancestor
                    max_depth = depth
        return common_ancestor

    @staticmethod
    def get_paths_to_root(node, graph):
        """
        Iteratively find all paths from node up to any root (node with no parent).
        Each path is a list [node, ..., root].
        """
        all_paths = []  # This will collect all the paths from node to any root
        # Stack for DFS: each element is a tuple (current_node, current_path)
        stack = [(node, [node])]
        
        while stack:
            current, path = stack.pop()
            parents = graph.get(current)
            # If current node has no parents, we've reached a root
            if not parents:
                all_paths.append(path)
            else:
                # For each parent, add a new tuple to the stack with the updated path
                for parent in parents:
                    # Add the parent to the current path (path + [parent])
                    stack.append((parent, path + [parent]))
        return all_paths