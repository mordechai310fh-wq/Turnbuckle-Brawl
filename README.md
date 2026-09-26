# Turnbuckle Brawl

A 3D pro-wrestling brawler (three.js) packaged as a Windows desktop app (Electron), with local 2-player, online play with a friend (PeerJS, with voice chat), bosses, weapons, knockdowns and a signature special for every fighter.

## What's new in 2.0

- **Combat:** dodge roll (Left Shift / M / LB) with a slow-mo *perfect dodge*, counter hits (+35%), combos that scale damage, a haymaker on every third chained punch, and *rage* below 25% health (+20% damage).
- **Three new finishers:** Meteor Elbow, Spin Cyclone and Thunder Clap.
- **Shop and progression:** earn coins from every match (itemised on the results card, with an S–D grade). Spend them on 1-player upgrades, finishers you can equip in any mode, impact-spark and entrance-pyro cosmetics, and one-match boosts. Twelve trophies pay out coins, plus a daily bonus.
- **Animation:** spring-driven poses with follow-through, hit-stop, squash on impact, motion smears on fists and feet, leaning into movement, heavy breathing when hurt, three victory celebrations.
- **Effects:** GPU particles (sparks, embers, fire, fireworks, confetti), manga impact bursts and shockwaves, lightning, gold "finisher ready" and red rage auras, colour fringing and zoom on big hits, vignette and film grain.
- **Presentation:** broadcast-style intro with camera cuts and name plates, redesigned HUD (portraits, segmented health, damage trail, combo counter, floating damage numbers), toasts, animated menus, synthesized arena music that builds with the crowd, and music/effects volume settings.

Upgrades and boosts only apply in 1-player matches, so online and couch matches stay even. The profile (coins, unlocks, trophies) is saved in the app's local storage under `tb-profile`.

## Layout

| Path | What it is |
|---|---|
| `src/game.html` | The whole game: rendering, fighters, specials, online, UI. **Edit this.** |
| `main.js` | Electron window (icon, fullscreen on F11, mic permission for voice chat). |
| `tools/roster.json` | Model fighters: names, stats, look, cape, guard, `special`, credits. |
| `models/*.glb` | Rigged fighter models and the arena. |
| `tools/*.py` | Blender scripts that clean and auto-rig downloaded models (`convert.py`). |
| `scripts/prepare.js` | Builds `app/` from `src/game.html` + models, using local copies of the libraries. |
| `scripts/pack.js` | Packages the game next to the untouched official Electron runtime and zips it. |
| `build/` | App icon and the installer's extra NSIS steps. |

## Build

```bash
npm install
npm start            # run from source (after npm run prepare-app)
npm run pack         # dist/Turnbuckle Brawl/ + dist/TurnbuckleBrawl-v<version>-Windows.zip
npm run installer    # dist/installer/TurnbuckleBrawl-v<version>-Setup.exe
```

Bump `version` in `package.json` for each release; it is shown on the title screen and names the zip and installer. Both online players need the same version.

The game exe is the official Electron binary, renamed and never edited: Windows Smart App Control blocks an edited copy. That is why the icon is set on the window, the shortcuts and the installer instead of on the exe.

## Model credits

3D models from Sketchfab, used for this private, non-commercial fan game:

- **The Boxer** — "BOXER LIGHT 2" by PONCHIK
- **Spider-Man (Fortnite)** — "Spiderman Brand New Day from Fortnite" by jimmyho905
- **Spider-Man** — "The Amazing Spider-Man 2 Spider-Man" by fredbear1211
- **Goldberg** — "WWE_GOLDBERG_2K22" by RadioactiveAG
- **Messi** — "Lionel Messi of the Argentina" by 3dUVpro
- **Scooby-Doo** — "Fortnite - Scooby Doo" by 雨宮レン (oscar3dmodel)
- **Dingel** — "Dingel - Freebie" by Valentin Winkelmann
- **Sub-Zero** — "Sub-Zero (Mortal Kombat Armageddon)" by linkuei
- **Luffy** — "Monkey D Luffy - Wano Kimono - One Piece" by MakeEz
- **Omni-Man** — "Omni-Man (Fortnite)" by rocklee.ff123
- **Pennywise** — "Pennywise animated low poly" by vicente betoret ferrero
- **Gojo** — "Gojo jujutsu kaisen" by Jujutsu_kaisen
