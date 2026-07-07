import sys
if sys.version_info[0] > 2:
    # Eliminate Python 2.7 from paths, otherwise packages, as sklearn, can not be loaded
    sys.path = [p for p in sys.path if "2.7" not in p]
import datetime
import numpy as np
import pickle
import csv
import time
from abc import ABC, abstractmethod
import pandas as pd
import json
from splunklib.searchcommands import dispatch, Configuration, StreamingCommand, EventingCommand, Option, validators
from model_per_square import ModelPerSquare
from preprocessing import preprocessing_pipeline
from preprocessing import rreg_preprocessing_featureEng_pipeline
from preprocessing import nn_preprocessing_featureEng_pipeline
from preprocessing import get_model
from tensorflow.keras.models import load_model


class AbstractPredictor:

    @abstractmethod
    def predict(self, features):
        pass


    @abstractmethod
    def preprocess(self, features):
        pass

    @abstractmethod
    def results(self, features, predictions):
        pass

class BayesPredictor(AbstractPredictor):
    def __init__(self, ts_day):
        self.ts_day = ts_day
        self.model = get_model("models/model_rreg_lg13x13.p")
        super().__init__()

    def predict(self, features):
        return self.model.predict(features)

    def preprocess(self, features):
        return rreg_preprocessing_featureEng_pipeline(self.ts_day).fit_transform(features)

    def results(self, features, predictions):
        i = 0
        for _, row in features.iterrows():
            yield row.Square, max(0, round(predictions[i]))
            i += 1


class MLPPredictor(AbstractPredictor):
    def __init__(self, ts_day, mavg_days, past_days):
        self.ts_day = ts_day
        self.mavg_days = mavg_days
        self.past_days = past_days
        self.model = load_model("models/model_mlp_v1.h5")
        self.valid_squares = np.load("./.valid_squares.npy")
        super().__init__()

    def predict(self, features):
        return self.model.predict(features)

    def preprocess(self, features):
        return nn_preprocessing_featureEng_pipeline(self.ts_day, self.valid_squares, self.mavg_days, self.past_days).fit_transform(features)

    def results(self, features, predictions):
        i = 0
        vs_l = self.valid_squares.tolist()

        for p in predictions[0, :].tolist():
            yield vs_l[i], max(0, round(p))
            i += 1


def create_predictor(model_type: str, ts_day: pd.Timestamp) -> AbstractPredictor:
    key = model_type.strip().lower()
    if key == "rreg":
        return BayesPredictor(ts_day)
    elif key == "mlp":
        return MLPPredictor(ts_day, [14, 31], 7)

@Configuration()
class PredictCrimeCommand(EventingCommand):

    day = Option(require=True)
    model = Option(require=False)

    def transform(self, records):
        ts_day = pd.to_datetime(self.day, format='%m/%d/%Y')
        features = pd.DataFrame([json.loads(r["_raw"]) for r in records])

        if self.model is None:
            self.model = "rreg"

        predictor = create_predictor(self.model, ts_day)
        features = predictor.preprocess(features)
        predictions = predictor.predict(features)

        for sq, pr in predictor.results(features, predictions):
            yield {
                '_time': ts_day.timestamp(),
                "square": sq,
                "prediction": pr,
                '_raw': {
                    "square": sq,
                    "prediction": pr
                },
            }


if __name__ == '__main__':
    dispatch(PredictCrimeCommand, sys.argv, sys.stdin, sys.stdout, __name__)
