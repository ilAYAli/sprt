# sprt

Small Python wrapper around `fastchess` for chess-engine SPRT runs.

It keeps full raw fastchess logs on disk while printing concise progress:

```text
[ 842/2000] Elo   5.8 +/-  14.7 | LLR  0.30/2.94 ( 10%) | LOS 78.0% | draw  61.0%
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
- ETA is shown automatically when it fits. Use `--eta` or `--no-eta` to force it.
- `--ntfy-url` sends start/end notifications. Auth is read from `NTFY_AUTH`, `LICHESS_NTFY_AUTH`, or `~/.ntfy`.
