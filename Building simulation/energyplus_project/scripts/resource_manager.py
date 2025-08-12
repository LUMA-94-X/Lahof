#!/usr/bin/env python3
"""
Österreichische EnergyPlus Resources - Management & Automation
=============================================================

Automatisches Verwalten/Validieren einer AT-EnergyPlus-Bibliothek inkl. U-Wert,
Excel-Export und dauerhaften DataFrame-Caches (CSV).

Author: EnergyPlus Austria Community
Version: 1.4 (CSV-Cache)
Date: 2025-08-12
"""

import os
import re
import json
import warnings
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import subprocess
import logging
from datetime import datetime

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('resources_management.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

@dataclass
class Material:
    """Repräsentiert ein EnergyPlus Material"""
    name: str
    thickness: float
    conductivity: float
    density: float
    specific_heat: float
    thermal_absorptance: float = 0.9
    solar_absorptance: float = 0.7
    visible_absorptance: float = 0.7

@dataclass
class Construction:
    """Repräsentiert eine EnergyPlus Konstruktion"""
    name: str
    layers: List[str]
    u_value: Optional[float] = None
    category: Optional[str] = None

class ResourceManager:
    """Hauptklasse für das Management der Resources"""
    
    def __init__(self, resources_path: str = "resources"):
        # Standardmäßig: .../energyplus_project/resources relativ zu diesem Script
        script_dir = Path(__file__).resolve().parent
        default_resources = script_dir.parent / "resources"
        
        rp = Path(resources_path)
        if resources_path == "resources" and default_resources.exists():
            rp = default_resources
        elif not rp.is_absolute():
            candidates = [
                (Path.cwd() / rp),
                (script_dir / rp),
                (script_dir.parent / rp),
                (script_dir.parent.parent / rp),
            ]
            for c in candidates:
                if c.exists():
                    rp = c.resolve()
                    break

        self.resources_path = rp
        logging.info(f"Suche IDFs unter: {self.resources_path}")

        self.materials: Dict[str, Material] = {}
        self.constructions: Dict[str, Construction] = {}
        self.window_U: Dict[str, float] = {}  # WindowMaterial:SimpleGlazingSystem (U-Factor)
        self.nomass_R: Dict[str, float] = {}  # NoMass/AirGap Widerstände nach Name

        # CSV-Cache Standardpfad + Format
        self.cache_dir = script_dir.parent / "cache"   # .../energyplus_project/cache
        self.cache_fmt = "csv"                         # <- CSV gewünscht

        # Laden & Parsen
        self.load_existing_resources()

        # Automatischer CSV-Cache: laden/mergen/speichern + als Attribute bereitstellen
        self._init_df_cache()
        
    def load_existing_resources(self):
        """Lädt alle existierenden Resources aus den IDF-Dateien"""
        logging.info("Lade existierende Resources...")
        # case-insensitive .idf
        idf_files = list(self.resources_path.rglob("*.[iI][dD][fF]"))
        if not idf_files:
            logging.warning(f"Keine IDF-Dateien gefunden unter: {self.resources_path}")
        for p in idf_files:
            logging.info(f"Gefundenes IDF: {p}")
        for idf_file in idf_files:
            self._parse_idf_file(idf_file)
        logging.info(f"Geladen: {len(self.materials)} Materialien, {len(self.constructions)} Konstruktionen")

    def _parse_idf_file(self, file_path: Path):
        """Sehr robuster IDF-Parser: Split an ';', Typ = Präfix bis 1. Komma (Spaces entfernt)."""
        try:
            # robust lesen (UTF-8, Fallback cp1252)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='cp1252') as f:
                    content = f.read()

            # Kommentare bis Zeilenende entfernen
            content = re.sub(r'!.*$', '', content, flags=re.MULTILINE)
            # NBSP/Zero-Width entfernen, Tabs -> Space
            content = content.replace('\xa0', ' ').replace('\u200b', '')
            content = content.replace('\t', ' ')

            # In Blöcke splitten
            raw_blocks = content.split(';')

            cnt_mat = cnt_nomass = cnt_airgap = cnt_win = cnt_con = 0

            for raw in raw_blocks:
                block = raw.strip()
                if not block or ',' not in block:
                    continue

                # Typ = Präfix bis erstes Komma (Spaces im Typ entfernen)
                type_part, payload = block.split(',', 1)
                typ_token = type_part.strip().lower().replace(' ', '')
                fields = [x.strip() for x in payload.split(',') if x.strip()]

                # --- Material ---
                if typ_token == 'material':
                    if len(fields) < 6:
                        logging.warning(f"Material zu wenige Felder in {file_path.name}: {fields[:3]}...")
                        continue
                    name = fields[0]
                    try:
                        thickness = float(fields[2])
                        conductivity = float(fields[3])
                        density = float(fields[4])
                        specific_heat = float(fields[5])
                        thermal_abs = float(fields[6]) if len(fields) > 6 else 0.9
                        solar_abs   = float(fields[7]) if len(fields) > 7 else 0.7
                        visible_abs = float(fields[8]) if len(fields) > 8 else 0.7
                        self.materials[name] = Material(
                            name=name,
                            thickness=thickness,
                            conductivity=conductivity,
                            density=density,
                            specific_heat=specific_heat,
                            thermal_absorptance=thermal_abs,
                            solar_absorptance=solar_abs,
                            visible_absorptance=visible_abs
                        )
                        cnt_mat += 1
                    except ValueError as e:
                        logging.warning(f"Fehler beim Parsen von Material {name}: {e}")

                # --- Material:NoMass ---
                elif typ_token == 'material:nomass':
                    if len(fields) < 3:
                        continue
                    name = fields[0]
                    try:
                        R = float(fields[2])  # Thermal Resistance {m2-K/W}
                        self.nomass_R[name] = R
                        cnt_nomass += 1
                    except ValueError:
                        logging.warning(f"Fehler beim Parsen von Material:NoMass {name}")

                # --- Material:AirGap ---
                elif typ_token == 'material:airgap':
                    if len(fields) < 2:
                        continue
                    name = fields[0]
                    try:
                        R = float(fields[1])  # Thermal Resistance {m2-K/W}
                        self.nomass_R[name] = R
                        cnt_airgap += 1
                    except ValueError:
                        logging.warning(f"Fehler beim Parsen von Material:AirGap {name}")

                # --- WindowMaterial:SimpleGlazingSystem ---
                elif typ_token == 'windowmaterial:simpleglazingsystem':
                    if len(fields) < 2:
                        continue
                    name = fields[0]
                    try:
                        u_factor = float(fields[1])  # U-Factor {W/m2-K}
                        self.window_U[name] = u_factor
                        cnt_win += 1
                    except ValueError:
                        logging.warning(f"Fehler beim Parsen von SimpleGlazing {name}")

                # --- Construction ---
                elif typ_token == 'construction':
                    if len(fields) < 2:
                        continue
                    name = fields[0]
                    layers = [x for x in fields[1:] if x]
                    self.constructions[name] = Construction(name=name, layers=layers)
                    cnt_con += 1

                # andere Typen ignorieren

            logging.info(f"  -> {cnt_mat} Material, {cnt_nomass} NoMass, {cnt_airgap} AirGap, {cnt_win} SimpleGlazing, {cnt_con} Konstruktionen in {file_path.name}")

        except Exception as e:
            logging.error(f"Fehler beim Parsen von {file_path}: {e}")

    def calculate_u_value(self, construction_name: str) -> Optional[float]:
        """Berechnet den U-Wert einer Konstruktion"""
        if construction_name not in self.constructions:
            logging.error(f"Konstruktion {construction_name} nicht gefunden")
            return None
            
        construction = self.constructions[construction_name]

        # Fenster-Spezialfall: Wenn eine Schicht ein SimpleGlazing ist, nutze dessen U-Factor direkt
        for layer_name in construction.layers:
            if layer_name in self.window_U:
                u = self.window_U[layer_name]
                self.constructions[construction_name].u_value = u
                return u
        
        # Wärmewiderstände: Rsi (innen) + Schichten + Rse (außen)
        total_resistance = 0.125 + 0.04  # Standard Wärmeübergangswiderstände
        
        for layer_name in construction.layers:
            if layer_name in self.materials:
                material = self.materials[layer_name]
                try:
                    resistance = material.thickness / material.conductivity
                except ZeroDivisionError:
                    logging.warning(f"λ=0 bei {layer_name}, ignoriere Schicht")
                    resistance = 0.0
                total_resistance += resistance
            elif layer_name in self.nomass_R:
                total_resistance += self.nomass_R[layer_name]
            elif re.search(r'luft|air|gap', layer_name, re.IGNORECASE):
                # einfache Pauschale für Luftschicht
                total_resistance += 0.17
            else:
                logging.warning(f"Material {layer_name} nicht gefunden in {construction_name}")
                
        if total_resistance <= 0:
            logging.error(f"Gesamtwiderstand <= 0 bei {construction_name}")
            return None

        u_value = 1.0 / total_resistance
        self.constructions[construction_name].u_value = u_value
        return u_value

    def validate_austrian_standards(self) -> Dict[str, List[str]]:
        """Validiert alle Konstruktionen gegen österreichische Standards"""
        logging.info("Validiere gegen österreichische Standards...")
        
        issues = {
            'u_value_too_high': [],
            'missing_materials': [],
            'naming_convention': [],
            'passivhaus_ready': []
        }
        
        # Österreichische U-Wert Grenzwerte (OIB RL6)
        austrian_limits = {
            'Außenwand': 0.35,
            'Dach': 0.20,
            'Bodenplatte': 0.40,
            'Fenster': 1.40
        }
        
        passivhaus_limits = {
            'Außenwand': 0.15,
            'Dach': 0.10,
            'Bodenplatte': 0.15,
            'Fenster': 0.80
        }
        
        for name, construction in self.constructions.items():
            # U-Wert berechnen
            u_value = self.calculate_u_value(name)
            if u_value is None:
                continue
                
            # Kategorisierung basierend auf Namen
            category = self._categorize_construction(name)
            construction.category = category
            
            # Österreichische Standards prüfen
            if category in austrian_limits:
                if u_value > austrian_limits[category]:
                    issues['u_value_too_high'].append(
                        f"{name}: {u_value:.3f} W/m²K (Grenzwert: {austrian_limits[category]} W/m²K)"
                    )
                    
                # Passivhaus Standard prüfen
                if u_value <= passivhaus_limits[category]:
                    issues['passivhaus_ready'].append(f"{name}: {u_value:.3f} W/m²K")
            
            # Namenskonvention prüfen
            if not name.startswith('AT_'):
                issues['naming_convention'].append(f"{name}: Fehlt 'AT_' Präfix")
                
            # Fehlende Materialien
            for layer in construction.layers:
                if (layer not in self.materials) and (layer not in self.nomass_R) and not re.search(r'luft|air|gap', layer, re.IGNORECASE):
                    issues['missing_materials'].append(f"{name}: Material '{layer}' fehlt")
        
        return issues

    def _categorize_construction(self, name: str) -> str:
        """Kategorisiert eine Konstruktion basierend auf dem Namen"""
        name_lower = name.lower()
        if any(keyword in name_lower for keyword in ['außenwand', 'aussenwand', 'fassade']):
            return 'Außenwand'
        elif any(keyword in name_lower for keyword in ['dach', 'roof']):
            return 'Dach'
        elif any(keyword in name_lower for keyword in ['boden', 'bodenplatte', 'fundament']):
            return 'Bodenplatte'
        elif any(keyword in name_lower for keyword in ['fenster', 'window']):
            return 'Fenster'
        elif any(keyword in name_lower for keyword in ['innenwand', 'trennwand']):
            return 'Innenwand'
        else:
            return 'Unbekannt'

    def generate_material_database(self) -> pd.DataFrame:
        """Erstellt eine DataFrame-Datenbank aller Materialien"""
        data = []
        for name, material in self.materials.items():
            data.append({
                'Name': name,
                'Dicke [m]': material.thickness,
                'Wärmeleitfähigkeit [W/mK]': material.conductivity,
                'Dichte [kg/m³]': material.density,
                'Spez. Wärmekapazität [J/kgK]': material.specific_heat,
                'Wärmewiderstand [m²K/W]': (material.thickness / material.conductivity) if material.conductivity else None,
                'Thermische Trägheit [kJ/m²K]': (material.density * material.specific_heat * material.thickness) / 1000.0,
                'Solar Absorptionsgrad': material.solar_absorptance,
                'Kategorie': self._categorize_material(name)
            })
        # NoMass/AirGap separat als Zeilen hinzufügen (mit R direkt)
        for name, R in self.nomass_R.items():
            data.append({
                'Name': name,
                'Dicke [m]': None,
                'Wärmeleitfähigkeit [W/mK]': None,
                'Dichte [kg/m³]': None,
                'Spez. Wärmekapazität [J/kgK]': None,
                'Wärmewiderstand [m²K/W]': R,
                'Thermische Trägheit [kJ/m²K]': None,
                'Solar Absorptionsgrad': None,
                'Kategorie': 'NoMass/AirGap'
            })
        df = pd.DataFrame(data)
        return df.sort_values(['Kategorie', 'Name'], na_position='last')

    def _categorize_material(self, name: str) -> str:
        """Kategorisiert Materialien"""
        name_lower = name.lower()
        if any(keyword in name_lower for keyword in ['dämmung', 'eps', 'steinwolle', 'pur', 'zellulose']):
            return 'Dämmstoffe'
        elif any(keyword in name_lower for keyword in ['ziegel', 'beton', 'porenbeton', 'mauerwerk']):
            return 'Mauerwerk'
        elif any(keyword in name_lower for keyword in ['holz', 'bsh', 'osb']):
            return 'Holzwerkstoffe'
        elif any(keyword in name_lower for keyword in ['putz', 'gips', 'beschichtung']):
            return 'Putze & Beschichtungen'
        elif any(keyword in name_lower for keyword in ['dach', 'ziegel', 'bitumen']):
            return 'Dacheindeckung'
        else:
            return 'Sonstige'

    def generate_construction_report(self) -> pd.DataFrame:
        """Erstellt einen Bericht aller Konstruktionen mit U-Werten"""
        data = []
        for name, construction in self.constructions.items():
            u_value = self.calculate_u_value(name)
            data.append({
                'Name': name,
                'Kategorie': construction.category or 'Unbekannt',
                'Anzahl Schichten': len(construction.layers),
                'Schichten': ' | '.join(construction.layers),
                'U-Wert [W/m²K]': round(u_value, 3) if u_value is not None else 'Fehler',
                'OIB-konform': self._check_oib_compliance(construction.category, u_value),
                'Passivhaus-tauglich': self._check_passivhaus_compliance(construction.category, u_value)
            })
        df = pd.DataFrame(data)
        # robust sortieren
        if 'U-Wert [W/m²K]' in df.columns:
            tmp = pd.to_numeric(df['U-Wert [W/m²K]'], errors='coerce')
            df = df.assign(_usort=tmp).sort_values(['Kategorie', '_usort']).drop(columns=['_usort'])
        return df

    def _check_oib_compliance(self, category: str, u_value: Optional[float]) -> str:
        """Prüft OIB-Konformität"""
        if u_value is None:
            return 'Unbekannt'
        limits = {'Außenwand': 0.35, 'Dach': 0.20, 'Bodenplatte': 0.40, 'Fenster': 1.40}
        if category in limits:
            return '✓ Ja' if u_value <= limits[category] else '✗ Nein'
        return 'N/A'

    def _check_passivhaus_compliance(self, category: str, u_value: Optional[float]) -> str:
        """Prüft Passivhaus-Tauglichkeit"""
        if u_value is None:
            return 'Unbekannt'
        limits = {'Außenwand': 0.15, 'Dach': 0.10, 'Bodenplatte': 0.15, 'Fenster': 0.80}
        if category in limits:
            return '✓ Ja' if u_value <= limits[category] else '✗ Nein'
        return 'N/A'

    def run_energyplus_simulation(self, idf_path: str, epw_path: str, output_dir: str = "output"):
        """Führt EnergyPlus Simulation aus"""
        logging.info(f"Starte EnergyPlus Simulation: {idf_path}")
        os.makedirs(output_dir, exist_ok=True)
        try:
            cmd = ['energyplus', '-w', epw_path, '-d', output_dir, idf_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logging.info("Simulation erfolgreich abgeschlossen")
                return True
            else:
                logging.error(f"Simulation fehlgeschlagen: {result.stderr}")
                return False
        except Exception as e:
            logging.error(f"Fehler beim Ausführen von EnergyPlus: {e}")
            return False

    def batch_simulation(self, scenarios: Dict[str, Dict]) -> Dict[str, bool]:
        """Führt Batch-Simulationen für verschiedene Szenarien aus"""
        results = {}
        for scenario_name, config in scenarios.items():
            logging.info(f"Starte Szenario: {scenario_name}")
            modified_idf = self._create_scenario_idf(config)  # TODO implement
            success = self.run_energyplus_simulation(
                modified_idf,
                config.get('weather_file', 'weather/AUT_SZ_Salzburg.epw'),
                f"output/{scenario_name}"
            )
            results[scenario_name] = success
        return results

    def _create_scenario_idf(self, config: Dict) -> str:
        """Erstellt eine modifizierte IDF-Datei für ein Szenario"""
        # TODO: implementieren (Layer-Mapping etc.)
        raise NotImplementedError("Szenario-IDF-Erzeugung ist noch nicht implementiert.")

    # ------------------------------
    # Persistente DF-Caches (CSV)
    # ------------------------------
    def _init_df_cache(self):
        """Lädt vorhandene DFs (falls da), erstellt neue aus IDFs, mergt & speichert. Setzt self.df_materials/-constructions."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Neu erzeugt (aus IDFs)
        new_mats = self.generate_material_database().copy()
        new_cons = self.generate_construction_report().copy()
        ts = datetime.now().isoformat(timespec='seconds')
        new_mats['last_updated'] = ts
        new_cons['last_updated'] = ts

        # Alt lesen (CSV)
        mats_old = self._read_csv_if_exists(self.cache_dir / "materials.csv")
        cons_old = self._read_csv_if_exists(self.cache_dir / "constructions.csv")

        # Mergen (neue Werte überschreiben alte)
        mats_merged = self._merge_updates(mats_old, new_mats, keys=['Name'])
        cons_merged = self._merge_updates(cons_old, new_cons, keys=['Name'])

        # Speichern (CSV)
        mats_csv = self.cache_dir / "materials.csv"
        cons_csv = self.cache_dir / "constructions.csv"
        mats_merged.to_csv(mats_csv, index=False)
        cons_merged.to_csv(cons_csv, index=False)
        logging.info(f"DF-Cache aktualisiert (CSV): {mats_csv} / {cons_csv}")

        # Als Attribut bereitstellen
        self.df_materials = mats_merged
        self.df_constructions = cons_merged

    def _merge_updates(self, old_df: Optional[pd.DataFrame], new_df: pd.DataFrame, keys: List[str]) -> pd.DataFrame:
        """Union beider DFs; neue Nicht-Null-Werte überschreiben alte (gleiche Keys)."""
        if old_df is None or old_df.empty:
            return new_df
        merged = old_df.merge(new_df, on=keys, how='outer', suffixes=('_old', ''))
        for col in new_df.columns:
            if col in keys:
                continue
            old_col = f"{col}_old"
            if old_col in merged.columns:
                merged[col] = merged[col].combine_first(merged[old_col])
                merged.drop(columns=[old_col], inplace=True)
        # evtl. Reste wegräumen
        for c in list(merged.columns):
            if c.endswith('_old'):
                merged.drop(columns=c, inplace=True)
        return merged

    def _read_csv_if_exists(self, path: Path) -> Optional[pd.DataFrame]:
        try:
            return pd.read_csv(path)
        except Exception:
            return None

    def save_or_update_cache(self, cache_dir: str = None, fmt: str = None):
        """Optionale manuelle Cache-Aktualisierung über CLI."""
        cache_dir = Path(cache_dir or self.cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        mats_new = self.generate_material_database().copy()
        cons_new = self.generate_construction_report().copy()
        ts = datetime.now().isoformat(timespec='seconds')
        mats_new['last_updated'] = ts
        cons_new['last_updated'] = ts

        old_mats = self._read_csv_if_exists(cache_dir / "materials.csv")
        old_cons = self._read_csv_if_exists(cache_dir / "constructions.csv")

        mats_out = self._merge_updates(old_mats, mats_new, keys=['Name'])
        cons_out = self._merge_updates(old_cons, cons_new, keys=['Name'])

        mats_out.to_csv(cache_dir / "materials.csv", index=False)
        cons_out.to_csv(cache_dir / "constructions.csv", index=False)
        logging.info(f"Cache aktualisiert (CSV): {cache_dir/'materials.csv'} / {cache_dir/'constructions.csv'}")

    def export_to_excel(self, output_file: str = "Austrian_EnergyPlus_Database.xlsx"):
        """Exportiert alle Daten zu Excel"""
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Materialien
            materials_df = self.generate_material_database()
            materials_df.to_excel(writer, sheet_name='Materialien', index=False)
            # Konstruktionen
            constructions_df = self.generate_construction_report()
            constructions_df.to_excel(writer, sheet_name='Konstruktionen', index=False)
            # Validierungsbericht
            issues = self.validate_austrian_standards()
            validation_data = []
            for issue_type, items in issues.items():
                for item in items:
                    validation_data.append({'Problem-Typ': issue_type, 'Details': item})
            if validation_data:
                validation_df = pd.DataFrame(validation_data)
                validation_df.to_excel(writer, sheet_name='Validierung', index=False)
        logging.info(f"Excel-Datei erstellt: {output_file}")

    def create_project_template(self, project_name: str, building_type: str = "EFH"):
        """Erstellt ein neues Projekt-Template"""
        template_dir = Path(f"projects/{project_name}")
        template_dir.mkdir(parents=True, exist_ok=True)
        # Basis IDF kopieren (Platzhalter)
        if building_type == "EFH":
            template_source = "templates/salzburg_efh_template.idf"
        else:
            template_source = "templates/generic_template.idf"
        project_idf = template_dir / f"{project_name}.idf"
        (template_dir / "weather").mkdir(exist_ok=True)
        (template_dir / "output").mkdir(exist_ok=True)
        (template_dir / "scripts").mkdir(exist_ok=True)
        logging.info(f"Projekt-Template erstellt: {template_dir}")

# CLI Interface
def main():
    """Hauptfunktion für Command Line Interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Österreichische EnergyPlus Resources Management")
    parser.add_argument('--validate', action='store_true', help='Validiere alle Ressourcen')
    parser.add_argument('--export-excel', type=str, help='Exportiere zu Excel')
    parser.add_argument('--create-project', type=str, help='Neues Projekt erstellen')
    parser.add_argument('--run-simulation', type=str, help='Simulation ausführen')
    parser.add_argument('--weather-file', type=str, default='weather/AUT_SZ_Salzburg.epw')
    parser.add_argument('--resources', type=str, default='resources',
                        help='Pfad zur Resource-IDF-Bibliothek')

    # Optional: manuelles Cache-Update (CSV)
    parser.add_argument('--update-cache', action='store_true',
                        help='Material- & Konstruktions-DFs persistieren/aktualisieren (CSV)')
    parser.add_argument('--cache-dir', type=str, default=None,
                        help='Ablageordner für Cache-DFs (Standard: .../energyplus_project/cache)')

    args = parser.parse_args()
    
    # Resource Manager initialisieren (mit --resources)
    rm = ResourceManager(resources_path=args.resources)
    
    if args.validate:
        issues = rm.validate_austrian_standards()
        print("\n=== VALIDIERUNGSBERICHT ===")
        any_issue = False
        for issue_type, items in issues.items():
            if items:
                any_issue = True
                print(f"\n{issue_type.upper().replace('_', ' ')}:")
                for item in items:
                    print(f"  • {item}")
        if not any_issue:
            print("\nKeine Probleme gefunden.")
                    
    if args.export_excel:
        rm.export_to_excel(args.export_excel)
        print(f"Excel-Export abgeschlossen: {args.export_excel}")

    if args.update_cache:
        rm.save_or_update_cache(cache_dir=args.cache_dir)
        print(f"Cache aktualisiert (CSV) unter: {args.cache_dir or rm.cache_dir}")
        
    if args.create_project:
        rm.create_project_template(args.create_project)
        print(f"Projekt erstellt: {args.create_project}")
        
    if args.run_simulation:
        try:
            success = rm.run_energyplus_simulation(args.run_simulation, args.weather_file)
            print("Simulation erfolgreich abgeschlossen" if success else "Simulation fehlgeschlagen")
        except NotImplementedError as e:
            print(str(e))

# Beispiel Batch-Simulation Configuration (derzeit nicht automatisch genutzt)
SALZBURG_SCENARIOS = {
    "Bestand_Sanierung": {
        "constructions": {
            "AT_Außenwand_WDVS_Standard": "AT_Außenwand_Bestand_Saniert",
            "AT_Fenster_3fach_Standard": "AT_Fenster_2fach_Bestand"
        },
        "weather_file": "weather/AUT_SZ_Salzburg.epw",
        "description": "Sanierung eines Bestandsgebäudes auf aktuellen Standard"
    },
    "Passivhaus_Neubau": {
        "constructions": {
            "AT_Außenwand_WDVS_Standard": "AT_Außenwand_Passivhaus",
            "AT_Steildach_Standard": "AT_Dach_Passivhaus",
            "AT_Fenster_3fach_Standard": "AT_Fenster_Passivhaus"
        },
        "weather_file": "weather/AUT_SZ_Salzburg.epw",
        "description": "Passivhaus-Standard Neubau"
    },
    "Klimawandel_2050": {
        "weather_file": "weather/AUT_SZ_Salzburg_2050.epw",
        "description": "Zukunftsszenario mit Klimawandel-Wetterdaten"
    }
}

# Utility Funktionen (Platzhalter)
def calculate_lifecycle_costs(construction_name: str, building_area: float, lifetime_years: int = 50):
    """Berechnet Lebenszykluskosten einer Konstruktion"""
    pass

def optimize_construction(target_u_value: float, available_materials: List[str]) -> Construction:
    """Optimiert eine Konstruktion für einen Ziel-U-Wert"""
    pass

if __name__ == "__main__":
    main()
