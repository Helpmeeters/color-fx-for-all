# Contributing to Helpmeet: Color FX for All

Thanks for helping. Bug reports, new sequences, wording fixes, and pull requests are all welcome.

## Reporting bugs

Open an [issue](https://github.com/Helpmeeters/color-fx-for-all/issues/new/choose) using the bug report form. The most useful things to include are:

- Your Home Assistant version, and whether it's a beta.
- The integration and model of the lights involved, and whether the hub targets a light group.
- The attributes of the hub's `switch.color_fx_…` entity, from **Developer tools > States**.
- For Media Art, the media player integration and the app that was playing.
- The debug log lines for the problem (see **Debug Logging** in the [README](README.md#-debug-logging)).

## Development setup

You need Python 3.14 and [uv](https://docs.astral.sh/uv/). A devcontainer is also included.

```bash
uv venv -p 3.14
uv pip install pytest-homeassistant-custom-component
.venv/bin/python -m pytest -q
```

The tests set up real hubs in a test Home Assistant instance, with fake lights and media players. They check which lights receive which colors, what gets restored on stop, and how Media Art follows artwork.

## Pull requests

- Keep changes focused. One fix or feature per pull request.
- Add or update tests for any behavior change, and make sure `pytest` passes.
- Run `ruff check` and `ruff format` (settings are in `pyproject.toml`).
- If you change `strings.json`, copy the same change into `translations/en.json`.
- User-facing text calls each configured instance a **Hub**, matching Home Assistant's **Add Hub** button.
- For changes to the animation or restore behavior, try them on real lights too. Bulbs differ in how they handle transitions.
- CI runs the tests against Home Assistant stable and beta, plus ruff, hassfest, and the HACS validation action. All of them need to pass.

By contributing, you agree that your contributions are licensed under the [MIT License](LICENSE).
