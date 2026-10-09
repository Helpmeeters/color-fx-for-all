# Security policy

## Supported versions

Only the latest release receives fixes.

## Reporting a vulnerability

Please don't open a public issue. Report it privately through GitHub's [private vulnerability reporting](https://github.com/Helpmeeters/color-fx-for-all/security/advisories/new) instead.

Include what you found, how to reproduce it, and what an attacker could do with it. You should get a reply within a week.

## What's in scope

Color FX for All runs inside Home Assistant with its full permissions. Issues that are especially relevant:

- A Hub controlling a light it wasn't configured for, beyond the members of a configured light group.
- The dashboard card, which is served without authentication at `/color_fx/color-fx-card.js` and loaded on every dashboard, exposing anything beyond its own static code.
- Media Art fetching or decoding artwork in a way that a crafted image or media player could abuse. Artwork is fetched through Home Assistant's media player entity, never from a URL directly, and decoded with Pillow.
