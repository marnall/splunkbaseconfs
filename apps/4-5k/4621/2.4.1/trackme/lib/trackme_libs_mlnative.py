#!/usr/bin/env python
# coding=utf-8

"""
TrackMe Native Outlier Detection Library

Implements a native DensityFunction-equivalent algorithm using scipy directly,
replacing the dependency on Splunk's MLTK DensityFunction which is broken in
AI Toolkit 5.7.0+ (pandas 3.0 removed include_groups parameter from groupby().apply()).

This library provides:
- Distribution fitting (normal, exponential, gaussian_kde, beta, auto)
- Per-group fitting using simple for-loops (no groupby().apply())
- Boundary computation from density thresholds
- KVstore-based model persistence
- Output compatible with TrackMe's existing BoundaryRanges/LowerBound/UpperBound pipeline

Author: TrackMe Limited
Copyright: 2022-2026, TrackMe Limited, U.K.
"""

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

import json
import time
import logging
from trackme_libs_logging import get_effective_logger

import numpy as np

# scipy imports - these are available via Splunk's Python Scientific Computing package
from scipy import stats
from scipy.stats import wasserstein_distance, ks_2samp

# Constants
NUMERIC_PRECISION = 4
MAX_DEFAULT_PARAM_SIZE = 10000
REPLACE_ZERO_STD = 0.000001
MIN_DATA_SIZE_TO_FIT = 10
BINARY_SEARCH_POINTS = 1000
BINARY_SEARCH_MAX_ITER = 100
BINARY_SEARCH_TOLERANCE = 0.001


class DistributionFitError(Exception):
    """Raised when a distribution cannot be fitted to the data."""

    pass


class NativeDistribution:
    """Base class for probability distributions."""

    def __init__(self):
        self._params = {}

    def fit(self, data):
        """Fit the distribution to data. Returns distance score."""
        raise NotImplementedError

    def compute_boundaries(self, lower_threshold, upper_threshold):
        """Compute anomaly boundaries from density thresholds.
        Returns (lower_bound, upper_bound, boundary_ranges_str).
        """
        raise NotImplementedError

    def to_dict(self):
        """Serialize distribution parameters to a dict for storage."""
        raise NotImplementedError

    @classmethod
    def from_dict(cls, params):
        """Reconstruct distribution from stored parameters."""
        raise NotImplementedError

    def _get_distance(self, data, metric="wasserstein"):
        """Compute distance between original data and fitted distribution samples."""
        samples = self._sample(len(data))
        if metric == "wasserstein":
            return wasserstein_distance(data, samples)
        elif metric == "ks":
            return ks_2samp(data, samples)[0]
        else:
            return wasserstein_distance(data, samples)

    def _sample(self, size):
        """Generate random samples from the fitted distribution."""
        raise NotImplementedError


class NormalDistribution(NativeDistribution):
    """Normal (Gaussian) distribution."""

    def __init__(self):
        super().__init__()
        self._mean = None
        self._std = None

    def fit(self, data):
        self._mean, self._std = stats.norm.fit(data)
        if self._std == 0:
            self._std = REPLACE_ZERO_STD
        return self._get_distance(data)

    def compute_boundaries(self, lower_threshold, upper_threshold):
        dist = stats.norm(loc=self._mean, scale=self._std)
        lower_bound = round(float(dist.ppf(lower_threshold)), NUMERIC_PRECISION)
        upper_bound = round(float(dist.ppf(1.0 - upper_threshold)), NUMERIC_PRECISION)
        boundary_ranges = self._format_boundary_ranges(lower_bound, upper_bound, lower_threshold, upper_threshold)
        return lower_bound, upper_bound, boundary_ranges

    def _sample(self, size):
        return stats.norm(loc=self._mean, scale=self._std).rvs(size=size)

    def to_dict(self):
        return {
            "type": "norm",
            "mean": self._mean,
            "std": self._std,
        }

    @classmethod
    def from_dict(cls, params):
        d = cls()
        d._mean = params["mean"]
        d._std = params["std"]
        return d

    @staticmethod
    def _format_boundary_ranges(lower_bound, upper_bound, lower_threshold, upper_threshold):
        return f"-Infinity:{lower_bound}:{round(lower_threshold, NUMERIC_PRECISION)}\n{upper_bound}:Infinity:{round(upper_threshold, NUMERIC_PRECISION)}"


class ExponentialDistribution(NativeDistribution):
    """Exponential distribution."""

    def __init__(self):
        super().__init__()
        self._loc = None
        self._scale = None
        self._min = None

    def fit(self, data):
        if np.allclose(data, data[0], atol=0.0001):
            raise DistributionFitError("All values are approximately equal, cannot fit exponential distribution.")
        self._loc, self._scale = stats.expon.fit(data)
        self._min = float(np.min(data))
        return self._get_distance(data)

    def compute_boundaries(self, lower_threshold, upper_threshold):
        dist = stats.expon(loc=self._loc, scale=self._scale)
        lower_bound = round(self._min, NUMERIC_PRECISION)
        upper_bound = round(float(dist.ppf(1.0 - upper_threshold)), NUMERIC_PRECISION)
        boundary_ranges = f"-Infinity:{lower_bound}:0\n{upper_bound}:Infinity:{round(upper_threshold, NUMERIC_PRECISION)}"
        return lower_bound, upper_bound, boundary_ranges

    def _sample(self, size):
        return stats.expon(loc=self._loc, scale=self._scale).rvs(size=size)

    def to_dict(self):
        return {
            "type": "expon",
            "loc": self._loc,
            "scale": self._scale,
            "min": self._min,
        }

    @classmethod
    def from_dict(cls, params):
        d = cls()
        d._loc = params["loc"]
        d._scale = params["scale"]
        d._min = params["min"]
        return d


class GaussianKDEDistribution(NativeDistribution):
    """Gaussian Kernel Density Estimation distribution."""

    def __init__(self):
        super().__init__()
        self._data = None
        self._mean = None
        self._std = None
        self._bandwidth = None
        self._min = None
        self._max = None

    def fit(self, data):
        if len(data) <= 1:
            raise DistributionFitError("Not enough data points for KDE.")
        if np.allclose(data, data[0], atol=0.0001):
            raise DistributionFitError("All values are approximately equal, cannot fit KDE.")

        # Downsample if needed
        if len(data) > MAX_DEFAULT_PARAM_SIZE:
            self._data = np.random.choice(data, size=MAX_DEFAULT_PARAM_SIZE, replace=False)
        else:
            self._data = data.copy()

        self._mean = float(np.mean(self._data))
        self._std = float(np.std(self._data))
        self._min = float(np.min(self._data))
        self._max = float(np.max(self._data))

        if self._std == 0:
            self._std = REPLACE_ZERO_STD

        kde = stats.gaussian_kde(self._data)
        self._bandwidth = float(kde.covariance_factor() * self._std)

        return self._get_distance(data)

    def compute_boundaries(self, lower_threshold, upper_threshold):
        kde = stats.gaussian_kde(self._data)

        # Use binary search to find anomaly regions
        data_range = self._max - self._min
        x_min = self._min - 0.1 * data_range
        x_max = self._max + 0.1 * data_range
        x_range = np.linspace(x_min, x_max, BINARY_SEARCH_POINTS)

        # Find lower boundary via binary search on area
        lower_bound = self._find_lower_boundary(kde, x_range, lower_threshold)
        upper_bound = self._find_upper_boundary(kde, x_range, upper_threshold)

        lower_bound = round(lower_bound, NUMERIC_PRECISION)
        upper_bound = round(upper_bound, NUMERIC_PRECISION)

        boundary_ranges = f"-Infinity:{lower_bound}:{round(lower_threshold, NUMERIC_PRECISION)}\n{upper_bound}:Infinity:{round(upper_threshold, NUMERIC_PRECISION)}"
        return lower_bound, upper_bound, boundary_ranges

    def _find_lower_boundary(self, kde, x_range, threshold):
        """Binary search for the x-value where the left tail area equals the threshold."""
        lo = x_range[0]
        hi = x_range[-1]
        mid = lo

        for _ in range(BINARY_SEARCH_MAX_ITER):
            mid = (lo + hi) / 2.0
            area = kde.integrate_box_1d(float('-inf'), mid)
            if abs(area - threshold) < threshold * BINARY_SEARCH_TOLERANCE:
                break
            if area < threshold:
                lo = mid
            else:
                hi = mid

        return mid

    def _find_upper_boundary(self, kde, x_range, threshold):
        """Binary search for the x-value where the right tail area equals the threshold."""
        lo = x_range[0]
        hi = x_range[-1]
        mid = hi

        for _ in range(BINARY_SEARCH_MAX_ITER):
            mid = (lo + hi) / 2.0
            area = kde.integrate_box_1d(mid, float('inf'))
            if abs(area - threshold) < threshold * BINARY_SEARCH_TOLERANCE:
                break
            if area < threshold:
                hi = mid
            else:
                lo = mid

        return mid

    def _sample(self, size):
        kde = stats.gaussian_kde(self._data)
        return kde.resample(size)[0]

    def to_dict(self):
        return {
            "type": "gaussian_kde",
            "data": self._data.tolist(),
            "mean": self._mean,
            "std": self._std,
            "bandwidth": self._bandwidth,
            "min": self._min,
            "max": self._max,
        }

    @classmethod
    def from_dict(cls, params):
        d = cls()
        d._data = np.array(params["data"])
        d._mean = params["mean"]
        d._std = params["std"]
        d._bandwidth = params["bandwidth"]
        d._min = params["min"]
        d._max = params["max"]
        return d


class BetaDistribution(NativeDistribution):
    """Beta distribution (data normalized to [0, 1] range)."""

    def __init__(self):
        super().__init__()
        self._alpha = None
        self._beta_param = None
        self._loc = None
        self._scale = None
        self._data_min = None
        self._data_max = None

    def fit(self, data):
        if np.allclose(data, data[0], atol=0.0001):
            raise DistributionFitError("All values are approximately equal, cannot fit beta distribution.")

        self._data_min = float(np.min(data))
        self._data_max = float(np.max(data))

        # Normalize to [0, 1]
        data_range = self._data_max - self._data_min
        if data_range == 0:
            raise DistributionFitError("Data range is zero, cannot fit beta distribution.")

        normalized = (data - self._data_min) / data_range

        # Clip to (0, 1) to avoid boundary issues
        normalized = np.clip(normalized, 1e-10, 1.0 - 1e-10)

        try:
            # Constrain loc=0 and scale=1 since data is already normalized to [0,1].
            # Without this, scipy may fit non-trivial loc/scale values, and then
            # compute_boundaries() and _sample() would double-transform because
            # dist.ppf() already incorporates loc/scale.
            self._alpha, self._beta_param, self._loc, self._scale = stats.beta.fit(
                normalized, floc=0, fscale=1
            )

            # Fallback to method of moments if scipy gives bad params
            if self._alpha <= 0 or self._beta_param <= 0:
                self._fit_method_of_moments(normalized)
        except Exception:
            self._fit_method_of_moments(normalized)

        return self._get_distance(data)

    def _fit_method_of_moments(self, normalized_data):
        """Method of moments estimation for beta distribution parameters."""
        m = float(np.mean(normalized_data))
        v = float(np.sum((normalized_data - m) ** 2) / len(normalized_data))
        if v == 0:
            raise DistributionFitError("Zero variance, cannot fit beta distribution.")
        u = ((m * (1 - m)) / v) - 1
        self._alpha = max(m * u, 1e-6)
        self._beta_param = max((1 - m) * u, 1e-6)
        self._loc = 0.0
        self._scale = 1.0

    def compute_boundaries(self, lower_threshold, upper_threshold):
        dist = stats.beta(self._alpha, self._beta_param, loc=self._loc, scale=self._scale)

        # Compute boundaries in normalized space
        norm_lower = float(dist.ppf(lower_threshold))
        norm_upper = float(dist.ppf(1.0 - upper_threshold))

        # Rescale back to original data range
        data_range = self._data_max - self._data_min
        lower_bound = round(norm_lower * data_range + self._data_min, NUMERIC_PRECISION)
        upper_bound = round(norm_upper * data_range + self._data_min, NUMERIC_PRECISION)

        boundary_ranges = f"-Infinity:{lower_bound}:{round(lower_threshold, NUMERIC_PRECISION)}\n{upper_bound}:Infinity:{round(upper_threshold, NUMERIC_PRECISION)}"
        return lower_bound, upper_bound, boundary_ranges

    def _sample(self, size):
        samples = stats.beta.rvs(self._alpha, self._beta_param, loc=self._loc, scale=self._scale, size=size)
        # Rescale to original range
        data_range = self._data_max - self._data_min
        return samples * data_range + self._data_min

    def to_dict(self):
        return {
            "type": "beta",
            "alpha": self._alpha,
            "beta_param": self._beta_param,
            "loc": self._loc,
            "scale": self._scale,
            "data_min": self._data_min,
            "data_max": self._data_max,
        }

    @classmethod
    def from_dict(cls, params):
        d = cls()
        d._alpha = params["alpha"]
        d._beta_param = params["beta_param"]
        d._loc = params["loc"]
        d._scale = params["scale"]
        d._data_min = params["data_min"]
        d._data_max = params["data_max"]
        return d


# Distribution factory mapping
DISTRIBUTION_CLASSES = {
    "norm": NormalDistribution,
    "expon": ExponentialDistribution,
    "gaussian_kde": GaussianKDEDistribution,
    "beta": BetaDistribution,
}

# Distribution type names for auto-selection
AUTO_DISTRIBUTION_ORDER = ["norm", "expon", "gaussian_kde", "beta"]


def get_distribution(dist_type):
    """Factory function to create a distribution instance."""
    if dist_type not in DISTRIBUTION_CLASSES:
        raise ValueError(f"Unknown distribution type: {dist_type}")
    return DISTRIBUTION_CLASSES[dist_type]()


def auto_select_distribution(data, exclude_dist=None):
    """
    Auto-select the best fitting distribution using wasserstein distance.

    Args:
        data: numpy array of data values
        exclude_dist: list of distribution types to exclude (e.g. ["beta", "expon"])

    Returns:
        (distribution_instance, selected_type_name, distance_score)
    """
    candidates = AUTO_DISTRIBUTION_ORDER[:]
    if exclude_dist:
        # Normalize exclusion names
        exclude_set = set()
        for e in exclude_dist:
            e_lower = e.strip().lower()
            # Map common aliases
            if e_lower in ("normal", "norm"):
                exclude_set.add("norm")
            elif e_lower in ("exponential", "expon"):
                exclude_set.add("expon")
            elif e_lower in ("kde", "gaussian_kde"):
                exclude_set.add("gaussian_kde")
            elif e_lower in ("beta",):
                exclude_set.add("beta")
            else:
                exclude_set.add(e_lower)
        candidates = [c for c in candidates if c not in exclude_set]

    fitted = []
    for dist_type in candidates:
        try:
            dist = get_distribution(dist_type)
            score = dist.fit(data)
            fitted.append((dist, dist_type, score))
        except (DistributionFitError, Exception) as e:
            get_effective_logger().debug(f"Distribution {dist_type} failed to fit: {e}")
            continue

    if not fitted:
        raise DistributionFitError("No distribution could be fitted to the data.")

    # Select the one with minimum distance
    best = min(fitted, key=lambda x: x[2])
    return best


def native_fit(data_values, group_values, feature_name, lower_threshold, upper_threshold,
               dist_type="auto", exclude_dist=None):
    """
    Fit a density function model to data, grouped by group_values.

    This is the core fit function that replaces Splunk's MLTK DensityFunction fit.
    It uses simple for-loop iteration over groups instead of pandas groupby().apply(),
    avoiding the pandas 3.0 include_groups regression.

    Args:
        data_values: list of dicts, each with at least feature_name and optionally group fields
        group_values: list of group column names (e.g. ["factor"]) or empty list for no grouping
        feature_name: name of the numeric feature to model
        lower_threshold: float, density threshold for lower bound (e.g. 0.005)
        upper_threshold: float, density threshold for upper bound (e.g. 0.005)
        dist_type: distribution type: "auto", "norm", "expon", "gaussian_kde", "beta"
                   or "DensityFunction" (alias for "auto")
        exclude_dist: list of distribution types to exclude from auto-selection

    Returns:
        dict: model definition containing:
            - groups: dict mapping group_key -> {distribution params, boundaries}
            - feature_name: the feature name
            - group_fields: the group column names
            - lower_threshold: the lower threshold used
            - upper_threshold: the upper threshold used
            - dist_type: the requested distribution type
            - fitted_at: epoch timestamp
    """
    # Normalize algorithm name
    if dist_type in ("DensityFunction", "auto", "Auto"):
        dist_type = "auto"

    # Validate thresholds - must be in (0, 1) for valid ppf() computation
    if lower_threshold <= 0 or lower_threshold >= 1:
        get_effective_logger().warning(f'Invalid lower_threshold={lower_threshold}, must be in (0, 1), using 0.005')
        lower_threshold = 0.005
    if upper_threshold <= 0 or upper_threshold >= 1:
        get_effective_logger().warning(f'Invalid upper_threshold={upper_threshold}, must be in (0, 1), using 0.005')
        upper_threshold = 0.005

    model = {
        "feature_name": feature_name,
        "group_fields": group_values,
        "lower_threshold": lower_threshold,
        "upper_threshold": upper_threshold,
        "dist_type": dist_type,
        "exclude_dist": exclude_dist,
        "fitted_at": time.time(),
        "groups": {},
    }

    # Group the data using simple dict-based grouping
    if group_values:
        groups = {}
        for row in data_values:
            # Build group key from the group field values
            key_parts = []
            for gf in group_values:
                val = row.get(gf, "")
                key_parts.append(str(val))
            group_key = "_".join(key_parts) if key_parts else "__default__"

            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(row)
    else:
        groups = {"__default__": data_values}

    # Fit each group using a simple for loop (no groupby().apply()!)
    for group_key, group_rows in groups.items():
        # Extract the numeric feature values
        values = []
        for row in group_rows:
            try:
                v = float(row[feature_name])
                if not np.isnan(v) and not np.isinf(v):
                    values.append(v)
            except (KeyError, ValueError, TypeError):
                continue

        if len(values) < MIN_DATA_SIZE_TO_FIT:
            get_effective_logger().warning(
                f"Group '{group_key}' has only {len(values)} data points "
                f"(minimum {MIN_DATA_SIZE_TO_FIT}), skipping."
            )
            model["groups"][group_key] = {
                "status": "insufficient_data",
                "count": len(values),
            }
            continue

        data_array = np.array(values, dtype=np.float64)

        try:
            if dist_type == "auto":
                dist_instance, selected_type, score = auto_select_distribution(
                    data_array, exclude_dist=exclude_dist
                )
            else:
                dist_instance = get_distribution(dist_type)
                score = dist_instance.fit(data_array)
                selected_type = dist_type

            # Compute boundaries
            lower_bound, upper_bound, boundary_ranges = dist_instance.compute_boundaries(
                lower_threshold, upper_threshold
            )

            model["groups"][group_key] = {
                "status": "fitted",
                "count": len(values),
                "distribution": dist_instance.to_dict(),
                "selected_type": selected_type,
                "distance_score": round(score, NUMERIC_PRECISION),
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "boundary_ranges": boundary_ranges,
            }

        except DistributionFitError as e:
            get_effective_logger().warning(f"Group '{group_key}' fit failed: {e}")
            model["groups"][group_key] = {
                "status": "fit_error",
                "count": len(values),
                "error": str(e),
            }
        except Exception as e:
            get_effective_logger().error(f"Group '{group_key}' unexpected error: {e}")
            model["groups"][group_key] = {
                "status": "error",
                "count": len(values),
                "error": str(e),
            }

    return model


def native_apply(data_rows, model, feature_name=None, group_fields=None):
    """
    Apply a fitted model to data rows, computing boundaries and outlier flags.

    This is the core apply function that replaces Splunk's MLTK DensityFunction apply.

    Args:
        data_rows: list of dicts, each row of data to evaluate
        model: dict, the model definition from native_fit() or loaded from KVstore
        feature_name: override feature name (defaults to model's feature_name)
        group_fields: override group fields (defaults to model's group_fields)

    Returns:
        list of dicts: the input rows augmented with:
            - BoundaryRanges: string with boundary range info
            - LowerBound: numeric lower boundary
            - UpperBound: numeric upper boundary
            - IsOutlier: 0 or 1
    """
    if feature_name is None:
        feature_name = model["feature_name"]
    if group_fields is None:
        group_fields = model.get("group_fields", [])

    results = []
    for row in data_rows:
        # Determine group key
        if group_fields:
            key_parts = []
            for gf in group_fields:
                val = row.get(gf, "")
                key_parts.append(str(val))
            group_key = "_".join(key_parts) if key_parts else "__default__"
        else:
            group_key = "__default__"

        # Get group model
        group_model = model["groups"].get(group_key)

        if not group_model or group_model.get("status") != "fitted":
            # No model for this group, cannot compute boundaries
            row["BoundaryRanges"] = ""
            row["LowerBound"] = 0
            row["UpperBound"] = 0
            row["IsOutlier"] = 0
            results.append(row)
            continue

        # Get boundaries from model (pre-computed during fit)
        lower_bound = group_model["lower_bound"]
        upper_bound = group_model["upper_bound"]
        boundary_ranges = group_model["boundary_ranges"]

        # If we need to re-compute boundaries (e.g., threshold changed), do it from stored distribution
        # For now, use the pre-computed values from the model.
        #
        # Coerce to native Python float: some distribution paths (e.g. the
        # gaussian_kde binary search over a numpy linspace) return numpy
        # scalars, and numpy >= 2.0 renders those as the repr string
        # "np.float64(7599.05)" when serialised to the search pipeline. That
        # non-numeric token breaks every downstream `isnum()` / arithmetic
        # consumer (it silently floored TrackMe adaptive delay's UpperBound to
        # 0). Emitting a plain float keeps the output a true drop-in for MLTK's
        # `fit DensityFunction`.
        row["BoundaryRanges"] = boundary_ranges
        try:
            row["LowerBound"] = float(lower_bound)
        except (ValueError, TypeError):
            row["LowerBound"] = lower_bound
        try:
            row["UpperBound"] = float(upper_bound)
        except (ValueError, TypeError):
            row["UpperBound"] = upper_bound

        # Determine IsOutlier
        raw_value = row.get(feature_name)
        if raw_value is None or raw_value == "":
            # Feature is missing or empty — cannot classify, leave as not outlier
            row["IsOutlier"] = 0
        else:
            try:
                value = float(raw_value)
                if value < lower_bound or value > upper_bound:
                    row["IsOutlier"] = 1
                else:
                    row["IsOutlier"] = 0
            except (ValueError, TypeError):
                row["IsOutlier"] = 0

        results.append(row)

    return results


def save_model_to_kvstore(service, collection_name, model_key, model_data, logger=None):
    """
    Save a fitted model to a KVstore collection.

    Args:
        service: splunklib.client.Service instance
        collection_name: name of the KVstore collection
        model_key: unique key for this model (typically the entity_outlier ID)
        model_data: the model dict from native_fit()
        logger: optional logger instance

    Returns:
        bool: True on success
    """
    if logger is None:
        logger = logging.getLogger()

    try:
        collection = service.kvstore[collection_name]
    except Exception as e:
        logger.error(f"Failed to access KVstore collection '{collection_name}': {e}")
        raise

    # Serialize model to JSON string
    model_json = json.dumps(model_data)

    record = {
        "_key": model_key,
        "model_data": model_json,
        "model_type": "native_density_function",
        "feature_name": model_data.get("feature_name", ""),
        "dist_type": model_data.get("dist_type", "auto"),
        "fitted_at": str(model_data.get("fitted_at", "")),
        "group_count": str(len(model_data.get("groups", {}))),
        "mtime": str(time.time()),
    }

    try:
        # Try update first, insert if not found
        try:
            collection.data.update(model_key, json.dumps(record))
        except Exception:
            collection.data.insert(json.dumps(record))

        logger.info(f"Model '{model_key}' saved to KVstore collection '{collection_name}'")
        return True

    except Exception as e:
        logger.error(f"Failed to save model '{model_key}' to KVstore: {e}")
        raise


def load_model_from_kvstore(service, collection_name, model_key, logger=None):
    """
    Load a fitted model from a KVstore collection.

    Args:
        service: splunklib.client.Service instance
        collection_name: name of the KVstore collection
        model_key: unique key for this model
        logger: optional logger instance

    Returns:
        dict: the model data, or None if not found
    """
    if logger is None:
        logger = logging.getLogger()

    try:
        collection = service.kvstore[collection_name]
    except Exception as e:
        logger.error(f"Failed to access KVstore collection '{collection_name}': {e}")
        return None

    try:
        query = json.dumps({"_key": model_key})
        records = collection.data.query(query=query)
        if records:
            model_json = records[0].get("model_data")
            if model_json:
                return json.loads(model_json)
        return None

    except Exception as e:
        logger.error(f"Failed to load model '{model_key}' from KVstore: {e}")
        return None


def delete_model_from_kvstore(service, collection_name, model_key, logger=None):
    """
    Delete a model from a KVstore collection.

    Args:
        service: splunklib.client.Service instance
        collection_name: name of the KVstore collection
        model_key: unique key for this model
        logger: optional logger instance

    Returns:
        bool: True on success, False if not found
    """
    if logger is None:
        logger = logging.getLogger()

    try:
        collection = service.kvstore[collection_name]
        collection.data.delete_by_id(model_key)
        logger.info(f"Model '{model_key}' deleted from KVstore collection '{collection_name}'")
        return True

    except Exception as e:
        logger.debug(f"Model '{model_key}' not found or could not be deleted: {e}")
        return False


def get_model_collection_name(tenant_id):
    """
    Get the KVstore collection name for native ML models for a given tenant.

    Args:
        tenant_id: the tenant identifier

    Returns:
        str: collection name
    """
    return f"kv_trackme_native_ml_models_tenant_{tenant_id}"
