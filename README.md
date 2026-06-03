# sprt

Small Python wrapper around `fastchess` for chess-engine SPRT runs.

It keeps full raw fastchess logs on disk while printing concise progress:

```text
[ 842/2000] Elo   5.8 +/-  14.7 | LLR  0.30/2.94 ( 10%) | LOS 78.0% | draw  61.0%
```

## Examples

Test the current build against the stable reference:

```sh
sprt \
  --reference ~/assets/engines/reference \
  --candidate ./build/enyo
```

Compare UCI options only when the engine configuration is part of the test:

```sh
sprt \
    --reference ~/assets/engines/reference \
    --candidate ~/assets/engines/reference \
    --reference-uci "nnue_file=$HOME/code/cpp/chess/enyo/net/default.nn" \
    --candidate-uci "nnue_file=$HOME/code/cpp/chess/nnue/runs/d16-rc2-secondhalf-fresh-huber-sign-lr2e7-e10-20260531/train/model.nn"

```

Test the current build with candidate process args:

```sh
sprt \
  --reference ~/assets/engines/reference \
  --candidate ./build/enyo \
  --candidate-opts "-c ~/.config/settings_nnue2.json"
```

Notes:

- `--candidate` is required.
- Defaults to 2000 games, auto concurrency/Threads, ETA enabled, and the
  reference/WOMP book under `~/assets`.
- Writes `logs/<name>.log` and `logs/<name>.pgn` by default.
- `--candidate-opts` and `--reference-opts` pass process args to engines.
- Process args do not change engine paths; use `--candidate` or `--reference`
  to override a side.
- `--candidate-uci` and `--reference-uci` pass UCI options to engines.
- Prints each engine's startup id or UCI `id name` in the header when available.
- Run `./sprt --help` for the full option list and defaults.
- `--elo0`, `--elo1`, `--alpha`, and `--beta` configure the fastchess SPRT.
- Use `--no-eta` to hide progress ETA.
- `--ntfy-url` sends start/end notifications; default is `SPRT_NTFY_URL` or
  empty.
- Use `--no-ntfy` only for distributed shard runs where an aggregate runner
  sends the final notification.
- `AI_stdout` summaries are not sent by this wrapper; they belong to the agent
  or the higher-level runner interpreting the result.
- Auth is read from `NTFY_AUTH`, `LICHESS_NTFY_AUTH`, or `~/.ntfy`.

Example local notification setup:

```sh
export SPRT_NTFY_URL=https://ntfy.example/sprt
```
