# Turnbuckle Brawl

A 3D pro-wrestling brawler (three.js) packaged as a Windows desktop app (Electron), with local 2-player, online play with a friend (PeerJS, with voice chat), bosses, weapons, knockdowns and a signature special for every fighter.

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
