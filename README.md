# Matcha Mountain

Die Idee: Möglichst viel Gameplay steckt in einem **eigenen Datapack**, nicht in Mods. Grundlage ist ein Fork von [Matcha Flavoured](https://modrinth.com/datapack/matcha-flavoured) (Klei_Wright), an dem wir Matchas Entscheidungen nach eigenem Geschmack ändern. Mods gibt es nur dort, wo ein Datapack an seine Grenzen stößt, vor allem neue Blöcke und Pflanzen, außerdem für Performance und Client-Komfort.

## Grundlage

| | |
|---|---|
| Minecraft | 26.3 |
| Loader | Fabric (Testinstanz „26.3“ in Prism: Fabric Loader 0.20.1) |
| Basis-Datapack | Matcha Flavoured 1.12.9 „Poplar Release“ (31.10.2026), Datapack und Ressourcenpack |
| Weltgenerierung | Vanilla und unser Matcha-Fork, **keine** Weltgenerierungs-Mods |

## Was Matcha mitbringt

Matcha baut Minecraft für langsamere, weniger technische Spieler um: keine Mob-, XP- oder Villager-Farmen nötig.

- **Kein Hunger:** `natural_health_regeneration false`. Essen heilt über Regeneration, die Lore zeigt Herzen statt Hungerkeulen.
- **Gerichte:** Rund 50 eigene Gerichte, gekocht über eigene Rezeptarten („oven“, „kiln“) sowie Lagerfeuer und Werkbank.
- **Gamerules:**
  - `keep_inventory true`
  - `players_sleeping_percentage 200`, die Nacht lässt sich also nicht überspringen
  - `spawn_phantoms false`
- **Progression:** Neue Legierungen, Rüstungen und Werkzeuge. Das frühe Spiel ist schwerer, Verzauberungen und Dorfhandel sind überarbeitet.
- **Mobs:** Sie werden beim Spawnen per Funktion angepasst, je nach Matcha-Schwierigkeit (z. B. Zombie-Geschwindigkeit 0.34 statt Vanilla 0.23).
- **Fischen:** Neues Fischen mit Angler's Almanac, gesteuert über Biom-Tags (`freshwater_*`, `saltwater_*`).
- **Weltgenerierung:**
  - Eigene Dörfer (`village_beta`): ohne Dorfbewohner, sehr selten (spacing 80/50 statt 34/8)
  - Neue Abbey-Struktur
  - Tiefes Smaragderz
  - Geänderte Spawns und Farben in 67 Vanilla-Biomen
- **Technik:** Eigene Items sind Vanilla-Items mit Komponenten (`item_model`, `item_name`, `consumable`, `use_remainder`, `lore`). Modelle und Texturen liefert das Ressourcenpack. Matcha färbt auch Vanilla-Pflanzen um, z. B. wird Rote Bete zur Tomate.

## Der Fork

Matcha bekommt alle paar Tage ein Update, deshalb ändern wir die Kopie nicht direkt. Upstream bleibt unangetastet, unsere Änderungen liegen getrennt daneben:

```
pack.json                      Versionen (Pack, Minecraft, Matcha) und Testinstanz
datapack/
  upstream/matcha-<version>/   Matcha-Datapack und -Ressourcenpack, unverändert entpackt
  overrides/                   nur die Matcha- und Vanilla-Dateien, die wir ersetzen
    pack.mcmeta                optional: Filter ergänzen ("filter.block") oder aufheben ("matchamountain:unblock")
    removals.txt               optional: Upstream-Dateien, die entfallen (ein Glob pro Zeile)
  overrides.lock.json          Upstream-Stand jeder überschriebenen Datei beim letzten Prüfen
  additions/                   eigener Namespace "matchamountain" (data/ und assets/)
  CHANGES.md                   welche Matcha-Entscheidung wir warum ändern
tools/build_datapack.py
```

So arbeitet `build_datapack.py`:
- Es legt die drei Ebenen übereinander.
- Es führt die `filter`-Blöcke aus den `pack.mcmeta`-Dateien zusammen. Matcha blendet damit rund 800 Vanilla-Dateien aus.
- Es baut **eine Jar mit Daten und Assets**, wie Matchas eigene Mod-Jar (`build/matcha-mountain-<version>.jar`, Mod-ID `matchamountain`, ersetzt `mr_matcha_flavoured`). Die liefert packwiz an Clients und Server aus, ohne Datapack-Ordner in der Welt.
- Bei einem Upstream-Update meldet es jede Datei, die wir überschreiben und die Matcha inzwischen selbst geändert hat.

```
python3 tools/build_datapack.py build [--install] [--strict]   # Jar bauen, optional in die Prism-Testinstanz kopieren
python3 tools/build_datapack.py check                          # überschriebene Dateien gegen Upstream prüfen
python3 tools/build_datapack.py accept [pfad ...]              # geprüften Upstream-Stand festhalten
```

**Neue Override-Datei:** Datei aus `upstream/…/datapack/` bzw. `…/resourcepack/` unter demselben Pfad nach `overrides/` kopieren, ändern, `accept <pfad>` ausführen und in `CHANGES.md` eintragen.

**Matcha-Update:** `fetch <neue-version>`, `matcha_version` in `pack.json` umstellen, `check`. Jede gemeldete Datei mit der neuen Upstream-Fassung abgleichen, dann `accept`. Den alten Upstream-Ordner löschen.

Matchas Namespaces bleiben (`matcha`, `matcha_item`, `main`, `endless_repairs`, `debug`, `custom_music`). Matcha besteht aus fast 6.000 Dateien, die sich gegenseitig referenzieren; Umbenennen bringt nur Arbeit.

## Geplante Änderungen an Matcha

### Mobs
- **Zombie-Geschwindigkeit** runter. Betroffen sind `data/matcha/function/mechanics/spawn_mechanic/{easy,normal,hard}_modifications/modify_zombie.mcfunction`. Der Zielwert ist noch offen.
- Die übrigen Mob-Anpassungen durchsehen.

## Keep Inventory Überarbeitung
- Spieler behält Werkzeuge, Waffen und Rüstungen
- Verliert jedoch jegliche Baublöcke, ggf gibt es ein kleines Icon welches den Hinweis gibt was gespeichert wird

### Dörfer werden zu Ruinen
Matchas `village_beta` ist schon jetzt unbewohnt (keine Dorfbewohner, Betten oder Golems, Truhen nur in zwei Bauteilen).

- **Verfall per Processor-List:** Eine eigene Liste `matchamountain:ruin` ersetzt `minecraft:empty` in `worldgen/template_pool/village_beta/*`. Sie macht Folgendes:
  - `block_rot` entfernt einen Teil der Wände und Dächer, das Fundament bleibt.
  - Regeln ersetzen Blöcke: Bruchstein und Steinziegel werden bemoost oder rissig, ein Teil der Bretter fällt weg, Glas, Türen und Fackeln verschwinden.
  - Spinnweben kommen dazu (Matchas `cobwebs`-Liste) und verdächtiger Kies mit eigener Archäologie-Beute.
- **Halb versunken:** `terrain_adaptation: "bury"` statt `beard_box`. Die Wege werden zu Kies und grober Erde.
- **Eigene Beute** für die Ruinen-Truhen.
- **Biome über Tags** statt fester Biomlisten. Abstand und Häufigkeit legen wir selbst fest.

## Eigene Inhalte im Datapack

**Neue Gerichte:**
- Vorlage sind die Gerichte der Farming-Mods aus Proud Mountain:
  - Farmer's Delight
  - Let's Do Farm & Charm, Bakery, Candlelight
  - Vegan Delight
  - Coffee Delight
- Daraus kommen rund 120 Gerichte infrage.
- Sie werden nach Matchas Muster gebaut: Heilung über Regeneration, Buffs als Effekte, Herzen in der Lore. 

**Aus Proud Mountain übernehmen (Kandidaten):**

| Inhalt | Umsetzung |
|---|---|
| Elytra-Sperre | Loot-Tables und Struktur-NBT des End-Schiffs |
| Spielerfarben | Scoreboard-Teams |
| End-Sperre | Tick-Funktion mit Storage-Flag |
| Testwelt | Eigene flache Dimension, `/trigger` mit Macro-Funktionen |
| Chat-Formate | `chat_type` |

## Eigene Mods

Was ein Datapack nicht kann, kommt in eigene Fabric-Mods:
- Farbige Spielernamen werden überarbeitet. Spieler haben einfach nur eine farbige Raute vor dem Namen.
- **Koch-Mod:** Kochen soll ein Prozess bleiben, nicht nur Werkbank-Rezepte. Dazu gehören:
  - Kochstationen wie Kochtopf, Herd und Schneidebrett
  - Neue Pflanzen mit wilden Vorkommen: Zwiebel, Reis, Kohl, Salat, Mais, Hafer, Erdbeere, Kaffee, Soja
  - Die Ergebnisse folgen Matchas Herzen-System, nicht dem Hunger-System.
- **Tweaks-Mod:** Was es serverseitig weiter braucht, z. B.:
  - Einladungen mit Bürgschaft (`/invite`, `/punish`, ändert die Whitelist)
  - Standard-Ressourcenpacks beim ersten Start einschalten
  - Jahreszeiten nach echtem Kalender

## Mods

Keine Weltgenerierungs-Mods: BOP, Tectonic, Natural Temperature sowie Struktur-Mods wie Moog's, Repurposed Structures und Dungeons & Taverns passen nicht zum Matcha-Gefühl.

**Durch Matcha überflüssig:**

| Mod | Grund |
|---|---|
| AppleSkin | Es gibt keinen Hunger mehr |
| GraveStone | `keep_inventory` ist an |
| Better Days | Matcha hat eine eigene Tag-Timeline |

**Kandidaten (alle für Fabric 26.3 verfügbar, Stand 04.11.2026):**

| Bereich | Mods |
|---|---|
| Performance | Sodium, Lithium, FerriteCore, ImmediatelyFast, Entity Culling |
| Grafik | Iris mit Complementary Reimagined, Continuity, LambDynamicLights, EMF/ETF mit Fresh Animations, Distant Horizons |
| Komfort | JEI, Jade, Inventory Profiles Next, Mouse Tweaks, FallingTree |
| Server | Chunky, spark, Ledger (statt CoreProtect), AntiXray, Simple Voice Chat |

Außerdem AmbientSounds, Sound Physics Remastered, Fallingleaves, ShulkerBoxTooltip, Countered's Terrain Slabs und ReplayMod.

## Auslieferung

Wie bei Proud Mountain: packwiz, Prism-Instanz und Docker-Server (itzg/minecraft-server mit `PACKWIZ_URL`). Dafür git@github.com:Stolzenberg/minecraft-modpack-matcha-mountain.git.

## Lizenz und Credits

Matcha Flavoured von Klei_Wright steht unter [CC-BY-NC-SA-4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). Für unseren Fork heißt das:
- Matcha als Grundlage nennen
- keine kommerzielle Nutzung
- unter derselben Lizenz weitergeben
