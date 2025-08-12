import sys
import os

eplus_path = r"C:/EnergyPlusV25-1-0"
sys.path.append(eplus_path)

from pyenergyplus.api import EnergyPlusAPI

def run_simulation(idf_path, epw_path, output_dir):
    api = EnergyPlusAPI()
    state = api.state_manager.new_state()
    args = ["-w", epw_path, "-d", output_dir, idf_path]
    print(f"Running simulation: {idf_path}")
    api.runtime.run_energyplus(state, args)
    print("Simulation complete.")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    idf = os.path.join(base_dir, "../idf/base_model.idf")
    epw = os.path.join(base_dir, "../weather/AUT_SZ_Salzburg.AP.111500_TMYx.2009-2023.epw")
    out = os.path.join(base_dir, "../output")
    run_simulation(idf, epw, out)
