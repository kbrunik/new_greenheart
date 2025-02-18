import copy
import numpy as np
import os

from hopp.simulation.technologies.sites import SiteInfo
from hopp.simulation.technologies.layout.wind_layout_tools import create_grid
from hopp.simulation.hopp_interface import HoppInterface


# Function to set up the HOPP model
def setup_hopp(hopp_config, plant_config):
    if ("desired_schedule" not in hopp_config["site"].keys() or hopp_config["site"]["desired_schedule"] == []):
        hopp_config["site"]["desired_schedule"] = [10.] * 8760

    hopp_site = SiteInfo(**hopp_config["site"])

    # setup hopp interface
    hopp_config_internal = copy.deepcopy(hopp_config)

    if "wave" in hopp_config_internal["technologies"].keys():
        wave_cost_dict = hopp_config_internal["technologies"]["wave"].pop("cost_inputs")

    if "battery" in hopp_config_internal["technologies"].keys():
        hopp_config_internal["site"].update({"desired_schedule": hopp_site.desired_schedule})
        
    hi = HoppInterface(hopp_config_internal)
    hi.system.site = hopp_site

    if "wave" in hi.system.technologies.keys():
        hi.system.wave.create_mhk_cost_calculator(wave_cost_dict)
        
    return hi


# Function to run hopp from provided inputs from setup_hopp()
def run_hopp(hi, project_lifetime, verbose=True):
    hi.simulate(project_life=project_lifetime)

    capex = 0.
    opex = 0.
    try:
        solar_capex = hi.system.pv.total_installed_cost
        solar_opex = hi.system.pv.om_total_expense[0]
        capex += solar_capex
        opex += solar_opex
    except AttributeError:
        pass

    try:
        wind_capex = hi.system.wind.total_installed_cost
        wind_opex = hi.system.wind.om_total_expense[0]
        capex += wind_capex
        opex += wind_opex
    except AttributeError:
        pass

    try:
        battery_capex = hi.system.battery.total_installed_cost
        battery_opex = hi.system.battery.om_total_expense[0]
        capex += battery_capex
        opex += battery_opex
    except AttributeError:
        pass

    # store results for later use
    hopp_results = {
        "hopp_interface": hi,
        "hybrid_plant": hi.system,
        "combined_hybrid_power_production_hopp": \
            hi.system.grid._system_model.Outputs.system_pre_interconnect_kwac[0:8760],
        "combined_hybrid_curtailment_hopp": hi.system.grid.generation_curtailed,
        "energy_shortfall_hopp": hi.system.grid.missed_load,
        "annual_energies": hi.system.annual_energies,
        "hybrid_npv": hi.system.net_present_values.hybrid,
        "npvs": hi.system.net_present_values,
        "lcoe": hi.system.lcoe_real,
        "lcoe_nom": hi.system.lcoe_nom,
        "capex": capex,
        "opex": opex,
    }
    if verbose:
        print("\nHOPP Results")
        print("Hybrid Annual Energy: ", hopp_results["annual_energies"])
        print("Capacity factors: ", hi.system.capacity_factors)
        print("Real LCOE from HOPP: ", hi.system.lcoe_real)

    return hopp_results
