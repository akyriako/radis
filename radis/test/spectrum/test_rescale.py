#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Summary
-------

Test Spectrum rescaling methods

-------------------------------------------------------------------------------


"""

import astropy.units as u
import numpy as np
import pytest

import radis
from radis.misc.printer import printm
from radis.spectrum.rescale import get_recompute, get_redundant
from radis.test.utils import getTestFile
from radis.tools.database import load_spec


@pytest.mark.fast
def test_compression(verbose=True, warnings=True, *args, **kwargs):
    """Test that redundant quantities are properly infered from already known
    spectral quantities"""

    # Get spectrum
    s1 = load_spec(getTestFile("CO_Tgas1500K_mole_fraction0.01.spec"), binary=True)

    s1.conditions["thermal_equilibrium"] = True
    s1.update()

    # Analyse redundant spectral quantities
    redundant = get_redundant(s1)
    if verbose:
        print(redundant)

    assert redundant == {
        "emissivity_noslit": True,
        "radiance_noslit": True,
        "emisscoeff": True,
        "transmittance_noslit": True,
        "absorbance": True,
        "abscoeff": False,
        "xsection": True,
    }

    return True


@pytest.mark.fast
def test_update_transmittance(verbose=True, warnings=True, *args, **kwargs):
    """Test that update can correctly recompute missing quantities"""
    # TODO: add one with radiance too

    # Work with a Spectrum object that was generated by Specair
    s = load_spec(getTestFile("N2C_specair_380nm.spec"))
    w1, T1 = s.get("transmittance_noslit")  # our reference

    if verbose:
        debug_mode = radis.config["DEBUG_MODE"]  # shows all the rescale steps taken
        radis.config["DEBUG_MODE"] = True

    # Now let's apply some update() steps

    # 1) Make sure updating doesnt change anything
    s.update()
    w2, T2 = s.get("transmittance_noslit")

    # 2) Now recompute from abscoeff
    del s._q["transmittance_noslit"]
    s.update()
    w2, T3 = s.get("transmittance_noslit")

    # 3) Now recompute from absorbance
    del s._q["transmittance_noslit"]
    del s._q["abscoeff"]
    s.update()
    w2, T4 = s.get("transmittance_noslit")

    if verbose:
        radis.config["DEBUG_MODE"] = debug_mode

    # Compare
    assert np.allclose(T1, T2)
    assert np.allclose(T1, T3)
    assert np.allclose(T1, T4)

    return True


def test_get_recompute(verbose=True, *args, **kwargs):
    """Make sure :func:`~radis.spectrum.rescale.get_recompute` works as expected

    Here, we check which quantities are needed to recompute radiance_noslit"""

    # Equilibrium
    # -----------
    s = load_spec(getTestFile("CO_Tgas1500K_mole_fraction0.01.spec"), binary=True)

    assert s.get_vars() == ["abscoeff"]
    assert s.conditions["thermal_equilibrium"]
    # At equilibrium, everything should be deduced from abscoeff
    assert set(get_recompute(s, ["radiance_noslit"])) == set(
        ("radiance_noslit", "abscoeff")
    )

    # Non Equilibrium
    # ----------------
    s.conditions["Tvib"] = 2000
    # a problem should be detected by is_at_equilibrium()
    with pytest.raises(AssertionError):
        assert not s.is_at_equilibrium(check="error")
    # force non equilibrium
    s.conditions["thermal_equilibrium"] = False

    # Now more data is needed:
    assert set(get_recompute(s, ["radiance_noslit"])) == set(
        ("abscoeff", "emisscoeff", "radiance_noslit")
    )


def test_rescale_vs_direct_computation(verbose=True, *args, **kwargs):
    """Compare spectral arrays initially computed with recomputed spectral arrays

    Notes
    -----
    Use verbose=2 to get DEBUG_MODE output
    """
    if verbose >= 2:
        DEBUG_MODE = radis.config["DEBUG_MODE"]
        radis.config["DEBUG_MODE"] = True

    # %%
    # Equilibrium Spectrum
    # -------------------
    from radis import calc_spectrum

    s = calc_spectrum(
        wavelength_min=4165,
        wavelength_max=4200,
        mole_fraction=1e-3,
        path_length=0.3,
        molecule="CO2",
        isotope="1",
        databank="HITRAN-CO2-TEST",
        Tgas=600,
        verbose=False,
    )

    s2 = s.copy()

    import numpy as np

    # 1. Compare initially computed with recomputed
    for var in ["abscoeff", "radiance_noslit"]:

        # default
        Imax_computed = s.take(var).max()
        # delete existing variables
        del s2._q[var]
        # recompute:
        Imax_recomputed = s2.take(var).max()
        # compare:
        if verbose:
            print("==>", var, Imax_computed)
            print("==>", var, Imax_recomputed)
        assert np.isclose(Imax_computed, Imax_recomputed)

    # 2. Do this systematically, for all configurations where `s` can be recomputed from.
    from radis.spectrum.rescale import _build_update_graph

    """Typical :py:func:`radis.spectrum.rescale._build_update_graph(s)` result :
    ::
        {
            "transmittance_noslit": [
                ["absorbance"],
                ["abscoeff"],
                ["absorbance"],
                ["emisscoeff"],
                ["emissivity_noslit"],
                ["transmittance"],
                ["radiance"],
                ["radiance_noslit"],
                ["xsection"],
            ],
            "absorbance": [
                ["transmittance_noslit"],
                ["abscoeff"],
                ["abscoeff"],
                ["emisscoeff"],
                ["emissivity_noslit"],
                ["transmittance"],
                ["radiance"],
                ["radiance_noslit"],
                ["transmittance_noslit"],
                ["xsection"],
            ],
            "abscoeff": [
                ["absorbance"],
                ["xsection"],
                ["absorbance"],
                ["emisscoeff"],
                ["emissivity_noslit"],
                ["transmittance"],
                ["radiance"],
                ["radiance_noslit"],
                ["transmittance_noslit"],
                ["xsection"],
            ],
            "radiance_noslit": [
                ["emisscoeff", "abscoeff"],
                ["abscoeff"],
                ["absorbance"],
                ["emisscoeff"],
                ["emissivity_noslit"],
                ["transmittance"],
                ["radiance"],
                ["transmittance_noslit"],
                ["xsection"],
            ],
            "emisscoeff": [
                ["radiance_noslit", "abscoeff"],
                ["abscoeff"],
                ["absorbance"],
                ["emissivity_noslit"],
                ["transmittance"],
                ["radiance"],
                ["radiance_noslit"],
                ["transmittance_noslit"],
                ["xsection"],
            ],
            "xsection": [["abscoeff"]],
            "emissivity_noslit": [
                ["abscoeff"],
                ["absorbance"],
                ["emisscoeff"],
                ["transmittance"],
                ["radiance"],
                ["radiance_noslit"],
                ["transmittance_noslit"],
                ["xsection"],
            ],
        }
    """
    from radis.misc.basics import all_in

    for var, vars_needed_list in _build_update_graph(s).items():
        for vars_needed in vars_needed_list:
            if all_in(vars_needed, s.get_vars()):
                if verbose:
                    print(f"Recomputing {var} from {vars_needed} only")
                s2 = s.copy()
                for v in list(s2.get_vars()):
                    if v not in vars_needed:
                        del s2._q[v]
                # recompute & compare:
                try:
                    s2.get(var)
                except NotImplementedError:
                    pass
                else:
                    assert np.isclose(s.take(var).max(), s2.take(var).max())
                    if verbose:
                        print(
                            f"Checked {var} recomputed from {vars_needed} is the same"
                        )

    #%%
    # Nonequilibrium spectrum, computed in wavenumber
    # -----------------------------------------------

    from radis import calc_spectrum

    s = calc_spectrum(
        wavenum_max=1e7 / 4165,
        wavenum_min=1e7 / 4200,
        mole_fraction=1e-3,
        path_length=0.3,
        molecule="CO2",
        isotope="1",
        databank="HITRAN-CO2-TEST",
        Tvib=2000,
        Trot=1000,
        verbose=False,
    )

    import numpy as np

    # Compare initially computed with recomputed
    for var in ["transmittance_noslit", "emisscoeff", "radiance_noslit"]:

        s2 = s.copy()

        # default
        Imax_computed = s.take(var).max()
        # delete existing variables
        del s2._q[var]
        # recompute:
        Imax_recomputed = s2.take(var).max()
        # compare:
        if verbose:
            print("==>", var, Imax_computed)
            print("==>", var, Imax_recomputed)
        assert np.isclose(Imax_computed, Imax_recomputed)

    """Typical :py:func:`radis.spectrum.rescale._build_update_graph(s)` result :
    ::

        {
            "transmittance_noslit": [["absorbance"]],
            "absorbance": [["transmittance_noslit"], ["abscoeff"]],
            "abscoeff": [["absorbance"], ["xsection"]],
            "radiance_noslit": [["emisscoeff", "abscoeff"]],
            "emisscoeff": [["radiance_noslit", "abscoeff"]],
            "xsection": [["abscoeff"]],
        }
    """

    for var, vars_needed_list in _build_update_graph(s).items():
        for vars_needed in vars_needed_list:
            if all_in(vars_needed, s.get_vars()):
                if verbose:
                    print(f"Recomputing {var} from {vars_needed} only")
                s2 = s.copy()
                for v in list(s2.get_vars()):
                    if v not in vars_needed:
                        del s2._q[v]
                # recompute & compare:
                try:
                    s2.get(var)
                except NotImplementedError:
                    pass
                else:
                    assert np.isclose(s.take(var).max(), s2.take(var).max())
                    if verbose:
                        print(
                            f"Checked {var} recomputed from {vars_needed} is the same"
                        )

    #
    if verbose >= 2:
        radis.config["DEBUG_MODE"] = DEBUG_MODE

    #%%


def test_recompute_equilibrium(verbose=True, warnings=True, plot=True, *args, **kwargs):
    """Test that spectral quantities recomputed under equilibrium assumption
    yields the same output as with non equilibrium routines when Tvib = Trot"""

    if plot:
        import matplotlib.pyplot as plt

        plt.ion()  # dont get stuck with Matplotlib if executing through pytest

    # Get spectrum
    s1 = load_spec(getTestFile("CO_Tgas1500K_mole_fraction0.01.spec"))
    s1.rescale_path_length(100)  # just for fun

    assert s1.is_at_equilibrium()
    s1.update("emisscoeff")

    # force non equilibrium calculation
    s2 = s1.copy()
    s2.conditions["thermal_equilibrium"] = False
    s2.update()
    assert (
        "emissivity_noslit" not in s2.get_vars()
    )  # just a check update() was done at nonequilibrium

    # update s1 now (at equilibrium)
    s1.update()
    assert (
        "emissivity_noslit" in s1.get_vars()
    )  # just a check update() was done at equilibrium

    s1.name = "scaled with Kirchoff law"
    s2.name = "scaled from emisscoeff + abscoeff with RTE"

    if verbose:
        print(
            "Checked that scaling at equilibrium with Kirchoff law yields the "
            + "same radiance as by solving the RTE from emisscoeff and abscoeff"
        )

    # Now Compare both update processes
    assert s1.compare_with(s2, spectra_only="radiance_noslit", plot=plot)


def test_rescale_all_quantities(verbose=True, warnings=True, *args, **kwargs):

    new_mole_fraction = 0.5
    new_path_length = 0.1

    # Get spectrum
    s0 = load_spec(getTestFile("CO_Tgas1500K_mole_fraction0.01.spec"), binary=True)
    s0.update("all")  # start with all possible quantities in s0
    sscaled = s0.copy()
    sscaled.rescale_mole_fraction(new_mole_fraction)
    sscaled.rescale_path_length(new_path_length)
    s0.conditions["thermal_equilibrium"] = False  # to prevent rescaling with Kirchoff
    # remove emissivity_no_slit (speciifc to equilibrium)
    del s0._q["emissivity_noslit"]

    # Determine all quantities that can be recomputed
    if verbose >= 2:
        import radis

        DEBUG_MODE = radis.config["DEBUG_MODE"]
        radis.config["DEBUG_MODE"] = True
    from radis.spectrum.rescale import _build_update_graph, get_reachable, ordered_keys

    # ordered_keys: all spectral quantities that can be rescaled
    can_be_recomputed = get_reachable(s0)
    # can_be_recomputed: all spectra quantities that can be rescaled for this
    # particular spectrum
    update_paths = _build_update_graph(s0)
    # update_paths: which quantities are needed to recompute the others

    rescale_list = [k for k in ordered_keys if can_be_recomputed[k]]

    for quantity in rescale_list:
        all_paths = update_paths[quantity]
        if verbose:
            printm(
                "{0} can be recomputed from {1}".format(
                    quantity,
                    " or ".join(["&".join(combinations) for combinations in all_paths]),
                )
            )

        # Now let's test all paths
        for combinations in all_paths:
            if verbose:
                printm(
                    "> computing {0} from {1}".format(quantity, "&".join(combinations))
                )
            s = s0.copy()
            # Delete all other quantities
            for k in s.get_vars():
                if k not in combinations:
                    del s._q[k]

            s.update(quantity, verbose=verbose)

            # Now rescale
            s.rescale_mole_fraction(new_mole_fraction)
            s.rescale_path_length(new_path_length)

            # Compare
            assert s.compare_with(sscaled, spectra_only=quantity, plot=False)

    if verbose >= 2:
        radis.config["DEBUG_MODE"] = DEBUG_MODE


def test_xsections(*args, **kwargs):
    r"""Test that we do have

    .. math::

        exp(-\sigma \cdot N_x \cdot L) = exp(- k \cdot L)

    Therefore

    .. math::

        k = \sigma \cdot \frac{x p}{k T}

    With ``p`` total pressure and ``x`` the mole fraction.

    """
    from radis.phys.constants import k_b
    from radis.phys.units import Unit as u

    # Get spectrum
    s = load_spec(getTestFile("CO_Tgas1500K_mole_fraction0.01.spec"), binary=True)

    p = s.c["pressure_mbar"] * u("mbar")
    kb = k_b * u("J/K")
    T = s.c["Tgas"] * u("K")

    N = p / kb / T

    assert s.c["pressure_mbar"] == 1013.25
    assert s.c["Tgas"] == 1500
    assert s.c["mole_fraction"] == 0.01

    assert np.isclose(N.to("1/cm3").value, 4.892e18, rtol=1e-3)

    N_x = N * 0.01

    assert np.isclose(s.take("abscoeff").max(), s.take("xsection").max() * N_x)

    # Test again for x =1

    s.rescale_mole_fraction(1)
    assert np.isclose(
        s.take("abscoeff").max().to("1/cm").value,
        (s.take("xsection").max() * N).to("1/cm").value,
    )


def test_astropy_units(verbose=True, warnings=True, *args, **kwargs):
    """This test is to assert the use of astropy units in rescale function,
    by comparing the absorbance of a spectrum rescaled with astropy units
    (in this test we use u.km) with the absorbance of original spectrum"""

    # Get precomputed spectrum
    s0 = load_spec(getTestFile("CO_Tgas1500K_mole_fraction0.01.spec"), binary=True)

    # Generate new spectrums by rescaling original one
    s_cm = s0.copy().rescale_path_length(100000)  # Rescale to 100000 cm = 1 km
    s_km = s0.copy().rescale_path_length(1 * u.km)  # Rescale directly to 1 astropy km

    # Get absorbance of original spectrum
    A0 = s0.get("absorbance", wunit="cm-1")

    # Get absorbance and path length of 100000cm-rescaled spectrum
    L_cm = s_cm.get_conditions()["path_length"]
    A_cm = s_cm.get("absorbance", wunit="cm-1")

    # Get absorbance and path length of 1km-rescale spectrum
    L_km = s_km.get_conditions()["path_length"]
    A_km = s_km.get("absorbance", wunit="cm-1")

    # ---------- ASSERTION ----------

    # Compare absorbances of original and 1km. They should be DIFFERENT.
    assert not np.array_equal(A0, A_km)

    # Compare absorbances of 100000cm and 1km. They should be THE SAME.
    assert np.array_equal(A_cm, A_km)

    # Compare path lengths in 1km and 100000cm. They should be THE SAME.
    assert L_cm == L_km

    if verbose:
        print(
            (
                "Astropy units work normally in the provided test case. "
                "The absorbances observed in original and rescaled spectrums "
                "follow the basis of absorption spectroscopy."
            )
        )


def _run_all_tests(verbose=True, warnings=True, *args, **kwargs):
    test_compression(verbose=verbose, warnings=warnings, *args, **kwargs)
    test_update_transmittance(verbose=verbose, warnings=warnings, *args, **kwargs)
    test_get_recompute(verbose=verbose, warnings=warnings, *args, **kwargs)
    test_rescale_vs_direct_computation(verbose=verbose, *args, **kwargs)
    test_recompute_equilibrium(verbose=verbose, warnings=warnings, *args, **kwargs)
    test_rescale_all_quantities(verbose=verbose, *args, **kwargs)
    test_xsections(*args, **kwargs)
    test_astropy_units(verbose=True, warnings=True, *args, **kwargs)
    return True


if __name__ == "__main__":
    print(("Testing test_rescale.py:", _run_all_tests(verbose=True)))
