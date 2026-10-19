# Proxies — leichte Stellvertreter für schwere Objekte in IngeTrazo

![Proxies](screenshot.webp)

Schwere Objekte (importierte Bäume, Möbel, Autos) durch leichte Proxy-Meshes ersetzen; die volle Geometrie liegt als .igz auf der Platte. Das Dokument wird klein und der Viewport schnell; vor einem Rendering oder Export kommen die Originale mit einem Klick zurück. Der Ablauf folgt Q-Proxies für 3ds Max.

## Installation
`proxy_tool.py` aus dem [neuesten Release](../../releases/latest) laden, in den Plugin-Ordner kopieren (Extensions ▸ Open plugins folder; unter Windows `%APPDATA%\ingetrazo\plugins`) und IngeTrazo neu starten. Benötigt IngeTrazo ≥ 0.5.7 · getestet mit IngeTrazo 0.5.8.

Zu finden unter **Extensions ▸ Proxies**, im Rechtsklick-Menü und in der Werkzeugleiste «Proxies» (4 Icons).

## Befehle
- **Create Proxies…** — gewählte Gruppen oder Komponenten in Proxies umwandeln.
- **Show Originals** — volle Geometrie zurückholen (gewählte Proxies, oder alle, wenn nichts gewählt ist). Vor Render with Blender oder einem Export benutzen.
- **Show Proxies** — zurück zu den Proxies. Wurde ein Original inzwischen bearbeitet, wird seine .igz neu geschrieben.
- **Select All Proxies** — alle Proxies im Dokument auswählen.

Name, Lage, Layer, Material der Gruppe und Instanzen bleiben erhalten; Kopien einer Komponente teilen sich einen Proxy, so wie sie sich eine Definition teilen. Ein Proxy, dessen Original gerade angezeigt wird, lässt sich mit anderem Typ oder anderen Werten wieder zum Proxy machen. Jeder Befehl ist ein Undo-Schritt.

## Create Proxies…
| Feld | Bedeutung |
|---|---|
| Only objects with more than … faces | Filter: kleine Objekte bleiben unverändert |
| Proxy mesh | **Box** (Bounding Box in den eigenen Achsen) · **Convex hull** · **Vertex cloud** · **From source** (Original reduziert) |
| Hull points | Extrempunkte der konvexen Hülle |
| Points / Max points | Anteil der Vertices als kleine Kreuze |
| Keep faces / Keep materials | Reduktion des Originals (Vertex-Clustering), Materialien übernehmen |
| Colour / See-through | Proxy-Farbe, durchscheinend mit 35 % |
| Save originals | **Individually** (je Objekt eine .igz) · **All together** (proxies.igz) · **By layer** (je Layer eine .igz) |
| Folder | Standard: `<Dokument>_proxies` neben der .igz |

**Preview** (wie in allen PESI3D-Plugins): grün «● Live Preview ON» zeigt die Proxies echt im Modell und folgt jeder Änderung; **OK** übernimmt die Vorschau, **Cancel** nimmt sie zurück, **Reset** stellt die Standardwerte her. Der Dialog ist nicht-modal — Orbit, Pan und Zoom gehen weiter.

Jede Original-.igz lässt sich in IngeTrazo normal öffnen. Ihr Pfad wird relativ zum Dokument gespeichert, der Projektordner kann also als Ganzes verschoben werden.

## Änderungen
- **1.0** — erste Veröffentlichung: Create Proxies… (Box, konvexe Hülle, Punktwolke, aus dem Original), Originale als .igz, Show Originals / Show Proxies, ein Proxy je Komponente, Live-Vorschau, eigene Werkzeugleiste. Getestet mit IngeTrazo 0.5.8.

## Hinweis
Nicht verbunden mit Spline Dynamics oder Autodesk; «Q-Proxies» und «3ds Max» dienen nur zur Beschreibung des Ablaufs.

Lizenz GPL-3.0-or-later · Pesi, [pesi3d.de](https://pesi3d.de) — English: [README.md](README.md)
