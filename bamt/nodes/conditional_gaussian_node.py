import itertools
import math
import random
from typing import Dict, Optional, List, Union

import numpy as np
from pandas import DataFrame
from sklearn import linear_model
from sklearn.base import clone
from sklearn.metrics import mean_squared_error as mse

from .base import BaseNode
from .schema import CondGaussParams


class ConditionalGaussianNode(BaseNode):
    """
    Main class for Conditional Gaussian Node
    """

    def __init__(self, name, regressor: Optional[object] = None):
        super(ConditionalGaussianNode, self).__init__(name)
        if regressor is None:
            regressor = linear_model.LinearRegression()
        self.regressor = regressor
        self.type = "ConditionalGaussian" + f" ({type(self.regressor).__name__})"

    def fit_parameters(self, data: DataFrame) -> Dict[str, Dict[str, CondGaussParams]]:
        """
        Train params for Conditional Gaussian Node.
        Return:
        {"hybcprob": {<combination of outputs from discrete parents> : CondGaussParams}}
        """
        hycprob = dict()
        values = []
        combinations = []
        for d_p in self.disc_parents:
            values.append(np.unique(data[d_p].values))
        for xs in itertools.product(*values):
            combinations.append(list(xs))
        for comb in combinations:
            mask = np.full(len(data), True)
            for col, val in zip(self.disc_parents, comb):
                mask = (mask) & (data[col] == val)
            new_data = data[mask]
            key_comb = [str(x) for x in comb]
            if new_data.shape[0] > 1:
                if self.cont_parents:
                    model = clone(self.regressor)
                    model.fit(
                        new_data[self.cont_parents].values, new_data[self.name].values
                    )
                    predicted_value = model.predict(new_data[self.cont_parents].values)
                    variance = mse(
                        new_data[self.name].values, predicted_value, squared=False
                    )
                    hycprob[str(key_comb)] = {
                        "variance": variance,
                        "mean": np.nan,
                        "regressor_obj": model,
                        "regressor": type(self.regressor).__name__,
                        "serialization": None,
                    }
                else:
                    mean_base = np.mean(new_data[self.name].values)
                    variance = np.var(new_data[self.name].values)
                    hycprob[str(key_comb)] = {
                        "variance": variance,
                        "mean": mean_base,
                        "regressor_obj": None,
                        "regressor": None,
                        "serialization": None,
                    }
            else:
                hycprob[str(key_comb)] = {
                    "variance": np.nan,
                    "regressor": None,
                    "regressor_obj": None,
                    "serialization": None,
                    "mean": np.nan,
                }
        return {"hybcprob": hycprob}

    def get_dist(self, node_info, pvals):
        dispvals = []
        lgpvals = []
        for pval in pvals:
            if isinstance(pval, str):
                dispvals.append(pval)
            else:
                lgpvals.append(pval)

        lgdistribution = node_info["hybcprob"][str(dispvals)]

        # JOBLIB

        if self.cont_parents:
            flag = False
            for el in lgpvals:
                if str(el) == "nan":
                    flag = True
                    break
            if flag:
                return np.nan, np.nan
            else:
                if lgdistribution["regressor"]:
                    model = lgdistribution["regressor_obj"]

                    cond_mean = model.predict(np.array(lgpvals).reshape(1, -1))[0]
                    variance = lgdistribution["variance"]
                    return cond_mean, variance
                else:
                    return np.nan, np.nan

        else:
            return lgdistribution["mean"], math.sqrt(lgdistribution["variance"])

    def choose(
        self,
        node_info: Dict[str, Dict[str, CondGaussParams]],
        pvals: List[Union[str, float]],
    ) -> float:
        """
        Return value from ConditionalLogit node
        params:
        node_info: nodes info from distributions
        pvals: parent values
        """

        cond_mean, variance = self.get_dist(node_info, pvals)
        if np.isnan(cond_mean) or np.isnan(variance):
            return np.nan

        return random.gauss(cond_mean, variance)

    def predict(
        self,
        node_info: Dict[str, Dict[str, CondGaussParams]],
        pvals: List[Union[str, float]],
    ) -> float:
        """
        Return value from ConditionalLogit node
        params:
        node_info: nodes info from distributions
        pvals: parent values
        """

        dispvals = []
        lgpvals = []
        for pval in pvals:
            if isinstance(pval, str):
                dispvals.append(pval)
            else:
                lgpvals.append(pval)

        lgdistribution = node_info["hybcprob"][str(dispvals)]

        if self.cont_parents:
            flag = False
            for el in lgpvals:
                if str(el) == "nan":
                    flag = True
                    break
            if flag:
                return np.nan
            else:
                if lgdistribution["regressor"]:
                    model = lgdistribution["regressor_obj"]
                    return model.predict(np.array(lgpvals).reshape(1, -1))[0]
                else:
                    return np.nan
        else:
            return lgdistribution["mean"]
