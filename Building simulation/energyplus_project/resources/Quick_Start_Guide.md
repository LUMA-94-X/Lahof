# 🚀 Quick Start Guide - Österreichische EnergyPlus Resources

## ⚡ 5-Minuten Setup

### Schritt 1: Ordnerstruktur anlegen
```bash
# Im Lahof-Projektordner
mkdir -p resources/{materials,hvac,schedules,templates}
mkdir -p projects/salzburg-efh
mkdir -p weather
mkdir -p scripts
```

### Schritt 2: Resources speichern
```bash
# Die erstellten Bibliotheken speichern
cp AT_Baumaterialien.idf resources/materials/
cp AT_HVAC_Templates.idf resources/hvac/
cp automation_script.py scripts/resource_manager.py
```

### Schritt 3: Erstes Projekt erstellen
```bash
# Salzburg EFH Template kopieren
cp salzburg_efh_template.idf projects/salzburg-efh/
cd projects/salzburg-efh
```

### Schritt 4: Simulation starten
```bash
# Mit deiner Salzburg Wetterdatei
energyplus -w ../../weather/AUT_SZ_Salzburg.epw -d output salzburg_efh_template.idf
```

---

## 🎯 Konkrete Anwendungsfälle

### Use Case 1: Schnelle Gebäudebewertung
```python
# Python Script für U-Wert Berechnung
from scripts.resource_manager import ResourceManager

rm = ResourceManager()

# U-Werte aller Konstruktionen berechnen
for name in rm.constructions:
    u_value = rm.calculate_u_value(name)
    print(f"{name}: {u_value:.3f} W/m²K")
```

### Use Case 2: Österreich-Standard Validation
```bash
# Alle Resources gegen OIB-Richtlinien prüfen
python scripts/resource_manager.py --validate

# Excel-Report generieren
python scripts/resource_manager.py --export-excel "OIB_Compliance_Report.xlsx"
```

### Use Case 3: Parameterstudie Dämmdicken
```python
# Verschiedene Dämmdicken testen
scenarios = {
    "Standard_16cm": {"dämmung_dicke": 0.16},
    "Verstärkt_20cm": {"dämmung_dicke": 0.20},
    "Passivhaus_24cm": {"dämmung_dicke": 0.24}
}

results = rm.batch_simulation(scenarios)
```

---

## 📊 Sofort verfügbare Konstruktionen

### ✅ Außenwände (sofort verwendbar)
- **`AT_Außenwand_WDVS_Standard`** - U: ~0.28 W/m²K
- **`AT_Außenwand_2schalig`** - U: ~0.32 W/m²K  
- **`AT_Außenwand_Passivhaus`** - U: ~0.14 W/m²K
- **`AT_Außenwand_Holzbau`** - U: ~0.25 W/m²K

### ✅ Dächer (sofort verwendbar)
- **`AT_Steildach_Standard`** - U: ~0.18 W/m²K
- **`AT_Flachdach_Warmdach`** - U: ~0.15 W/m²K
- **`AT_Dach_Passivhaus`** - U: ~0.09 W/m²K

### ✅ Fenster (sofort verwendbar)
- **`AT_Fenster_3fach_Standard`** - U: 0.8 W/m²K
- **`AT_Fenster_Passivhaus`** - U: 0.6 W/m²K

### ✅ HVAC-Systeme (sofort verwendbar)
- **`AT_LWWP_Heizung`** - Luft-Wasser Wärmepumpe
- **`AT_KWL_Wärmetauscher`** - 85% Wärmerückgewinnung
- **`AT_Fußbodenheizung`** - 35°C Vorlauftemperatur

---

## 🔧 Anpassung für deine Projekte

### Projekt-spezifische Materialien hinzufügen
```energyplus
! In deiner Projekt-IDF ergänzen:
##include resources/materials/AT_Baumaterialien.idf

! Dann eigene Anpassungen:
Material,
    Mein_Sonder_Ziegel,          !- Name
    MediumRough,                 !- Roughness
    0.30,                        !- Thickness {m} (angepasst)
    0.40,                        !- Conductivity {W/m-K}
    1700,                        !- Density {kg/m3}
    1000;                        !- Specific Heat {J/kg-K}

Construction,
    Meine_Spezial_Wand,          !- Name
    AT_Kalkzementputz_2cm,       !- Layer 1 (aus Bibliothek)
    Mein_Sonder_Ziegel,          !- Layer 2 (projektspezifisch)
    AT_EPS_WDVS_16cm;            !- Layer 3 (aus Bibliothek)
```

### Regionale Wetterdaten einbinden
```energyplus
! Für verschiedene österreichische Standorte:
! Wien: AUT_VI_Vienna.epw
! Salzburg: AUT_SZ_Salzburg.epw  
! Innsbruck: AUT_TI_Innsbruck.epw
! Graz: AUT_ST_Graz.epw

Site:Location,
    Salzburg_Custom,             !- Name
    47.80,                       !- Latitude
    13.00,                       !- Longitude
    1.0,                         !- Time Zone
    430.0;                       !- Elevation {m}
```

---

## ⚡ Power-User Tipps

### 1. Automatische U-Wert Berechnung
```python
# Alle deine Konstruktionen checken
import pandas as pd

def audit_building(idf_file):
    constructions = parse_constructions(idf_file)
    
    report = []
    for name, layers in constructions.items():
        u_value = calculate_u_value_from_layers(layers)
        oib_ok = u_value <= get_oib_limit(categorize(name))
        
        report.append({
            'Konstruktion': name,
            'U-Wert': u_value,
            'OIB-konform': oib_ok,
            'Empfehlung': get_improvement_tip(name, u_value)
        })
    
    return pd.DataFrame(report)
```

### 2. Batch-Optimierung für verschiedene Standards
```bash
# Verschiedene österreichische Standards testen
python scripts/resource_manager.py --batch-optimize \
  --standards "OIB,Passivhaus,ÖGNB" \
  --building-type "EFH" \
  --location "Salzburg"
```

### 3. Lebenszykluskosten Integration
```python
def lifecycle_assessment(construction_name):
    # Material costs (€/m²)
    material_costs = calculate_material_costs(construction_name)
    
    # Energy savings over 50 years
    u_value = rm.calculate_u_value(construction_name)
    annual_savings = (0.35 - u_value) * 20 * 2000 * 0.12  # kWh * €/kWh
    
    # NPV calculation
    npv = -material_costs + sum([annual_savings * (1.03**-year) for year in range(50)])
    
    return {
        'initial_cost': material_costs,
        'annual_savings': annual_savings,
        'npv_50_years': npv
    }
```

---

## 🎯 Konkrete nächste Schritte für dich:

### Heute (30 Minuten):
1. **Ordner anlegen** und Dateien kopieren
2. **Salzburg Template** mit deinen Gebäudedaten füllen
3. **Erste Simulation** starten

### Diese Woche:
4. **Python Script** anpassen für deine Bedürfnisse
5. **Excel-Reports** für Projektdokumentation
6. **Git Repository** für Versionskontrolle

### Langfristig:
7. **Eigene Materialien** aus Herstellerdaten ergänzen
8. **Parameterstudien** für Optimierung
9. **Lebenszykluskosten** Integration
10. **Team-Bibliothek** aufbauen

---

## 📞 Support & Hilfe

### Bei Problemen:
- **Logfiles** checken: `resources_management.log`
- **U-Werte** validieren mit Online-Rechnern
- **EnergyPlus Fehler** in `.err` Files analysieren

### Erweitern:
- **Neue Materialien:** Namenskonvention `AT_Material_Dicke`
- **Dokumentation:** Immer mit Quelle/Standard kommentieren
- **Testing:** U-Werte mit Referenzwerten abgleichen

### Community:
- **IBPSA Austria** - Österreichische Simulationsgemeinschaft
- **EnergyPlus Helpdesk** - Internationale Unterstützung
- **Lehrstuhl Bauphysik** - Universitäre Expertise

---

## 🎉 Du bist bereit!

Mit dieser Bibliothek hast du:
- ✅ **50+ österreichische Baumaterialien** sofort verfügbar
- ✅ **20+ validierte Konstruktionen** nach OIB-Standards  
- ✅ **HVAC-Templates** für typische österreichische Haustechnik
- ✅ **Automatisierung** für Qualitätssicherung
- ✅ **Salzburg-spezifisches Template** als Startpunkt

**Starte jetzt deine erste Simulation und optimiere österreichische Gebäude professionell!** 🏠⚡

---

*Viel Erfolg mit deinen EnergyPlus Simulationen! Bei Fragen stehe ich gerne zur Verfügung.*