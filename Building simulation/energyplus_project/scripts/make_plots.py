#!/usr/bin/env python3
# make_plots.py
# Liest eplusout.csv und erzeugt Zeitreihenplots (PNG) pro Zone/Variable.
# Zusätzlich wird – falls vorhanden – eine Tagesstatistik für Zone-Temperatur geschrieben.

import argparse
from pathlib import Path
import re
import pandas as pd
import matplotlib.pyplot as plt

# ================== Default-Pfade/Optionen für VS Code-Start ==================
DEFAULT_CSV = Path(r"y:/ansys01/MLu/lahof/Building simulation/energyplus_project/output/eplusout.csv")
DEFAULT_OUT = DEFAULT_CSV.parent / "figures"
DEFAULT_ZONE = None  # z. B. "WOHNZIMMER" für nur eine Zone; None = alle
DEFAULT_VARS = ["Zone Air Temperature", "Zone Air Relative Humidity"]  # weitere z. B. "Zone Operative Temperature"
DEFAULT_YEAR = 2013  # Jahr anfügen, wenn CSV keines enthält (dein Run startet 2013)
DEFAULT_DPI = 150
# ==============================================================================

def parse_args():
    p = argparse.ArgumentParser(description="Plot EnergyPlus-Zeitreihen aus eplusout.csv")
    p.add_argument("--csv", default=str(DEFAULT_CSV), help="Pfad zur eplusout.csv")
    p.add_argument("--out", default=str(DEFAULT_OUT), help="Ausgabeordner für PNGs")
    p.add_argument("--zone", default=DEFAULT_ZONE, help="Nur diese Zone plotten (default: alle gefundenen Zonen)")
    p.add_argument("--vars", nargs="+", default=DEFAULT_VARS,
                   help="Variablennamen, z. B. 'Zone Air Temperature'")
    p.add_argument("--year", type=int, default=DEFAULT_YEAR, help="Jahr fürs Datumsparsing (falls CSV nur MM/DD enthält)")
    p.add_argument("--dpi", type=int, default=DEFAULT_DPI, help="Auflösung der PNGs")
    return p.parse_args()

def find_time_column(df):
    for cand in ("Date/Time", "Date Time", "Date_Time"):
        if cand in df.columns:
            return cand
    raise KeyError("Konnte die 'Date/Time'-Spalte in eplusout.csv nicht finden.")

def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).strip()).lower()

# Bekannte Synonyme/Varianten von Variablennamen (werden case-insensitiv gematcht)
SYNONYMS = {
    "zone air temperature": ["zone mean air temperature", "zone air temperature"],
    "zone operative temperature": ["zone operative temperature"],
    "zone relative humidity": ["zone air relative humidity", "zone relative humidity"],
    "zone humidity ratio": ["zone mean air humidity ratio", "zone air humidity ratio", "zone humidity ratio"],
}

def parse_datetime(series: pd.Series, default_year: int) -> pd.Series:
    """Robustes Parsing für verschiedene EnergyPlus Date/Time-Varianten."""
    def _norm(s: str) -> str:
        s = str(s).strip().replace("*", "")  # DST-Markierung entfernen
        # Doppelte Spaces (häufig zwischen Datum und Zeit) auf einfachen Space normalisieren
        while "  " in s:
            s = s.replace("  ", " ")
        return s

    t = series.astype(str).map(_norm)

    # 1) Direkter Versuch (falls Jahr schon enthalten ist)
    dt = pd.to_datetime(t, errors="coerce")

    # 2) Ohne Jahr: Jahr anhängen und bekannte Formate testen
    m = dt.isna()
    if m.any():
        cand = t[m] + f" {default_year}"
        # Versuch mit Sekunden
        dt.loc[m] = pd.to_datetime(cand, format="%m/%d %H:%M:%S %Y", errors="coerce")
        m = dt.isna()
        if m.any():
            # Versuch ohne Sekunden
            dt.loc[m] = pd.to_datetime(t[m] + f" {default_year}", format="%m/%d %H:%M %Y", errors="coerce")

    # 3) Sonderfall 24:00:00 -> nächster Tag 00:00:00
    m = dt.isna()
    if m.any():
        def fix_24h(s: str):
            if "24:" in s:
                s2 = s.replace("24:", "00:")
                ts = pd.to_datetime(s2 + f" {default_year}", errors="coerce")
                if pd.isna(ts):
                    return pd.NaT
                return ts + pd.Timedelta(days=1)
            return pd.NaT
        dt.loc[m] = t[m].map(fix_24h)

    if dt.isna().any():
        bad = t[dt.isna()].unique()[:5]
        raise ValueError(f"Datum/Uhrzeit konnten nicht geparst werden. Beispiele: {bad}")

    return dt

def list_zone_series(df):
    """
    Liefert Dict: zone -> {var_name -> [spalten]}
    Spaltenstruktur i. d. R.: "<Key>:<Variable> [Unit](Freq)"
    """
    pattern = re.compile(r"^(?P<key>[^:]+):(?P<var>.+?)(?:\s*\[.*?\])?(?:\(.+?\))?$")
    by_zone = {}
    for col in df.columns:
        if ":" not in col or col.startswith("Date"):
            continue
        m = pattern.match(col)
        if not m:
            continue
        key = m.group("key").strip()
        var = m.group("var").strip()
        by_zone.setdefault(key, {}).setdefault(var, []).append(col)
    return by_zone

def find_var_name(zone_vars: dict, wanted_var: str):
    """Finde beste Übereinstimmung eines gewünschten Variablennamens in den vorhandenen Variablen."""
    wanted_norm = normalize(wanted_var)
    # exakter Treffer (case-insensitiv)
    for v in zone_vars.keys():
        if normalize(v) == wanted_norm:
            return v
    # Synonyme
    for canon, alts in SYNONYMS.items():
        if wanted_norm == normalize(canon) or wanted_norm in [normalize(a) for a in alts]:
            for alt in alts:
                for v in zone_vars.keys():
                    if normalize(v) == normalize(alt):
                        return v
    # Teilstring
    for v in zone_vars.keys():
        if wanted_norm in normalize(v):
            return v
    return None

def pick_column(columns_for_var):
    """Wenn mehrere Spalten (versch. Frequenzen/Units) existieren, wähle deterministisch die erste."""
    return sorted(columns_for_var)[0]

def ensure_out_dir(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)

def plot_series(dt, y, title, ylabel, out_path: Path, dpi: int):
    plt.figure()
    plt.plot(dt, y)
    plt.xlabel("Zeit")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(out_path, dpi=dpi)
    plt.close()

def main():
    args = parse_args()
    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV nicht gefunden: {csv_path}")

    out_dir = Path(args.out)
    ensure_out_dir(out_dir)

    df = pd.read_csv(csv_path)
    time_col = find_time_column(df)
    dt = parse_datetime(df[time_col], args.year)
    by_zone = list_zone_series(df)

    # Zonen bestimmen (case-insensitiv matchen)
    all_zones = list(by_zone.keys())
    if not all_zones:
        raise RuntimeError("Keine Zonen/Keys in der CSV gefunden.")
    zones = [args.zone] if args.zone else sorted(all_zones)

    print(f"Gefundene Zonen: {', '.join(sorted(all_zones))}")
    print(f"Zu plottende Variablen: {', '.join(args.vars)}")
    print(f"Ausgabeordner: {out_dir}")

    for zone in zones:
        # tatsächlichen Zonenschlüssel finden (Groß-/Kleinschreibung egal)
        zone_actual = None
        for z in by_zone.keys():
            if normalize(z) == normalize(zone):
                zone_actual = z
                break
        # Falls keine Zone vorgegeben war und die CSV hat z. B. "WOHNZIMMER", nimm sie direkt
        if zone_actual is None and args.zone is None:
            zone_actual = zone
        if zone_actual is None:
            print(f"- Übersprungen: Zone '{zone}' nicht gefunden. Verfügbar: {', '.join(sorted(all_zones))}")
            continue

        for var in args.vars:
            var_key = find_var_name(by_zone[zone_actual], var)
            if var_key is None:
                avail = ", ".join(sorted(by_zone[zone_actual].keys()))
                print(f"  - Übersprungen: '{zone_actual}:{var}' nicht gefunden. Verfügbar: {avail}")
                continue

            col = pick_column(by_zone[zone_actual][var_key])
            y = pd.to_numeric(df[col], errors="coerce")
            ylabel = re.sub(r".*\[(.*)\].*", r"[\1]", col)
            if ylabel == col:
                ylabel = var_key
            title = f"{zone_actual} – {var_key}"
            safe_zone = re.sub(r"[^A-Za-z0-9_-]+", "_", zone_actual)
            safe_var = re.sub(r"[^A-Za-z0-9_-]+", "_", var_key)
            out_path = out_dir / f"{safe_zone}__{safe_var}.png"
            plot_series(dt, y, title, ylabel, out_path, args.dpi)
            print(f"  ✓ {zone_actual}:{var_key} → {out_path}")

            # Tagesstatistik für Temperatur automatisch erzeugen
            if normalize(var_key) in [normalize(v) for v in SYNONYMS["zone air temperature"]]:
                ts = pd.Series(pd.to_numeric(df[col], errors="coerce").values, index=dt).dropna()
                if not ts.empty:
                    daily = ts.resample("D").agg(["mean", "min", "max"])
                    csv_daily = out_dir / f"{safe_zone}__ZoneAirTemperature_daily.csv"
                    daily.to_csv(csv_daily, index=True)
                    print(f"    ↳ Tagesstatistik gespeichert: {csv_daily}")

if __name__ == "__main__":
    main()
