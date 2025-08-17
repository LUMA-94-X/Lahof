# 🏗️ Schrittweise Zonen zu EnergyPlus hinzufügen

## 📋 Überblick der Methoden

Du hast **3 Hauptoptionen** für das Hinzufügen von Zonen:

### Option 1: 🎯 **Template-System** (Empfohlen)
- Wiederverwendbare Zone-Templates
- Österreichische Standards eingebaut
- Modulare Struktur

### Option 2: 🤖 **Automatischer Generator** 
- Python-Script erstellt Zonen automatisch
- Konfiguration über JSON/Parameter
- Schnell für komplette Gebäude

### Option 3: ✏️ **Manuelle Erstellung**
- Direkt in IDF-Dateien arbeiten
- Maximale Kontrolle
- Gut zum Lernen/Verstehen

---

## 🚀 **OPTION 1: Template-System (START HIER)**

### Schritt 1: Ordnerstruktur erweitern
```bash
cd "Building simulation/energyplus_project"

# Neue Ordner anlegen
mkdir -p resources/zones
mkdir -p resources/schedules
mkdir -p projects/mein_efh
```

### Schritt 2: Zone-Templates speichern
```bash
# AT_Zones_Templates.idf aus dem Chat speichern
# In: resources/zones/AT_Zones_Templates.idf
```

### Schritt 3: Base Model erweitern
Dein `idf/base_model.idf` ergänzen:

```energyplus
!-   ===========  Used Resources ===========
! Materialien
##include resources/materials/AT_Baumaterialien.idf

! Zonen (HIER NEU!)
##include resources/zones/AT_Zones_Templates.idf

! Optional: HVAC & Schedules
##include resources/hvac/AT_HVAC_Templates.idf
##include resources/schedules/AT_Schedules.idf
```

### Schritt 4: Erste Simulation starten
```bash
python scripts/run_simulation.py
```

**✅ Ergebnis:** 4-Zonen Einfamilienhaus mit österreichischen Standards

---

## 🔧 **OPTION 2: Automatischer Generator**

### Schritt 1: Zone Builder installieren
```bash
# zone_builder.py aus dem Chat speichern
# In: scripts/zone_builder.py

# Ausführbar machen
chmod +x scripts/zone_builder.py
```

### Schritt 2: Beispiel-Gebäude generieren
```bash
cd "Building simulation/energyplus_project"

# Komplettes EFH erstellen
python scripts/zone_builder.py --create-sample

# Ergebnis: resources/zones/Salzburg_EFH_Complete.idf
```

### Schritt 3: Eigene Zonen erstellen
```bash
# Einzelne Küche erstellen
python scripts/zone_builder.py \
  --room-type kueche \
  --name "KuecheEG" \
  --dimensions "4.5,3.2,2.7" \
  --position "0,8,0"

# Büro erstellen  
python scripts/zone_builder.py \
  --room-type buero \
  --name "HomeOffice" \
  --dimensions "3.5,4.0,2.7" \
  --position "10,0,0"
```

### Schritt 4: In Base Model einbinden
```energyplus
! In deinem base_model.idf
##include resources/zones/Salzburg_EFH_Complete.idf
##include resources/zones/AT_Zone_HomeOffice.idf
```

---

## ⚡ **QUICK START (5 Minuten)**

### Für Einsteiger:
```bash
# 1. Zone Builder kopieren
cp zone_builder.py scripts/

# 2. Beispiel erstellen
python scripts/zone_builder.py --create-sample

# 3. In base_model.idf einbinden
echo "##include resources/zones/Salzburg_EFH_Complete.idf" >> idf/base_model.idf

# 4. Simulation starten
python scripts/run_simulation.py
```

**🎉 Du hast jetzt ein funktionsfähiges 4-Zonen Einfamilienhaus!**

---

## 🏗️ **Schrittweise Erweiterung**

### Schritt 1: Mit 1 Zone beginnen
```bash
# Nur Wohnzimmer
python scripts/zone_builder.py \
  --room-type wohnzimmer \
  --name "Wohnzimmer" \
  --dimensions "5,6,2.7" \
  --position "0,0,0"
```

### Schritt 2: Zweite Zone hinzufügen
```bash
# Küche daneben
python scripts/zone_builder.py \
  --room-type kueche \
  --name "Kueche" \
  --dimensions "4,3,2.7" \
  --position "0,7,0"
```

### Schritt 3: Zonen verbinden
In den generierten IDFs die Wandverbindungen anpassen:
```energyplus
! In Wohnzimmer: Nordwand zu Küche
BuildingSurface:Detailed,
    AT_Zone_Wohnzimmer_Wand_Nord,
    Wall,
    AT_Innenwand_Ziegel_14cm,    !- Innenwand statt Außenwand
    AT_Zone_Wohnzimmer,
    Surface,                     !- Surface statt Outdoors
    AT_Zone_Kueche_Wand_Sued,    !- Verbindung zur Küche
    NoSun,                       !- NoSun statt SunExposed
    NoWind;                      !- NoWind statt WindExposed
```

### Schritt 4: Nach und nach erweitern
- Schlafzimmer → Badezimmer → Büro → Keller → Obergeschoss

---

## 📐 **Koordinaten-System verstehen**

### Österreichisches Standard-Layout:
```
Nord (Y-Achse +)
↑
│
│  [Küche]    [Bad]
│  4x3m       2.5x3m
│
│  [Wohnzimmer]  [Schlafzimmer]
│  5x6m          4x4m
│
└──────────────────────→ Ost (X-Achse +)
   Süd (Y=0)
```

### Koordinaten-Beispiele:
```python
# Erdgeschoss Layout
zones = {
    'Wohnzimmer':   (0,   0, 0),  # Süd-West Ecke
    'Schlafzimmer': (6,   0, 0),  # Süd-Ost Ecke  
    'Küche':        (0,   7, 0),  # Nord-West Ecke
    'Badezimmer':   (4,   7, 0),  # Nord-Mitte
    
    # Obergeschoss (Z=3.0m)
    'SZ_Eltern':    (0,   0, 3.0),
    'SZ_Kind1':     (5,   0, 3.0),
    'SZ_Kind2':     (0,   5, 3.0),
    'Bad_OG':       (5,   5, 3.0)
}
```

---

## 🔍 **Häufige Anpassungen**

### 1. **Größen ändern**
```python
# In zone_builder.py oder direkt in IDF
dimensions = (4.5, 3.2, 2.7)  # Breiter x Tiefer x Höher
```

### 2. **Fenster anpassen**
```python
windows = [
    {'wall': 'sued', 'width': 3.0, 'height': 1.4, 'sill_height': 0.9},
    {'wall': 'ost',  'width': 1.0, 'height': 1.2, 'sill_height': 1.0}
]
```

### 3. **Konstruktionen tauschen**
```energyplus
! Statt Standard-Außenwand
AT_Außenwand_WDVS_Standard

! Passivhaus-Wand verwenden  
AT_Außenwand_Passivhaus
```

### 4. **Heizungs-Solltemperaturen**
```energyplus
! Verschiedene Temperaturen pro Raum
ThermostatSetpoint:DualSetpoint,
    SZ_Setpoint,
    AT_Heizung_Schlafbereich,    ! 18°C statt 21°C
    AT_Kühlung_Zeitplan;

ThermostatSetpoint:DualSetpoint,
    BAD_Setpoint,  
    BAD_Heizung_Zeitplan,        ! 22°C für Badezimmer
    AT_Kühlung_Zeitplan;
```

---

## 🎯 **Praktische Workflows**

### Workflow A: **Neubau-Planung**
```bash
# 1. Grundriss-Skizze erstellen
# 2. Koordinaten festlegen
# 3. Zonen mit zone_builder.py generieren
# 4. In base_model.idf zusammenführen
# 5. Erste Simulation → Ergebnisse prüfen
# 6. U-Werte optimieren (resources/materials/)
# 7. HVAC-System ergänzen (resources/hvac/)
```

### Workflow B: **Bestandsanalyse**
```bash
# 1. Bestehende Abmessungen vermessen
# 2. Zonen für Ist-Zustand erstellen
# 3. Simulation → Baseline etablieren
# 4. Sanierungsoptionen erstellen:
#    - AT_Außenwand_WDVS_Standard → AT_Außenwand_Passivhaus
#    - AT_Fenster_3fach_Standard → AT_Fenster_Passivhaus
# 5. Vergleich Vorher/Nachher
```

### Workflow C: **Parameterstudie**
```bash
# 1. Base-Modell erstellen
# 2. Python-Script für Varianten:
for dämmdicke in [16, 20, 24]:
    for fenster_typ in ['standard', 'passivhaus']:
        create_variant(dämmdicke, fenster_typ)
        run_simulation()
        collect_results()
# 3. Optimale Konfiguration auswählen
```

---

## ⚠️ **Häufige Fehler vermeiden**

### 1. **Koordinaten-Überschneidungen**
```python
# FALSCH: Zonen überlappen
zone1 = (0, 0, 0)  # 5x6m
zone2 = (3, 0, 0)  # 4x4m → Überschneidung!

# RICHTIG: Abstand lassen
zone1 = (0, 0, 0)  # 5x6m  
zone2 = (6, 0, 0)  # 4x4m → Beginnt bei X=6m
```

### 2. **Wandverbindungen vergessen**
```energyplus
! Innenwände brauchen Surface-zu-Surface Verbindungen
Outside Boundary Condition, Surface,
Outside Boundary Condition Object, AT_Zone_Nachbar_Wand_Gegenrichtung,
```

### 3. **Vertex-Reihenfolge**
```energyplus
! EnergyPlus braucht Counter-Clockwise Reihenfolge
! Von außen betrachtet gegen Uhrzeigersinn
```

### 4. **Fehlende Schedules**
```energyplus
! Jede Zone braucht:
! - Thermostat-Schedule
! - People-Schedule  
! - Lighting-Schedule
! - Equipment-Schedule
```

---

## 📊 **Erfolgskontrolle**

### Nach jeder Zone-Ergänzung prüfen:
```bash
# 1. IDF-Syntax prüfen
energyplus --version

# 2. Simulation starten
python scripts/run_simulation.py

# 3. Logs prüfen  
tail output/eplusout.err

# 4. Ergebnisse validieren
ls output/eplusout.csv  # Daten vorhanden?
ls output/eplustbl.htm  # HTML-Report vorhanden?
```

### Erwartete Ausgaben:
- ✅ **eplusout.csv**: Stündliche Daten für alle Zonen
- ✅ **eplustbl.htm**: Summary-Report mit U-Werten
- ✅ **eplusout.err**: Keine SEVERE Errors, nur Warnings ok

---

## 🎓 **Nächste Schritte**

### Sobald deine Zonen funktionieren:

1. **HVAC-System hinzufügen**
   ```bash
   ##include resources/hvac/AT_HVAC_Templates.idf
   ```

2. **Detaillierte Schedules**
   ```bash  
   ##include resources/schedules/AT_Schedules.idf
   ```

3. **Automatisierung mit Python**
   ```bash
   python scripts/resource_manager.py --validate
   python scripts/resource_manager.py --export-excel
   ```

4. **Optimierung**
   - U-Werte mit Material-Bibliothek optimieren
   - Lebenszykluskosten-Analyse
   - Parameterstudien für verschiedene Standards

---

## 💡 **Pro-Tipps**

### Tipp 1: **Iterative Entwicklung**
- ✅ Beginne mit 1 Zone
- ✅ Teste, simuliere, verstehe
- ✅ Dann erweitern

### Tipp 2: **Template wiederverwenden**
```bash
# Einmal erstellt, für alle Projekte nutzbar
cp resources/zones/AT_Zones_Templates.idf ../projekt2/resources/zones/
```

### Tipp 3: **Git für Versionskontrolle**
```bash
git add resources/zones/
git commit -m "Neue Zone: Büro mit Südverglasung"
```

### Tipp 4: **Dokumentation**
```energyplus
! Immer kommentieren was geändert wurde
! Zone erstellt: 2025-08-12, ML
! Grund: Erweitert um Home-Office
! Besonderheiten: Extra Verglasung Süd
```

---

## 🆘 **Hilfe & Support**

### Bei Problemen:
1. **Logs checken**: `output/eplusout.err`
2. **Validierung**: `python scripts/resource_manager.py --validate`
3. **Community**: EnergyPlus Helpdesk, IBPSA Austria
4. **Dokumentation**: EnergyPlus Engineering Reference

### Typische Lösungen:
- **Severe Error**: Koordinaten/Vertex-Reihenfolge prüfen
- **Warning**: Oft ok, aber Surface-Verbindungen checken  
- **No Output**: Schedule-Namen und Zone-Namen abgleichen

---

**🎉 Viel Erfolg beim schrittweisen Aufbau deiner EnergyPlus-Gebäude!**

*Mit diesem System kannst du von einfachen Ein-Zonen-Tests bis zu komplexen Mehrfamilienhäusern alles erstellen.*