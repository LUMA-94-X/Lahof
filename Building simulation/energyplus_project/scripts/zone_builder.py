#!/usr/bin/env python3
"""
Zone Builder für EnergyPlus - Österreichische Standards
======================================================

Automatisches Erstellen von Zonen mit österreichischen Standards
und modularer Herangehensweise für schrittweisen Gebäudeaufbau.

Author: EnergyPlus Austria Community
Version: 1.0
Date: 2025-08-12
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import json

@dataclass
class ZoneConfig:
    """Konfiguration für eine Zone"""
    name: str
    room_type: str  # 'wohnzimmer', 'kueche', 'schlafzimmer', 'badezimmer', etc.
    dimensions: Tuple[float, float, float]  # (width, depth, height)
    position: Tuple[float, float, float]    # (x, y, z) offset
    orientation: float = 0.0  # Rotation in degrees
    constructions: Dict[str, str] = None  # Override default constructions
    windows: List[Dict] = None  # Window definitions
    people_count: float = 1.0
    lighting_power: float = 100.0  # W
    equipment_power: float = 50.0   # W

class ZoneBuilder:
    """Hauptklasse für das Erstellen von Zonen"""
    
    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path)
        self.zones_dir = self.project_path / "resources" / "zones"
        self.zones_dir.mkdir(parents=True, exist_ok=True)
        
        # Österreichische Standard-Raumtypen
        self.room_defaults = {
            'wohnzimmer': {
                'dimensions': (5.0, 6.0, 2.7),
                'people_count': 2.5,
                'lighting_power': 300,
                'equipment_power': 500,
                'heating_setpoint': 'AT_Heizung_Zeitplan',
                'windows': [
                    {'wall': 'sued', 'width': 4.0, 'height': 1.4, 'sill_height': 0.8}
                ]
            },
            'kueche': {
                'dimensions': (4.0, 3.0, 2.7),
                'people_count': 1.0,
                'lighting_power': 180,
                'equipment_power': 800,
                'heating_setpoint': 'AT_Heizung_Zeitplan',
                'windows': [
                    {'wall': 'nord', 'width': 2.4, 'height': 1.4, 'sill_height': 0.8}
                ]
            },
            'schlafzimmer': {
                'dimensions': (4.0, 4.0, 2.7),
                'people_count': 2.0,
                'lighting_power': 100,
                'equipment_power': 50,
                'heating_setpoint': 'AT_Heizung_Schlafbereich',
                'windows': [
                    {'wall': 'sued', 'width': 1.0, 'height': 1.4, 'sill_height': 0.8}
                ]
            },
            'badezimmer': {
                'dimensions': (2.5, 3.0, 2.7),
                'people_count': 0.5,
                'lighting_power': 120,
                'equipment_power': 200,
                'heating_setpoint': 'BAD_Heizung_Zeitplan',
                'windows': [
                    {'wall': 'nord', 'width': 1.1, 'height': 0.8, 'sill_height': 1.2}
                ]
            },
            'buero': {
                'dimensions': (3.5, 4.0, 2.7),
                'people_count': 1.0,
                'lighting_power': 200,
                'equipment_power': 300,
                'heating_setpoint': 'AT_Heizung_Zeitplan',
                'windows': [
                    {'wall': 'sued', 'width': 1.5, 'height': 1.4, 'sill_height': 0.8}
                ]
            },
            'keller': {
                'dimensions': (4.0, 6.0, 2.3),
                'people_count': 0.1,
                'lighting_power': 80,
                'equipment_power': 100,
                'heating_setpoint': 'Keller_Heizung_Zeitplan',
                'windows': [
                    {'wall': 'sued', 'width': 0.8, 'height': 0.6, 'sill_height': 2.0}
                ]
            }
        }
        
        # Österreichische Standard-Konstruktionen
        self.constructions = {
            'exterior_wall': 'AT_Außenwand_WDVS_Standard',
            'interior_wall': 'AT_Innenwand_Ziegel_14cm',
            'floor': 'AT_Zwischendecke_Standard',
            'ceiling': 'AT_Zwischendecke_Standard',
            'roof': 'AT_Steildach_Standard',
            'window': 'AT_Fenster_3fach_Standard',
            'door': 'AT_Innentür_Standard'
        }

    def create_zone_template(self, zone_config: ZoneConfig) -> str:
        """Erstellt eine Zone basierend auf der Konfiguration"""
        
        # Merge with room defaults
        defaults = self.room_defaults.get(zone_config.room_type, {})
        
        if not zone_config.dimensions:
            zone_config.dimensions = defaults.get('dimensions', (4.0, 4.0, 2.7))
        if not zone_config.people_count:
            zone_config.people_count = defaults.get('people_count', 1.0)
        if not zone_config.lighting_power:
            zone_config.lighting_power = defaults.get('lighting_power', 100)
        if not zone_config.equipment_power:
            zone_config.equipment_power = defaults.get('equipment_power', 50)
        if not zone_config.windows:
            zone_config.windows = defaults.get('windows', [])
            
        # Generate IDF content
        idf_content = self._generate_zone_idf(zone_config, defaults)
        
        return idf_content

    def _generate_zone_idf(self, config: ZoneConfig, defaults: Dict) -> str:
        """Generiert den IDF-Code für eine Zone"""
        
        width, depth, height = config.dimensions
        x, y, z = config.position
        
        zone_name = f"AT_Zone_{config.name}"
        
        idf = f"""! ========================================================================
! ZONE: {config.name.upper()} ({config.room_type})
! Automatisch generiert - {width}m x {depth}m x {height}m
! ========================================================================

Zone,
    {zone_name},             !- Name
    {config.orientation},    !- Direction of Relative North {{deg}}
    {x},                     !- X Origin {{m}}
    {y},                     !- Y Origin {{m}}
    {z},                     !- Z Origin {{m}}
    1,                       !- Type
    1,                       !- Multiplier
    autocalculate,           !- Ceiling Height {{m}}
    autocalculate;           !- Volume {{m3}}

! {config.name} Grundfläche
BuildingSurface:Detailed,
    {zone_name}_Boden,       !- Name
    Floor,                   !- Surface Type
    {self.constructions['floor']}, !- Construction Name
    {zone_name},             !- Zone Name
    OtherSideCoefficients,   !- Outside Boundary Condition
    ,                        !- Outside Boundary Condition Object
    NoSun,                   !- Sun Exposure
    NoWind,                  !- Wind Exposure
    1.0,                     !- View Factor to Ground
    4,                       !- Number of Vertices
    {x},{y},{z},             !- X,Y,Z ==> Vertex 1 {{m}}
    {x},{y+depth},{z},       !- X,Y,Z ==> Vertex 2 {{m}}
    {x+width},{y+depth},{z}, !- X,Y,Z ==> Vertex 3 {{m}}
    {x+width},{y},{z};       !- X,Y,Z ==> Vertex 4 {{m}}

! {config.name} Decke
BuildingSurface:Detailed,
    {zone_name}_Decke,       !- Name
    Ceiling,                 !- Surface Type
    {self.constructions['ceiling']}, !- Construction Name
    {zone_name},             !- Zone Name
    OtherSideCoefficients,   !- Outside Boundary Condition
    ,                        !- Outside Boundary Condition Object
    NoSun,                   !- Sun Exposure
    NoWind,                  !- Wind Exposure
    0,                       !- View Factor to Ground
    4,                       !- Number of Vertices
    {x},{y},{z+height},      !- X,Y,Z ==> Vertex 1 {{m}}
    {x+width},{y},{z+height}, !- X,Y,Z ==> Vertex 2 {{m}}
    {x+width},{y+depth},{z+height}, !- X,Y,Z ==> Vertex 3 {{m}}
    {x},{y+depth},{z+height}; !- X,Y,Z ==> Vertex 4 {{m}}

! {config.name} Wände
{self._generate_walls(config, zone_name, x, y, z, width, depth, height)}

{self._generate_windows(config, zone_name, x, y, z, width, depth, height)}

! {config.name} Thermostat
ZoneControl:Thermostat,
    {zone_name}_Thermostat,  !- Name
    {zone_name},             !- Zone or ZoneList Name
    AT_Dual_Zone_Control,    !- Control Type Schedule Name
    ThermostatSetpoint:DualSetpoint, !- Control Object Type 1
    {zone_name}_Setpoint;    !- Control Name 1

ThermostatSetpoint:DualSetpoint,
    {zone_name}_Setpoint,    !- Name
    {defaults.get('heating_setpoint', 'AT_Heizung_Zeitplan')}, !- Heating Setpoint Temperature Schedule Name
    AT_Kühlung_Zeitplan;     !- Cooling Setpoint Temperature Schedule Name

! {config.name} Menschen
People,
    {zone_name}_People,      !- Name
    {zone_name},             !- Zone or ZoneList Name
    {config.name}_Anwesenheit, !- Number of People Schedule Name
    people,                  !- Number of People Calculation Method
    {config.people_count},   !- Number of People
    ,                        !- People per Zone Floor Area {{person/m2}}
    ,                        !- Zone Floor Area per Person {{m2/person}}
    0.3,                     !- Fraction Radiant
    ,                        !- Sensible Heat Fraction
    {config.name}_Aktivitaet; !- Activity Level Schedule Name

! {config.name} Beleuchtung
Lights,
    {zone_name}_Lights,      !- Name
    {zone_name},             !- Zone or ZoneList Name
    {config.name}_Beleuchtung, !- Schedule Name
    LightingLevel,           !- Design Level Calculation Method
    {config.lighting_power}, !- Lighting Level {{W}}
    ,                        !- Watts per Zone Floor Area {{W/m2}}
    ,                        !- Watts per Person {{W/person}}
    0,                       !- Return Air Fraction
    0.4,                     !- Fraction Radiant
    0.2,                     !- Fraction Visible
    1.0,                     !- Fraction Replaceable
    General,                 !- End-Use Subcategory
    No;                      !- Return Air Fraction Calculated from Plenum Temperature

! {config.name} Elektrogeräte
ElectricEquipment,
    {zone_name}_Equipment,   !- Name
    {zone_name},             !- Zone or ZoneList Name
    {config.name}_Geraete,   !- Schedule Name
    EquipmentLevel,          !- Design Level Calculation Method
    {config.equipment_power}, !- Design Level {{W}}
    ,                        !- Watts per Zone Floor Area {{W/m2}}
    ,                        !- Watts per Person {{W/person}}
    0,                       !- Fraction Latent
    0.3,                     !- Fraction Radiant
    0,                       !- Fraction Lost
    General;                 !- End-Use Subcategory

{self._generate_schedules(config)}

"""
        return idf

    def _generate_walls(self, config: ZoneConfig, zone_name: str, x: float, y: float, z: float, 
                       width: float, depth: float, height: float) -> str:
        """Generiert die Wände für eine Zone"""
        
        walls = []
        
        # Süd-Wand (y=0 Seite)
        walls.append(f"""BuildingSurface:Detailed,
    {zone_name}_Wand_Sued,   !- Name
    Wall,                    !- Surface Type
    {self.constructions['exterior_wall']}, !- Construction Name
    {zone_name},             !- Zone Name
    Outdoors,                !- Outside Boundary Condition
    ,                        !- Outside Boundary Condition Object
    SunExposed,              !- Sun Exposure
    WindExposed,             !- Wind Exposure
    0.5,                     !- View Factor to Ground
    4,                       !- Number of Vertices
    {x},{y},{z+height},      !- X,Y,Z ==> Vertex 1 {{m}}
    {x},{y},{z},             !- X,Y,Z ==> Vertex 2 {{m}}
    {x+width},{y},{z},       !- X,Y,Z ==> Vertex 3 {{m}}
    {x+width},{y},{z+height}; !- X,Y,Z ==> Vertex 4 {{m}}""")

        # Nord-Wand (y=depth Seite)
        walls.append(f"""BuildingSurface:Detailed,
    {zone_name}_Wand_Nord,   !- Name
    Wall,                    !- Surface Type
    {self.constructions['exterior_wall']}, !- Construction Name
    {zone_name},             !- Zone Name
    Outdoors,                !- Outside Boundary Condition
    ,                        !- Outside Boundary Condition Object
    SunExposed,              !- Sun Exposure
    WindExposed,             !- Wind Exposure
    0.5,                     !- View Factor to Ground
    4,                       !- Number of Vertices
    {x+width},{y+depth},{z+height}, !- X,Y,Z ==> Vertex 1 {{m}}
    {x+width},{y+depth},{z}, !- X,Y,Z ==> Vertex 2 {{m}}
    {x},{y+depth},{z},       !- X,Y,Z ==> Vertex 3 {{m}}
    {x},{y+depth},{z+height}; !- X,Y,Z ==> Vertex 4 {{m}}""")

        # West-Wand (x=0 Seite)
        walls.append(f"""BuildingSurface:Detailed,
    {zone_name}_Wand_West,   !- Name
    Wall,                    !- Surface Type
    {self.constructions['exterior_wall']}, !- Construction Name
    {zone_name},             !- Zone Name
    Outdoors,                !- Outside Boundary Condition
    ,                        !- Outside Boundary Condition Object
    SunExposed,              !- Sun Exposure
    WindExposed,             !- Wind Exposure
    0.5,                     !- View Factor to Ground
    4,                       !- Number of Vertices
    {x},{y},{z+height},      !- X,Y,Z ==> Vertex 1 {{m}}
    {x},{y+depth},{z+height}, !- X,Y,Z ==> Vertex 2 {{m}}
    {x},{y+depth},{z},       !- X,Y,Z ==> Vertex 3 {{m}}
    {x},{y},{z};             !- X,Y,Z ==> Vertex 4 {{m}}""")

        # Ost-Wand (x=width Seite)
        walls.append(f"""BuildingSurface:Detailed,
    {zone_name}_Wand_Ost,    !- Name
    Wall,                    !- Surface Type
    {self.constructions['exterior_wall']}, !- Construction Name
    {zone_name},             !- Zone Name
    Outdoors,                !- Outside Boundary Condition
    ,                        !- Outside Boundary Condition Object
    SunExposed,              !- Sun Exposure
    WindExposed,             !- Wind Exposure
    0.5,                     !- View Factor to Ground
    4,                       !- Number of Vertices
    {x+width},{y},{z+height}, !- X,Y,Z ==> Vertex 1 {{m}}
    {x+width},{y},{z},       !- X,Y,Z ==> Vertex 2 {{m}}
    {x+width},{y+depth},{z}, !- X,Y,Z ==> Vertex 3 {{m}}
    {x+width},{y+depth},{z+height}; !- X,Y,Z ==> Vertex 4 {{m}}""")

        return "\n\n".join(walls)

    def _generate_windows(self, config: ZoneConfig, zone_name: str, x: float, y: float, z: float,
                         width: float, depth: float, height: float) -> str:
        """Generiert Fenster für eine Zone"""
        
        if not config.windows:
            return ""
            
        windows = []
        
        for i, window in enumerate(config.windows):
            wall_name = window['wall'].lower()
            win_width = window['width']
            win_height = window['height']
            sill_height = window['sill_height']
            
            # Fenster zentral in Wand positionieren
            if wall_name == 'sued':
                # Süd-Wand
                win_x_start = x + (width - win_width) / 2
                win_x_end = win_x_start + win_width
                win_y = y
                win_z_bottom = z + sill_height
                win_z_top = win_z_bottom + win_height
                
                vertices = f"""    {win_x_start},{win_y},{win_z_top},   !- X,Y,Z ==> Vertex 1 {{m}}
    {win_x_start},{win_y},{win_z_bottom}, !- X,Y,Z ==> Vertex 2 {{m}}
    {win_x_end},{win_y},{win_z_bottom},   !- X,Y,Z ==> Vertex 3 {{m}}
    {win_x_end},{win_y},{win_z_top};      !- X,Y,Z ==> Vertex 4 {{m}}"""
                building_surface = f"{zone_name}_Wand_Sued"
                
            elif wall_name == 'nord':
                # Nord-Wand
                win_x_start = x + (width - win_width) / 2
                win_x_end = win_x_start + win_width
                win_y = y + depth
                win_z_bottom = z + sill_height
                win_z_top = win_z_bottom + win_height
                
                vertices = f"""    {win_x_end},{win_y},{win_z_top},     !- X,Y,Z ==> Vertex 1 {{m}}
    {win_x_end},{win_y},{win_z_bottom},   !- X,Y,Z ==> Vertex 2 {{m}}
    {win_x_start},{win_y},{win_z_bottom}, !- X,Y,Z ==> Vertex 3 {{m}}
    {win_x_start},{win_y},{win_z_top};    !- X,Y,Z ==> Vertex 4 {{m}}"""
                building_surface = f"{zone_name}_Wand_Nord"
                
            elif wall_name == 'west':
                # West-Wand
                win_y_start = y + (depth - win_width) / 2
                win_y_end = win_y_start + win_width
                win_x = x
                win_z_bottom = z + sill_height
                win_z_top = win_z_bottom + win_height
                
                vertices = f"""    {win_x},{win_y_start},{win_z_top},   !- X,Y,Z ==> Vertex 1 {{m}}
    {win_x},{win_y_end},{win_z_top},     !- X,Y,Z ==> Vertex 2 {{m}}
    {win_x},{win_y_end},{win_z_bottom},  !- X,Y,Z ==> Vertex 3 {{m}}
    {win_x},{win_y_start},{win_z_bottom}; !- X,Y,Z ==> Vertex 4 {{m}}"""
                building_surface = f"{zone_name}_Wand_West"
                
            else:  # ost
                # Ost-Wand
                win_y_start = y + (depth - win_width) / 2
                win_y_end = win_y_start + win_width
                win_x = x + width
                win_z_bottom = z + sill_height
                win_z_top = win_z_bottom + win_height
                
                vertices = f"""    {win_x},{win_y_end},{win_z_top},     !- X,Y,Z ==> Vertex 1 {{m}}
    {win_x},{win_y_start},{win_z_top},   !- X,Y,Z ==> Vertex 2 {{m}}
    {win_x},{win_y_start},{win_z_bottom}, !- X,Y,Z ==> Vertex 3 {{m}}
    {win_x},{win_y_end},{win_z_bottom};  !- X,Y,Z ==> Vertex 4 {{m}}"""
                building_surface = f"{zone_name}_Wand_Ost"

            window_idf = f"""FenestrationSurface:Detailed,
    {zone_name}_Fenster_{wall_name.title()}_{i+1}, !- Name
    Window,                  !- Surface Type
    {self.constructions['window']}, !- Construction Name
    {building_surface},      !- Building Surface Name
    ,                        !- Outside Boundary Condition Object
    0.5,                     !- View Factor to Ground
    ,                        !- Frame and Divider Name
    1,                       !- Multiplier
    4,                       !- Number of Vertices
{vertices}"""

            windows.append(window_idf)
            
        return "\n\n".join(windows)

    def _generate_schedules(self, config: ZoneConfig) -> str:
        """Generiert raumspezifische Zeitpläne"""
        
        schedules = []
        
        # Anwesenheit basierend auf Raumtyp
        if config.room_type == 'schlafzimmer':
            anwesenheit = f"""Schedule:Compact,
    {config.name}_Anwesenheit,   !- Name
    Fraction,                !- Schedule Type Limits Name
    Through: 12/31,          !- Field 1
    For: AllDays,            !- Field 2
    Until: 7:00,1.0,         !- Field 3 (Schlafen)
    Until: 8:00,0.8,         !- Field 5 (Aufstehen)
    Until: 21:00,0.1,        !- Field 7 (Tagsüber selten im SZ)
    Until: 23:00,0.5,        !- Field 9 (Zu Bett gehen)
    Until: 24:00,1.0;        !- Field 11 (Schlafen)"""
        elif config.room_type == 'badezimmer':
            anwesenheit = f"""Schedule:Compact,
    {config.name}_Anwesenheit,   !- Name
    Fraction,                !- Schedule Type Limits Name
    Through: 12/31,          !- Field 1
    For: Weekdays,           !- Field 2
    Until: 6:00,0.0,         !- Field 3
    Until: 8:00,0.8,         !- Field 5 (Morgenroutine)
    Until: 18:00,0.1,        !- Field 7
    Until: 22:00,0.6,        !- Field 9 (Abendroutine)
    Until: 24:00,0.1,        !- Field 11
    For: Weekends Holidays,  !- Field 13
    Until: 8:00,0.0,         !- Field 14
    Until: 10:00,0.6,        !- Field 16
    Until: 22:00,0.2,        !- Field 18
    Until: 23:00,0.6,        !- Field 20
    Until: 24:00,0.1;        !- Field 22"""
        else:
            # Standard Wohnbereich
            anwesenheit = f"""Schedule:Compact,
    {config.name}_Anwesenheit,   !- Name
    Fraction,                !- Schedule Type Limits Name
    Through: 12/31,          !- Field 1
    For: Weekdays,           !- Field 2
    Until: 6:00,1.0,         !- Field 3
    Until: 8:00,1.0,         !- Field 5
    Until: 17:00,0.2,        !- Field 7 (Bei der Arbeit)
    Until: 23:00,1.0,        !- Field 9
    Until: 24:00,1.0,        !- Field 11
    For: Weekends Holidays,  !- Field 13
    Until: 23:00,0.9,        !- Field 14
    Until: 24:00,1.0;        !- Field 16"""
        
        schedules.append(anwesenheit)
        
        # Aktivitätslevel
        aktivitaet = f"""Schedule:Compact,
    {config.name}_Aktivitaet,    !- Name
    Activity Level,          !- Schedule Type Limits Name
    Through: 12/31,          !- Field 1
    For: AllDays,            !- Field 2
    Until: 6:00,70,          !- Field 3 (Schlaf)
    Until: 8:00,120,         !- Field 5 (Morgenroutine)
    Until: 18:00,100,        !- Field 7 (Normal)
    Until: 22:00,110,        !- Field 9 (Abends)
    Until: 24:00,70;         !- Field 11 (Ruhe)"""
        
        schedules.append(aktivitaet)
        
        # Beleuchtung - raumtypspezifisch
        if config.room_type == 'schlafzimmer':
            beleuchtung = f"""Schedule:Compact,
    {config.name}_Beleuchtung,   !- Name
    Fraction,                !- Schedule Type Limits Name
    Through: 12/31,          !- Field 1
    For: Weekdays,           !- Field 2
    Until: 6:00,0.0,         !- Field 3
    Until: 7:00,0.3,         !- Field 5 (Aufstehen)
    Until: 21:00,0.0,        !- Field 7
    Until: 23:00,0.4,        !- Field 9 (Zu Bett gehen)
    Until: 24:00,0.0,        !- Field 11
    For: Weekends Holidays,  !- Field 13
    Until: 8:00,0.0,         !- Field 14
    Until: 9:00,0.2,         !- Field 16
    Until: 22:00,0.0,        !- Field 18
    Until: 23:00,0.3,        !- Field 20
    Until: 24:00,0.0;        !- Field 22"""
        else:
            # Standard Beleuchtung - kann AT_Beleuchtung_Wohnen verwenden
            beleuchtung = f"""Schedule:Compact,
    {config.name}_Beleuchtung,   !- Name
    Fraction,                !- Schedule Type Limits Name
    Through: 12/31,          !- Field 1
    For: Weekdays,           !- Field 2
    Until: 6:00,0.1,         !- Field 3
    Until: 8:00,0.8,         !- Field 5
    Until: 17:00,0.1,        !- Field 7
    Until: 22:00,1.0,        !- Field 9
    Until: 24:00,0.2,        !- Field 11
    For: Weekends Holidays,  !- Field 13
    Until: 9:00,0.1,         !- Field 14
    Until: 22:00,0.8,        !- Field 16
    Until: 24:00,0.2;        !- Field 18"""
            
        schedules.append(beleuchtung)
        
        # Geräte - raumtypspezifisch
        if config.room_type == 'kueche':
            geraete = f"""Schedule:Compact,
    {config.name}_Geraete,       !- Name
    Fraction,                !- Schedule Type Limits Name
    Through: 12/31,          !- Field 1
    For: Weekdays,           !- Field 2
    Until: 6:00,0.3,         !- Field 3 (Kühlschrank)
    Until: 8:00,1.0,         !- Field 5 (Frühstück)
    Until: 12:00,0.4,        !- Field 7
    Until: 13:00,0.8,        !- Field 9 (Mittagessen)
    Until: 17:00,0.3,        !- Field 11
    Until: 20:00,1.0,        !- Field 13 (Abendessen)
    Until: 24:00,0.3,        !- Field 15
    For: Weekends Holidays,  !- Field 17
    Until: 9:00,0.3,         !- Field 18
    Until: 10:00,0.8,        !- Field 20
    Until: 13:00,0.4,        !- Field 22
    Until: 14:00,0.8,        !- Field 24
    Until: 19:00,0.3,        !- Field 26
    Until: 20:00,1.0,        !- Field 28
    Until: 24:00,0.3;        !- Field 30"""
        else:
            # Standard Geräte
            geraete = f"""Schedule:Compact,
    {config.name}_Geraete,       !- Name
    Fraction,                !- Schedule Type Limits Name
    Through: 12/31,          !- Field 1
    For: Weekdays,           !- Field 2
    Until: 7:00,0.1,         !- Field 3 (Standby)
    Until: 8:00,0.5,         !- Field 5
    Until: 17:00,0.2,        !- Field 7
    Until: 22:00,0.8,        !- Field 9
    Until: 24:00,0.2,        !- Field 11
    For: Weekends Holidays,  !- Field 13
    Until: 9:00,0.1,         !- Field 14
    Until: 22:00,0.6,        !- Field 16
    Until: 24:00,0.2;        !- Field 18"""
            
        schedules.append(geraete)
        
        return "\n\n".join(schedules)

    def create_building_from_layout(self, layout_config: Dict) -> str:
        """Erstellt ein komplettes Gebäude aus einer Layout-Konfiguration"""
        
        building_idf = """! ========================================================================
! AUTOMATISCH GENERIERTES GEBÄUDE
! ========================================================================

"""
        
        for zone_data in layout_config['zones']:
            zone_config = ZoneConfig(**zone_data)
            zone_idf = self.create_zone_template(zone_config)
            building_idf += zone_idf + "\n\n"
            
        return building_idf

    def save_zone_template(self, zone_config: ZoneConfig, filename: Optional[str] = None):
        """Speichert eine Zone als Template-Datei"""
        
        if not filename:
            filename = f"AT_Zone_{zone_config.name}.idf"
            
        filepath = self.zones_dir / filename
        zone_idf = self.create_zone_template(zone_config)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(zone_idf)
            
        print(f"Zone gespeichert: {filepath}")
        
    def create_sample_building(self):
        """Erstellt ein Beispiel-Einfamilienhaus"""
        
        # Layout-Konfiguration für typisches österreichisches EFH
        layout = {
            'zones': [
                {
                    'name': 'Wohnzimmer',
                    'room_type': 'wohnzimmer',
                    'position': (0, 0, 0),
                    'dimensions': (5.0, 6.0, 2.7)
                },
                {
                    'name': 'Kueche',
                    'room_type': 'kueche', 
                    'position': (0, 7, 0),
                    'dimensions': (4.0, 3.0, 2.7)
                },
                {
                    'name': 'Schlafzimmer',
                    'room_type': 'schlafzimmer',
                    'position': (6, 0, 0),
                    'dimensions': (4.0, 4.0, 2.7)
                },
                {
                    'name': 'Badezimmer',
                    'room_type': 'badezimmer',
                    'position': (4, 7, 0),
                    'dimensions': (2.5, 3.0, 2.7)
                }
            ]
        }
        
        building_idf = self.create_building_from_layout(layout)
        
        # Als Template speichern
        output_file = self.zones_dir / "Salzburg_EFH_Complete.idf"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(building_idf)
            
        print(f"Komplettes Gebäude erstellt: {output_file}")
        return output_file

# CLI Interface für das Zone Building
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="EnergyPlus Zone Builder")
    parser.add_argument('--create-sample', action='store_true', help='Erstelle Beispiel-EFH')
    parser.add_argument('--room-type', type=str, help='Raumtyp (wohnzimmer, kueche, etc.)')
    parser.add_argument('--name', type=str, help='Zonename')
    parser.add_argument('--dimensions', type=str, help='Abmessungen: "width,depth,height"')
    parser.add_argument('--position', type=str, help='Position: "x,y,z"')
    parser.add_argument('--project-path', type=str, default='.', help='Projektpfad')
    
    args = parser.parse_args()
    
    builder = ZoneBuilder(args.project_path)
    
    if args.create_sample:
        output_file = builder.create_sample_building()
        print(f"✅ Beispiel-EFH erstellt: {output_file}")
        print("Nächste Schritte:")
        print("1. Include in dein base_model.idf:")
        print(f"   ##include {output_file}")
        print("2. Simulation starten:")
        print("   python scripts/run_simulation.py")
        
    elif args.room_type and args.name:
        # Einzelne Zone erstellen
        dimensions = None
        if args.dimensions:
            dimensions = tuple(map(float, args.dimensions.split(',')))
            
        position = (0, 0, 0)
        if args.position:
            position = tuple(map(float, args.position.split(',')))
            
        zone_config = ZoneConfig(
            name=args.name,
            room_type=args.room_type,
            dimensions=dimensions,
            position=position
        )
        
        builder.save_zone_template(zone_config)
        print(f"✅ Zone '{args.name}' erstellt")
        
    else:
        print("Verwendung:")
        print("  --create-sample                    # Erstelle komplettes EFH")
        print("  --room-type kueche --name Kueche1  # Erstelle einzelne Zone")
        print("  --dimensions 4,3,2.7 --position 0,7,0  # Mit Abmessungen")

if __name__ == "__main__":
    main()