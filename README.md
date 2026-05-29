# sprt

Small Python wrapper around `fastchess` for chess-engine SPRT runs.

It keeps full raw fastchess logs on disk while printing concise progress:

```text
[ 842/2000] Elo   5.8 +/-  14.7 | LLR  0.30/2.94 ( 10%) | LOS 78.0% | draw  61.0%
```

## Common Commands

Run the default local SPRT setup:

```sh
sprt
```

Test the current build against the default reference:

```sh
sprt --candidate ./build/enyo
```

Test the current build with alternate process args:

```sh
sprt --candidate-opts "-c ~/.config/settings_nnue2.json" \
  --candidate ./build/enyo
```

Spell out the stable reference when you want the baseline visible:

```sh
sprt --reference ~/assets/engines/reference \
  --candidate ./build/enyo
```

Notes:

- Requires `fastchess` in `PATH`, `~/local/bin/fastchess`, or `--fastchess`.
- Defaults to 2000 games, host-auto concurrency/Threads, ETA enabled,
  `https://ntfy.wahlman.no/sprt`, and the candidate/reference/WOMP book under
  `~/assets`.
- Writes `logs/<name>.log` and `logs/<name>.pgn` by default.
- `--candidate-opts` and `--reference-opts` pass process args to engines.
- `--candidate-uci` and `--reference-uci` pass UCI options to engines.
- Prints each engine's startup id or UCI `id name` in the header when available.
- Run `./sprt --help` for the full option list and defaults.
- `--elo0`, `--elo1`, `--alpha`, and `--beta` configure the fastchess SPRT.
- Use `--no-eta` to hide progress ETA.
- `--ntfy-url` sends start/end notifications. Auth is read from `NTFY_AUTH`, `LICHESS_NTFY_AUTH`, or `~/.ntfy`.
