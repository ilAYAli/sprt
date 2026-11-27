#!/usr/bin/env python3
"""Resume tests for the sprt wrapper, using a fake fastchess."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

SPRT = Path(__file__).resolve().parents[1] / "sprt"

FAKE_FASTCHESS = textwrap.dedent('''\
    #!/usr/bin/env python3
    import os, sys
    args = sys.argv[1:]
    rounds = int(args[args.index("-rounds") + 1])
    start = next(int(a.split("=", 1)[1]) for a in args if a.startswith("start="))
    with open(os.environ["FAKE_CALLS"], "a") as calls:
        calls.write(f"start={start} rounds={rounds}\\n")
    each = args.index("-each") + 1
    with open(os.environ["FAKE_CALLS"] + ".each", "a") as limits:
        limits.write(" ".join(args[each:args.index("-config")]) + "\\n")
    die_after = int(os.environ.get("FAKE_DIE_AFTER", "0"))
    # Pair p (1-based) yields candidate 1-0 as white and 1/2 as black.
    w = d = l = 0
    for game in range(1, 2 * rounds + 1):
        if die_after and game > die_after:
            os.kill(os.getpid(), 9)
        white = "candidate" if game % 2 else "reference"
        black = "reference" if game % 2 else "candidate"
        result = "1-0" if game % 2 else "1/2-1/2"
        if game % 2:
            w += 1
        else:
            d += 1
        print(f"Finished game {game} ({white} vs {black}): {result} {{x}}", flush=True)
        if game % 2 == 0:
            print(f"Score of candidate vs reference: {w} - {l} - {d}  [0.750] {w + d + l}", flush=True)
            print("Elo difference: 190.85 +/- 50.00, LOS: 99.00 %, DrawRatio: 50.00 %", flush=True)
            print(f"SPRT: llr {0.1 * (game // 2):.2f} (5.0%), lbound -2.94, ubound 2.94", flush=True)
''')

FAKE_ENGINE = "#!/bin/sh\nwhile read l; do [ \"$l\" = uci ] && echo 'id name Fake 1' && echo uciok; [ \"$l\" = quit ] && exit 0; done\n"


class ResumeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name, body in (("fastchess", FAKE_FASTCHESS), ("engine", FAKE_ENGINE)):
            path = self.root / name
            path.write_text(body)
            path.chmod(0o755)
        (self.root / "book.epd").write_text("x\n")
        self.calls = self.root / "calls.txt"

    def run_sprt(self, games: int, *, die_after: int = 0, extra: list[str] | None = None) -> subprocess.CompletedProcess[str]:
        env = {**os.environ, "FAKE_CALLS": str(self.calls), "FAKE_DIE_AFTER": str(die_after)}
        return subprocess.run(
            [
                sys.executable, str(SPRT),
                "--candidate", str(self.root / "engine"),
                "--reference", str(self.root / "engine"),
                "--book", str(self.root / "book.epd"),
                "--fastchess", str(self.root / "fastchess"),
                "--games", str(games), "--book-offset", "100",
                "--concurrency", "1", "--threads", "1",
                "--log-dir", str(self.root / "logs"), "--name", "shard",
                "--no-ntfy", "--no-eta", *(extra or []),
            ],
            capture_output=True, text=True, env=env, cwd=self.root,
        )

    @property
    def state(self) -> Path:
        return self.root / "logs" / "shard.resume.json"

    def last_progress(self, stdout: str) -> str:
        return [line for line in stdout.splitlines() if line.startswith("[")][-1]

    def test_completed_shard_removes_state(self) -> None:
        result = self.run_sprt(8)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertFalse(self.state.exists())
        self.assertIn("WDL 4/4/0", self.last_progress(result.stdout))

    def test_killed_shard_resumes_remaining_pairs(self) -> None:
        killed = self.run_sprt(10, die_after=7)  # 3 complete pairs, game 7 lost
        self.assertNotEqual(0, killed.returncode)
        saved = json.loads(self.state.read_text())
        self.assertEqual(3, saved["segments"][0]["pairs"])

        resumed = self.run_sprt(10)
        self.assertEqual(0, resumed.returncode, resumed.stderr)
        self.assertEqual(
            ["start=101 rounds=5", "start=104 rounds=2"],
            self.calls.read_text().split("\n")[:2],
        )
        line = self.last_progress(resumed.stdout)
        self.assertIn("[10/10]", line)
        self.assertIn("WDL 5/5/0", line)
        self.assertIn("Ptnml 0-0-0-5-0", line)
        # LLR = 0.30 from the killed segment + 0.20 from the resumed one.
        self.assertRegex(line, r"LLR\s+0\.50/2\.94")
        self.assertIn("resume: 6 games already played", resumed.stdout)
        self.assertFalse(self.state.exists())

    def test_changed_settings_start_over(self) -> None:
        self.run_sprt(10, die_after=5)
        self.assertTrue(self.state.exists())
        result = self.run_sprt(10, extra=["--tc", "5+0.05"])
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("start=101 rounds=5", self.calls.read_text().split("\n")[1])

    def each_limits(self) -> list[str]:
        return Path(str(self.calls) + ".each").read_text().splitlines()

    def test_clock_is_default_limit(self) -> None:
        result = self.run_sprt(2, extra=["--tc", "5+0.05"])
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(["tc=5+0.05"], self.each_limits())

    def test_fixed_depth_and_nodes_replace_clock(self) -> None:
        result = self.run_sprt(2, extra=["--depth", "8"])
        self.assertEqual(0, result.returncode, result.stderr)
        result = self.run_sprt(2, extra=["--nodes", "5000", "--tc", "5+0.05"])
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(["depth=8", "nodes=5000"], self.each_limits())

    def test_changed_depth_starts_over(self) -> None:
        self.run_sprt(10, die_after=5, extra=["--depth", "8"])
        self.assertTrue(self.state.exists())
        result = self.run_sprt(10, extra=["--depth", "9"])
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("start=101 rounds=5", self.calls.read_text().split("\n")[1])

    def test_no_resume_discards_state(self) -> None:
        self.run_sprt(10, die_after=5)
        result = self.run_sprt(10, extra=["--no-resume"])
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("start=101 rounds=5", self.calls.read_text().split("\n")[1])
        self.assertFalse(self.state.exists())

    def test_fully_played_state_reports_and_cleans_up(self) -> None:
        # Killed after the last pair was saved but before sprt exited.
        self.run_sprt(6, die_after=5)
        saved = json.loads(self.state.read_text())
        saved["params"]["games"] = 4
        saved["segments"][0].update(pairs=2, wins=2, draws=2, losses=0, pentanomial=[0, 0, 0, 2, 0])
        self.state.write_text(json.dumps(saved))
        self.calls.unlink()
        result = self.run_sprt(4)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("[4/4]", self.last_progress(result.stdout))
        self.assertFalse(self.calls.exists())
        self.assertFalse(self.state.exists())


class PairingTests(unittest.TestCase):
    """Games finish out of order with concurrency > 1."""

    def formatter(self):
        import importlib.machinery, importlib.util
        loader = importlib.machinery.SourceFileLoader("sprt_script", str(SPRT))
        spec = importlib.util.spec_from_loader("sprt_script", loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        return module.ProgressFormatter(8, False)

    def finish(self, fmt, game, result):
        white, black = ("candidate", "reference") if game % 2 else ("reference", "candidate")
        fmt.format(f"Finished game {game} ({white} vs {black}): {result} {{x}}\n")

    def test_out_of_order_games_pair_by_number(self) -> None:
        fmt = self.formatter()
        # Pair 1 = games 1,2; pair 2 = games 3,4.  Candidate wins both games of
        # pair 2 and draws both of pair 1; they arrive interleaved.
        self.finish(fmt, 4, "0-1")
        self.finish(fmt, 3, "1-0")
        self.assertEqual(0, fmt.pairs)  # pair 2 is past the unfinished pair 1
        self.finish(fmt, 1, "1/2-1/2")
        self.finish(fmt, 2, "1/2-1/2")
        self.assertEqual(2, fmt.pairs)
        self.assertEqual([0, 0, 1, 0, 1], fmt.pentanomial)
        self.assertEqual([2, 2, 0], fmt.wdl)

    def test_trim_pgn_drops_games_past_saved_pairs(self) -> None:
        import importlib.machinery, importlib.util
        loader = importlib.machinery.SourceFileLoader("sprt_script", str(SPRT))
        spec = importlib.util.spec_from_loader("sprt_script", loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        game = lambda rnd, res: f'[Event "x"]\n[Round "{rnd}"]\n\n1. e4 {res}\n\n'
        with tempfile.TemporaryDirectory() as tmp:
            pgn = Path(tmp) / "kt.pgn"
            first = game(1, "1-0") + game(1, "0-1")  # earlier segment, kept as is
            pgn.write_text(first + game(2, "1-0") + game(1, "1-0") + game(3, "1/2-1/2") + game(1, "0-1"))
            state = module.ResumeState(Path(tmp) / "s.json", {})
            state.segments = [{"pairs": 1}, {"pairs": 1, "pgn_start": len(first)}]
            module.trim_pgn(pgn, state)
            self.assertEqual(first + game(1, "1-0") + game(1, "0-1"), pgn.read_text())


if __name__ == "__main__":
    unittest.main()
