
# 🏗️ EnergyPlus VS Code Projektstruktur

Dieses Projekt bietet eine strukturierte Arbeitsumgebung für die Simulation mit **EnergyPlus** in Verbindung mit **Visual Studio Code** und **Python (pyenergyplus API)**.

---

## 📁 Projektstruktur

```
energyplus-project/
│
├── idf/                  # Enthält die .idf-Dateien (Gebäudemodelle)
│   │── base_model.idf
│   │── base_model_with_zone.idf
│   └── base_model_lahof.idf
│
├── weather/              # Wetterdaten (.epw) für die Simulation
│   └── AUT_SZ_Salzburg.AP.111500_TMYx.2009-2023.epw
│
├── output/               # Ergebnisse und Logs nach der Simulation
│
├── scripts/              # Python-Skripte zur Steuerung von EnergyPlus
│   │── run_simulation.py
│   └── resource_manager.py
│
├── resources/            # Eigene Bibliotheken: Materialien, Konstruktionen etc.
│   │── hvac
│   │── internal_loads
│   │   └──LAHOF_Internal_loads.idf
│   │── materials
│   │   └──LAHOF_Konstruktionen.idf
│   │── schedules
│   │   └──LAHOF_Schedules.idf
│   └── zones
│       └──LAHOF_H4_Kinderwagenraum.idf
│
└── README.md             # Diese Dokumentation
```

---

## 🧰 Vorbereitung

1. Stelle sicher, dass **Python 3.8+** installiert ist.
2. Installiere das benötigte Python-Paket:

```bash
pip install -r requirements.txt
```

3. Stelle sicher, dass **EnergyPlus installiert** ist (am besten Version 9.6 oder höher).
   - Prüfe, ob `energyplus` über die Kommandozeile aufrufbar ist (`energyplus -v`).
   - Optional: Setze den Pfad zu `energyplus.exe` in die Umgebungsvariable.

---

## 🚀 Simulation starten

### Option 1: Direkt über Python (empfohlen)
```bash
python scripts/run_simulation.py
```

### Option 2: Innerhalb von VS Code
- Öffne das Projekt mit VS Code
- Drücke `Strg+Shift+B`, um die Simulation über `tasks.json` zu starten

Die Ausgabe erscheint im Ordner `output/`.

---

## 🔁 Eingabedateien anpassen

- **idf/base_model.idf**: Hier definierst du dein Gebäude (Zonen, Bauteile, Systeme etc.)
- **weather/AUT_Vienna.epw**: Wetterdaten für die Standort-Simulation
- **resources/my_library.idf**: Optional: eigene Materialien oder Konstruktionen, die du in die IDF einfügen kannst

---

## 💡 Tipps

- Nutze Git für Versionskontrolle (z. B. für verschiedene Modellvarianten)
- Du kannst weitere Skripte z. B. zur Auswertung oder Batch-Simulation im Ordner `scripts/` anlegen
- Ausgabeparameter kannst du über `Output:Variable`-Objekte in der IDF-Datei konfigurieren

---

## 👨‍💻 Weiterführende Nutzung

- Integration in Co-Simulationsframeworks wie **mosaik**, **FMI**, etc.
- Automatisierte Simulation mit verschiedenen Wetterdaten
- Post-Processing mit Pandas oder matplotlib in Python

---

## 📬 Fragen oder Probleme?
Wenn du diese Struktur weitergeben willst, lässt sie sich auch als GitHub-Projekt aufsetzen.  
Für Rückfragen oder Erweiterungen kann die Dokumentation erweitert werden.

Viel Erfolg bei der Simulation!
