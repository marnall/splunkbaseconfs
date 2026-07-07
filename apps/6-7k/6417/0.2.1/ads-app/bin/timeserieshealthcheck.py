import exec_anaconda
exec_anaconda.exec_anaconda()

import os
import sys
import json
import math
import logging
import datetime

import numpy as np

from dateutil import parser

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from splunklib.searchcommands import dispatch, ReportingCommand, Configuration, Option, validators

logger = logging.getLogger(__name__)


@Configuration(requires_preop=True)
class TimeSeriesHealthCheck(ReportingCommand):
    """
    Given a time series and its timestamps, estimates the "health" of the series.
    By "health", we mean how generally well-suited the time series is to downstream 
    statistical analysis/modeling tasks such as forecasting or anomaly detection.

    Args:
        time_series: List of numeric values
        timestamps: List of Unix-seconds timestamps, 1 for each value in the time_series.

    Returns:
        health_score, int, a three-leveled indicator of the time series' health (0=bad, 1=okay, 2=good)
        health_explanation, string, a text description of why the time series was assigned the given health_score.

    Usage:
        | inputlookup kpi.csv
        | timeserieshealthcheck field_name=input
    """

    field_name = Option(require=True)
    time_value_pairs = []

    @Configuration()
    def map(self, events):
        ts = [(e['_time'], e[self.field_name]) for e in events]
        yield {'time_series': ts}

    def reduce(self, events):
        chunk_time_value_pairs = [json.loads(pair_str) for pair_str in list(events)[0]['time_series']]
        self.time_value_pairs.extend(chunk_time_value_pairs)
        if self._finished:
            sorted_time_value_pairs = [
                (self.convert_to_unix_timestamp(time), self.convert_to_value(val))
                for time, val in self.time_value_pairs
            ]
            sorted_time_value_pairs.sort()  # Sort the series in chronological order
            timestamps = [pair[0] for pair in sorted_time_value_pairs]
            values = [pair[1] for pair in sorted_time_value_pairs]
            health_score, explanation = self.compute_health_score(values, timestamps)
            yield {'health_score': health_score,
                   'health_explanation': explanation}

    @staticmethod
    def compute_health_score(time_series, timestamps):
        if len(time_series) < 5:
            return 0, 'Field contains too few values for analysis.'

        nan_score = TimeSeriesHealthCheck.compute_nan_score(time_series)
        timestamp_score = TimeSeriesHealthCheck.compute_timestamp_score(timestamps)
        magnitude_score = TimeSeriesHealthCheck.compute_magnitude_score(time_series)
        diversity_score = TimeSeriesHealthCheck.compute_diversity_score(time_series)
        smoothness_score = TimeSeriesHealthCheck.compute_smoothness_score(time_series)

        # 'Bad' Case 1: Nans. Check in there are NaNs. If so, return 0.
        if nan_score < 1:
            return 0, 'Field contains missing or non-numeric values.'

        # 'Bad' Case 2: Timestamps. Check if timestamps are evenly spaced. 1.0 indicates perfectly
        # spaced, and monthly-spaced data is ~0.82 (months are different lengths).
        # Therefore, monthly will be the approximate lower-bound of what we'll accept.
        if timestamp_score < 0.85:
            return 0, 'ERROR: Timestamps are unevenly spaced. The app will not succesfully run on this field.'        

        #'Bad' Case 3: Diversity. Extremely low diversity of distinct values.
        # This implies the dataset is likely categorical or relatively
        # constant with spikes, which is unfavorable for forecasting.
        if diversity_score < 0.1:
            return 0, 'Field contains very few discrete values, and so might be better interpreted as categorical than numeric.'

        if len(time_series) > 10000:
            return 1, 'Results are truncated: ADS and the corresponding visualization are currently configured to operate on time series of at most 10,000 points.'

        # 'Okay' Case 1: Magnitude. Check if the magnitude difference between the min and
        # max value of the dataset. If it's >8, return 0 (data-vis breaks).
        if magnitude_score == 0:
            return 1, 'Field ranges over 8 or more orders of magnitude; numerical issues may disrupt results.'

        # 'Okay' Case 2: Smoothness. Check to see how predictive each point is of its
        # successor. The more predictive, the more likely forecasting is to do well.
        if smoothness_score < 0.5:
            return 1, 'Field exhibits high volatility/low smoothness, and so may contain insufficient information to make quality predictions.'

        # 'Okay' Case 3: Diversity. There is a moderate number of diverse values, but
        # given how this score is calculated, this may indicate a large number of
        # outliers which stretch the distribution, and make forecasting difficult.
        if diversity_score < 0.25:
            return 1, 'Field contains only a moderate number of discrete values; if there are obvious anomalies, it may be best to manually remove them before analysis.'

        # 'Good' Case: No problems were found in the above checks
        return 2, 'No issues detected. This field is ready for analysis!'

    @staticmethod
    def compute_nan_score(series):
        """
        NaN-score is proportional to the amount of NaNs in the data.
        All NaNs = 0, no NaNs = 1, and linear interpolation.
        """
        nan_count = sum(int(math.isnan(val)) for val in series)
        return 1 - (nan_count / len(series))

    @staticmethod
    def compute_timestamp_score(times):
        """
        Compute the spacing between timestamps. A score is calculated by computing the
        standard deviation and median of the timestamp differences, and using rules:
        - STD <= (std_lower_bound * median): score = 1
        - STD >= (std_upper_bound * median): score = 0
        - linear interpolation in between
        """
        std_lower_bound = 0.01
        std_upper_bound = 0.1

        times = sorted(times)
        diffs = [t2 - t1 for t1, t2 in zip(times[:-1], times[1:])]
        diff_median = np.median(diffs)
        diff_std = np.std(diffs)
        std_ratio = diff_std / max(diff_median, 1e-10)
        score = TimeSeriesHealthCheck.convert_to_score(std_ratio, std_lower_bound, std_upper_bound)
        return score

    @staticmethod
    def compute_magnitude_score(series):
        """
        Computes the min and max magnitude of the series, and converts the difference
        to a score. The score is [0, 1], where 0 indicates difference >= 8 orders
        of magnitude, 1 indicates the same order of magnitude, and linear
        interpolation in between. Does not account for negatives, and anything
        <= 1 is clamped to a value of 1.

        TODO: investigate:
        1) If it's order of magnitude between values, or the max magnitude
        2) If it's linear or exponential relationship as mag diff increases
        """
        non_nan_vals = [val for val in series if not math.isnan(val)]
        min_magnitude = math.log10(max(min(non_nan_vals), 1))
        max_magnitude = math.log10(max(non_nan_vals + [1]))
        mag_diff = max_magnitude - min_magnitude
        score = TimeSeriesHealthCheck.convert_to_score(mag_diff, 0, 8)
        return score

    @staticmethod
    def compute_diversity_score_deprecated1(series):
        """
        Diversity-score is the number of unique values in the series as a
        percent of the series' length.
        """
        unique_val_count = len(set(series))
        score = unique_val_count / len(series)
        return score

    @staticmethod
    def compute_diversity_score(series):
        """
        Diversity-score is the number of unique values in the series as a
        percent of the series' length.
        """
        cutoff_perc = 1
        min_bins = 1
        max_bins = 100
        num_bins = max(min_bins, min(max_bins, int(round(len(series) / 10))))

        # Sort non-NaN values
        sorted_vals = sorted(val for val in series if not math.isnan(val))

        # Chop off outliers on both ends
        cutoff = int(round(cutoff_perc / 100 * len(sorted_vals)))
        non_extreme_vals = sorted_vals[cutoff: len(sorted_vals) - 1 - cutoff]

        # Bin the remaining values
        bins = [0] * num_bins
        min_val = min(non_extreme_vals)
        val_range = max(max(non_extreme_vals) - min_val, 1e-7)
        for val in non_extreme_vals:
            bin_num = int(round((val - min_val) / val_range * (num_bins - 1)))
            bins[bin_num] += 1

        # Compute "error" from uniform using MSE
        worst_binning = [len(non_extreme_vals)] + [0] * (num_bins - 1)
        expected_count = len(non_extreme_vals) / num_bins
        error = sum(abs(bin_count - expected_count) for bin_count in bins)
        max_error = sum(abs(bin_count - expected_count) for bin_count in worst_binning)
        score = 1 - (error / max_error)

        return score

    @staticmethod
    def compute_smoothness_score(series):
        """
        Use the lag-1 correlation as a measure of smoothness.

        Correlations of -1 or 1 indicate the previous point is predictive of the next,
        while a correlation of 0 means there's no correlation.
        """
        non_nan_vals = [val for val in series if not math.isnan(val)]
        coeff = np.corrcoef(non_nan_vals[:-1], non_nan_vals[1:])[0][1]
        coeff = 1 if math.isnan(coeff) else coeff  # Only occurs when perfectly flat
        score = abs(coeff)
        return score

    @staticmethod
    def convert_to_score(val, lower_bound, upper_bound):
        bounded_val = max(lower_bound, min(val, upper_bound))
        score = abs(bounded_val - upper_bound) / (upper_bound - lower_bound)
        return score

    @staticmethod
    def convert_to_unix_timestamp(timestamp):
        # Check if it's already unix timestamp
        try:
            return int(round(float(timestamp)))
        except:
            pass

        # If it's not a unix timestamp, parse it
        date = parser.parse(timestamp)
        unix_seconds = datetime.datetime.timestamp(date)
        unix_timestamp = int(round(unix_seconds))
        return unix_timestamp

    @staticmethod
    def convert_to_value(value_str):
        try:
            return float(value_str)
        except:
            return float('nan')


dispatch(TimeSeriesHealthCheck, sys.argv, sys.stdin, sys.stdout, __name__)
