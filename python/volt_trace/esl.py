"""
esl.py - Einlesen und Parsen von ESL-XML-Dateien (ESLBillingData).

Zweck und Aufgaben dieser Datei:
--------------------------------
1. Einlesen von ESL-XML-Dateien mit absoluten Zählerständen.
2. Extrahieren der relevanten XML-Knoten und Attribute:
   - <TimePeriod end="YYYY-MM-DDTHH:MM:SS">: Stichtag / Endzeitpunkt der Messperiode in UTC.
   - <ValueRow obis="..." value="..." status="..."/>: Auslesen der Werte nach OBIS-Kennzahlen.
3. OBIS-Code-Zuordnung und Summierung:
   - ID742 (Netzbezug Strom):
     * "1-1:1.8.1" (Bezug Hochtarif) + "1-1:1.8.2" (Bezug Niedertarif)
     * Summe = absoluter Zählerstand für Netzbezug (ID742)
   - ID735 (Einspeisung Solaranlage ins Netz):
     * "1-1:2.8.1" (Einspeisung Hochtarif) + "1-1:2.8.2" (Einspeisung Niedertarif)
     * Summe = absoluter Zählerstand für Einspeisung (ID735)
4. Bereitstellung der Referenz-Zählerstände:
   - Dient als Referenz- bzw. Nullpunkt-Zählerstand, um aus relativen sdat-Verbrauchswerten
     absolute Zählerstände über die Zeit berechnen zu können.
"""
