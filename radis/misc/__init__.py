# -*- coding: utf-8 -*-
"""Created on Tue May 26 11:52:15 2015.

Erwan Pannier EM2C, CentraleSupélec, 2015 CNRS UPR 288
"""


from .arrays import (
    array_allclose,
    autoturn,
    bining,
    calc_diff,
    centered_diff,
    count_nans,
    evenly_distributed,
    find_first,
    find_nearest,
    is_sorted,
    is_sorted_backward,
    logspace,
    nantrapz,
    norm,
    norm_on,
    scale_to,
)
from .basics import (
    compare_dict,
    compare_lists,
    compare_paths,
    exec_file,
    is_float,
    key_max_val,
    list_if_float,
    make_folders,
    merge_lists,
    partition,
    remove_duplicates,
)
from .config import automatic_conversion, getDatabankEntries, getDatabankList
from .curve import (
    curve_add,
    curve_distance,
    curve_divide,
    curve_multiply,
    curve_substract,
)
from .debug import export
from .progress_bar import ProgressBar
from .signal import resample, resample_even
from .utils import DatabankNotFound, NotInstalled, getProjectRoot

# Checking `~radis.json` exist or not, if not then converting `~.radis` into `~/radis.json`
try:
    automatic_conversion()
except:
    raise ("Couldn't Convert `.radis` to `radis.json`")
