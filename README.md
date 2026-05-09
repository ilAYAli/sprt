# sprt

Small Python wrapper around `fastchess` for chess-engine SPRT runs.

It keeps full raw fastchess logs on disk while printing concise progress:

```text
[312/2000] DrawRatio: 64.42 %, Elo difference: -18.95 +/- 23.00, LOS: 5.26 %, LLR: -0.95
```

Example:

```sh
./sprt \
  --candidate ./build/enyo \
  --reference ../assets/engines/reference \
  --book ../assets/books/UHO_Lichess_4852_v1.epd \
  --games 2000 \
  --concurrency 8 \
  --threads 4
```

Notes:

- Requires `fastchess` in `PATH`, `~/local/bin/fastchess`, or `--fastchess`.
- Writes `logs/<name>.log` and `logs/<name>.pgn` by default.
- `--ntfy-url` sends start/end notifications. Auth is read from `NTFY_AUTH`, `LICHESS_NTFY_AUTH`, or `~/.ntfy`.
