"""
This module experiments with ways to compose signal ML systems from a gallery of
parametrizable components.

The intent is to offer a python interface to the process that emulates the user
experience of a drag and drop GUI.

"""

from dol.sources import AttrContainer
import numpy as np
from inspect import signature

from slang.chunkers import fixed_step_chunker, mk_chunker
from slang.featurizers import mk_wf_to_spectr
from slang.spectrop import (
    logarithmic_bands_matrix,
    GeneralProjectionLearner,
    SpectralProjectorSupervisedFitter,
    SpectralProjectorUnsupervisedFitter,
)

from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.decomposition import PCA, IncrementalPCA
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.cluster import KMeans
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.pipeline import Pipeline


from i2.deco import FuncFactory


def identity(obj):
    return obj


from atypes import WfStore


class a:
    wf_store = AttrContainer()
    chunker = AttrContainer(fixed_step=mk_chunker)
    featurizer = AttrContainer(
        fft=mk_wf_to_spectr,
        # we need no parametrization, so we use FuncFactory.func_returning_obj to wrap
        # std in a factory:
        vol=FuncFactory.func_returning_obj(np.std),
    )
    learner = AttrContainer(
        # Note that none of these have names. We use AttrContainer's auto namer here
        StandardScaler,
        MinMaxScaler,
        PCA,
        IncrementalPCA,
        LinearRegression,
        LogisticRegression,
        KMeans,
        LinearDiscriminantAnalysis,
        logarithmic_bands_matrix,
        GeneralProjectionLearner,
        SpectralProjectorSupervisedFitter,
        SpectralProjectorUnsupervisedFitter,
    )


def test_a():
    assert list(a.featurizer) == ['fft', 'vol']
    assert 'StandardScaler' in a.learner
    assert a.learner.StandardScaler == StandardScaler


test_a()
