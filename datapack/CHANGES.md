# Änderungen gegenüber Matcha

Jede Matcha-Entscheidung, die wir ändern, steht hier mit Grund. Betroffene
Dateien liegen in `overrides/`, eigene Inhalte in `additions/`.

Format: **Was** · Dateien · Warum

## Mobs

**Zombie-Geschwindigkeit gesenkt** · `data/matcha/function/mechanics/spawn_mechanic/{normal,hard}_modifications/modify_zombie.mcfunction`
· Matcha setzt Normal 0.34 und Hard 0.38 (Vanilla 0.23). Das ist für ein gemütliches Pack zu hektisch, Zombies holen Spieler zu leicht ein. Neu: Normal 0.27, Hard 0.30. Easy hat bei Matcha keine Zombie-Anpassung und bleibt Vanilla. Leben, Schaden, Sprung- und Stufenhöhe bleiben wie bei Matcha.
