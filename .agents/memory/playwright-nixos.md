---
name: Playwright on NixOS/Replit
description: System dependencies required for Playwright Chromium in the Replit NixOS environment.
---

# Playwright on NixOS/Replit

After installing `playwright` and running `python -m playwright install chromium`, launching Chromium in Replit (NixOS) fails with missing shared libraries.

## Required Nix system dependencies

Install these via `installSystemDependencies`:

- `nspr` — libnspr4.so
- `nss` — libnss3.so
- `xorg.libxcb` — libxcb.so
- `xorg.libX11`, `xorg.libXcomposite`, `xorg.libXdamage`, `xorg.libXext`, `xorg.libXfixes`, `xorg.libXrandr`, `xorg.libXrender`, `xorg.libXtst`
- `libxkbcommon`
- `libdrm`
- `mesa`
- `libgbm` — libgbm.so.1 (separate from `mesa` in current nixpkgs)
- `alsa-lib`
- `cups`, `dbus`, `expat`, `cairo`, `pango`, `atk`, `gdk-pixbuf`, `gtk3`

## Why

Playwright downloads its own browser binaries, but those binaries are dynamically linked against the host system's shared libraries. NixOS does not keep libraries in standard FHS paths, so the package manager must make them available in the Replit environment.

## How to apply

If Chromium fails to launch with a missing `.so`, add the corresponding Nix package to the project dependencies. After adding, restart the workflow and test with a minimal headless page load.
