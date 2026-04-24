# Player Dealership + Loaner System for CareerMP

**Subtitle:** A modular multiplayer career expansion for CareerMP, with a player-run vehicle marketplace, timed temporary keys, and optional party tools.

This repository contains a standalone server-side and client-side add-on for `CareerMP` servers in BeamNG.drive.

It was built to extend online career gameplay with the features players usually want most:

- a real player dealership
- player-to-player vehicle sales
- timed temporary keys
- return and revoke controls for loaned vehicles
- party creation and party invites
- party-only shared vehicle visibility
- a dedicated in-game UI app with separate `Party`, `Dealership`, and `Loaners` tabs

The current implementation is designed to work as a modular layer on top of `CareerMP`, especially for servers using `RLS + CareerMP`, while staying isolated from the main compatibility patch.

## What The Mod Does

### Dealership / Marketplace

- lets players list vehicles from their own inventory
- creates a server-wide marketplace for other players to browse
- handles buyer/seller handshake flow for player-to-player vehicle sales
- removes listings when they are delisted, sold, or invalidated
- prevents conflicting states such as listing a vehicle that is already temporarily loaned out

### Temporary Keys / Loaners

- lets a player lend one of their vehicles to another online player for a limited time
- supports manual `Revoke` by the owner
- supports manual `Return` by the borrower
- automatically expires the temporary key when the timer runs out
- reconciles borrowed vehicles on rejoin so temporary loan access survives reconnects cleanly
- removes temporary access automatically if the vehicle is sold

### Party Tools

- create a party
- invite players
- accept invites
- leave or disband the party
- view party members and their online state
- share vehicles with the party in a separate party-only visibility layer

### UI App

The mod ships with a dedicated in-game UI app:

- `Party` tab for members, invites, and party-shared vehicles
- `Dealership` tab for inventory management, listings, and marketplace browsing
- `Loaners` tab for timed temporary key grants and borrowed vehicle tracking

### Optional RLS Phone Integration

RLS uses its own Vue phone bundle instead of the standard BeamNG UI app layout system, so the phone shortcut is generated as a local overlay instead of committing redistributed RLS files to this repository.

The overlay adds a `Player Dealer` tile to the RLS phone. Selecting it closes the phone and opens this mod's existing UI directly on the `Dealership` tab.

Build the overlay from your local RLS compatible zip:

```powershell
python .\scripts\build_rls_phone_overlay.py --rls-compatible-zip "C:\Path\To\rls_career_overhaul_2.6.5.1_careermp_compatible.zip" --out-dir .\dist
```

If `python` does not work on your system:

```powershell
py .\scripts\build_rls_phone_overlay.py --rls-compatible-zip "C:\Path\To\rls_career_overhaul_2.6.5.1_careermp_compatible.zip" --out-dir .\dist
```

Install the generated overlay on the BeamMP server:

```text
Resources/Client/zz_CareerMPPartySharedVehiclesRLSPhoneOverlay.zip
```

## Current Scope

This is a working beta focused on the systems below:

- player dealership listings
- player marketplace browsing
- timed loaner access
- party state and invites
- party shared vehicle registry
- server-side JSON persistence

## Repository Layout

- `ClientSource/`
  Client Lua, UI app, mod metadata, and mod scripts
- `Resources/Server/CareerMPPartySharedVehicles/`
  BeamMP server Lua and JSON persistence folder
- `build_client_zip.py`
  Builds the distributable client zip from `ClientSource`

## Build The Client Zip

From the repository root:

```powershell
python .\build_client_zip.py
```

If your system uses the Python launcher:

```powershell
py .\build_client_zip.py
```

The generated client archive will be created in:

```text
dist/CareerMPPartySharedVehicles.zip
```

## Recent Fixes

- fixed RLS transferred vehicles importing with missing insurance data
- fixed transferred vehicles showing `Value: 0`, `Insurance: n/a`, and `Not insured`
- fixed the repair screen Lua crash caused by missing RLS insurance inventory records
- added automatic repair for already affected transferred vehicles when the world loads
- stopped injecting the UI app into FRE/freeroam/mission layouts that could block RLSMP event staging text
- added cleanup for older layout injections from earlier builds
- added the optional RLS phone overlay builder

## Install

### Client

Build the zip and place it in your BeamMP server client mods folder:

```text
Resources/Client/CareerMPPartySharedVehicles.zip
```

### Server

Copy the server Lua folder into:

```text
Resources/Server/CareerMPPartySharedVehicles/
```

## Notes

- this project is intentionally kept separate from the main `RLS + CareerMP` compatibility patch
- dealership and loaner features are the primary focus
- party tools are kept as a supporting trust/social layer rather than the main feature

## Credits

- the in-game UI visual direction for this project was inspired by the `Banking UI App` mod by `@deadendreece`
- this project builds its own dealership, loaner, and party workflow on top of `CareerMP`, while openly crediting that UI inspiration

## Status

**Beta**

The architecture, UI structure, and main gameplay systems are implemented. As with any multiplayer economy feature, the most important long-session validation is still multi-player live testing.
