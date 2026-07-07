import pandas as pd
import numpy as np
import pickle
from sklearn.base import BaseEstimator, TransformerMixin, RegressorMixin
from sklearn.model_selection import cross_validate, TimeSeriesSplit, GridSearchCV, RandomizedSearchCV
from pipeline_utilties import SelectSquare

class ModelPerSquare(BaseEstimator, RegressorMixin):
    
    def __init__(self,  param_dist, estimator, cv = None, n_iter = 30, scoring='neg_mean_squared_error'):
        self.param_dist = param_dist
        self.estimator = estimator
        self.cv = cv
        self.n_iter = n_iter
        self.scoring = scoring
        
    def fit_square_model(self, X,y, square):
        X_square, y_square, _ = SelectSquare(square = square).transform(X,y)

        cv_split = self.cv.split(X_square) if self.cv else self.cv

        rscv = RandomizedSearchCV(estimator=self.estimator, 
                                  param_distributions=self.param_dist, 
                                  cv=self.cv,
                                  scoring=self.scoring, # 'neg_mean_squared_error' or 'neg_mean_absolute_error'
                                  return_train_score=True, 
                                  n_iter=self.n_iter)

        rscv.fit(X_square, y_square)

        y_pred = rscv.predict(X_square)

        return {'model': rscv.best_estimator_, 
                'error': sum((y_square-y_pred)**2)/sum(y_square)}
    
    
    def fit(self, X, y=None, save=True, verbose=False):        
        #self.load_model('models\\model_dict.p')
        square_list = X.Square.unique()

        self.model_dict = {}
        for square in square_list:
            self.model_dict[f'{square}'] = self.fit_square_model(X,y, square)
            
            if verbose:
                print(f'fit Square {square}')
            
        if save:
            self.save_model()
        
        return self
    
    
    def predict(self, X):
        y_pred = pd.Series()

        for Square,X_Square in X.reset_index(drop=True).groupby("Square"):
            y_square_pred = self.model_dict[str(Square)]['model'].predict(X_Square)
            y_pred = y_pred.append(pd.Series(y_square_pred, index = X_Square.index))

        return np.array(y_pred.sort_index())
    
    
    def load_model(self, model_dir):
        with open(model_dir, "rb") as file:
            self.model_dict = pickle.load(file)
            
    def save_model(self):
        model_dir = 'models//model_dict_' + pd.Timestamp.now().strftime('%Y-%m-%d_%H-%M') + '.p'
        pickle.dump(self.model_dict, open(model_dir, "wb" ))
     