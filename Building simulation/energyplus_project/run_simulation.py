from pathlib import Path
import os
import sys

def _ensure_pyenergyplus():
    """
    Ensure pyenergyplus is importable:
    - if import fails, try to locate EnergyPlus install dir via EPLUS_ROOT or common paths
    - extend sys.path and (on Windows) DLL search path
    """
    try:
        from pyenergyplus.api import EnergyPlusAPI  # noqa: F401
        return
    except ModuleNotFoundError:
        pass

    # 1) user-provided env var (set this if you installed EnergyPlus elsewhere)
    env_root = os.environ.get("EPLUS_ROOT") or os.environ.get("ENERGYPLUS_ROOT")
    candidates = []
    if env_root:
        candidates.append(Path(env_root))

    # 2) typical Windows install locations (edit if yours differs)
    candidates += [
        Path(r"C:/EnergyPlusV25-1-0"),
        Path(r"C:/Program Files/EnergyPlusV25-1-0"),
        Path(r"C:/Program Files (x86)/EnergyPlusV25-1-0"),
    ]

    for root in candidates:
        if root.exists():
            # Add to sys.path so 'from pyenergyplus...' works
            if str(root) not in sys.path:
                sys.path.append(str(root))
            # Ensure DLLs can be found (Python 3.8+ on Windows)
            if hasattr(os, "add_dll_directory"):
                try:
                    os.add_dll_directory(str(root))
                except Exception:
                    pass
            try:
                from pyenergyplus.api import EnergyPlusAPI  # noqa: F401
                return
            except ModuleNotFoundError:
                continue

    raise ModuleNotFoundError(
        "pyenergyplus not found. Set environment variable EPLUS_ROOT to your EnergyPlus "
        "install folder (e.g. C:\\EnergyPlusV25-1-0) or adjust the candidate paths in this script."
    )

# make sure pyenergyplus is importable before proceeding
_ensure_pyenergyplus()
from pyenergyplus.api import EnergyPlusAPI


def run_simulation(idf_path, epw_path, output_dir):
    api = EnergyPlusAPI()
    state = api.state_manager.new_state()

    idf = Path(idf_path).resolve()
    epw = Path(epw_path).resolve()
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    print(f"IDF : {idf}")
    print(f"EPW : {epw}")
    print(f"OUT : {out}")

    # -w weather, -d output dir, -r => run ReadVarsESO to generate eplusout.csv
    args = ["-m", "-x", "-w", str(epw), "-d", str(out), "-r", str(idf)]
    ok = api.runtime.run_energyplus(state, args)
    print("Simulation complete." if ok else "Simulation finished with errors (see eplusout.err).")

    # helpful post-run checks
    err = out / "eplusout.err"
    csv = out / "eplusout.csv"
    htm = out / "eplustbl.htm"
    eso = out / "eplusout.eso"

    if err.exists():
        # print last few lines of ERR to spot issues quickly
        print("\n--- eplusout.err (tail) ---")
        try:
            tail = err.read_text(encoding="utf-8", errors="ignore").splitlines()[-15:]
            for line in tail:
                print(line)
        except Exception:
            print(f"(Could not read {err})")

    print("\n--- Output files ---")
    print(f"CSV:  {'OK' if csv.exists() else 'missing'} -> {csv}")
    print(f"HTML: {'OK' if htm.exists() else 'missing'} -> {htm}")
    print(f"ESO:  {'OK' if eso.exists() else 'missing'} -> {eso}")
    print(f"ERR:  {'OK' if err.exists() else 'missing'} -> {err}")


if __name__ == "__main__":
    base = Path(__file__).resolve().parent
    idf = base / "../idf/base_model.idf"
    epw = base / "../weather/AUT_SZ_Salzburg.AP.111500_TMYx.2009-2023.epw"
    out = base / "../output"
    run_simulation(idf, epw, out)
