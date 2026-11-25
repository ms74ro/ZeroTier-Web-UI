# Changelog

Versioning: `YYYY.MM.DD.counter` (e.g. `2026.11.25.1` = first release of 25 Nov 2026).
The value lives in `VERSION` in `zerotier-web-ui/app.py` and matches the git tag (`v2026.11.25.1`).

## 2026.11.25.1
- First public release.
- Single-container Flask + waitress UI for the local ZeroTier daemon (join / leave / peers).
- Basic Auth via `.htpasswd`, CSRF protection on join/leave.
- 12 languages in `language/*.json` (Romanian default), dark/light theme.
- Version shown discreetly in the page footer.
