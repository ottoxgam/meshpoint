# Vendored xterm.js

Pinned, byte-for-byte copies of the xterm.js terminal emulator and its
fit addon. Vendored so the dashboard `/terminal` section keeps working
on Pis with no internet route off the LAN (factory floors, field kits,
mesh-only deployments, RV / boat / cabin installs).

## Files

| File                    | Source                                                                         | Bytes  |
|-------------------------|--------------------------------------------------------------------------------|--------|
| `xterm.js`              | https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.js                          | 283404 |
| `xterm.css`             | https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css                         |   5383 |
| `xterm-addon-fit.js`    | https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.js      |   1503 |

## Versions

- `xterm` 5.3.0
- `xterm-addon-fit` 0.8.0

## Why these exact versions

Tied to whatever was on the jsdelivr CDN when the v0.7.4 terminal
panel landed. Bumping is easy -- replace the file, update this table,
re-run `tests/test_terminal_*` -- but it's a deliberate decision, not
something we want auto-floating.

## License

MIT, owned by the xterm.js authors. See https://github.com/xtermjs/xterm.js
for the full text. Vendored copies retain the upstream sourceMappingURL
comment.

## Refresh procedure

```bash
curl -fsSLo frontend/vendor/xterm/xterm.js              https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.js
curl -fsSLo frontend/vendor/xterm/xterm.css             https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css
curl -fsSLo frontend/vendor/xterm/xterm-addon-fit.js    https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.js
```

Then update the byte counts in the table above.
