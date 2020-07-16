"""
Collection of Enum classes used in /geospatial.
"""

from enum import Enum


class ExperimentConfigMode(Enum):
    """Which mode is the current experiment config file in, e.g. training, scoring, etc mode"""
    PREPROCESSING = 1
    TRAINING = 2
    EVALUATION = 3  # different from SCORING as it usually only involves labeled tiles in the validation set
    SCORING = 4  # over a large area and the output should be georeferenced
