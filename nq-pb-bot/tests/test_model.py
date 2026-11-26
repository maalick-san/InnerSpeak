import numpy as np
import pandas as pd

from pb_nq.model import Params, Trade, run_day
from pb_nq.prop import PropRules, contracts, simulate


def _bars(rows):
    a = np.array(rows, float)
    times = pd.date_range("2026-01-05 09:30", periods=len(a), freq="5min", tz="America/New_York")
    return a[:, 0], a[:, 1], a[:, 2], a[:, 3], times


LONG_SETUP = [
    # o, h, l, c
    (110, 111, 109, 110),
    (110, 110.5, 106, 106.5),
    (106, 106.5, 103, 103.5),   # bearish FVG: high 106.5 < low 109 of bar 0 -> zone 106.5..109
    (103.5, 106.2, 98, 101),     # sweeps level 100 and closes back above
    (101, 110, 100.5, 109.5),   # displacement closes above 109 -> gap inverted
    (109.5, 111, 108.5, 110.5), # retest of 109 fills the long
    (110.5, 135, 110, 134),     # target
    (134, 135, 133, 134),
]


def test_long_sweep_ifvg_retest_hits_target():
    o, h, l, c, t = _bars(LONG_SETUP)
    p = Params(min_stop_atr=1, max_stop_atr=100, rr=1.5, stop_buffer=1)
    trades = run_day(o, h, l, c, np.ones(len(o)), t, 0, 7, 7, {"ONL": 100}, {}, p)
    assert len(trades) == 1
    tr = trades[0]
    assert (tr.side, tr.entry, tr.stop, tr.reason) == (1, 109, 97, "target")
    assert tr.target == 109 + 1.5 * 12
    assert abs(tr.r - 1.5) < 1e-9


def test_short_is_mirror_of_long():
    o, h, l, c, t = _bars([(-r[0], -r[2], -r[1], -r[3]) for r in LONG_SETUP])
    p = Params(min_stop_atr=1, max_stop_atr=100, rr=1.5, stop_buffer=1)
    trades = run_day(o, h, l, c, np.ones(len(o)), t, 0, 7, 7, {}, {"ONH": -100}, p)
    assert len(trades) == 1 and trades[0].side == -1
    assert trades[0].entry == -109 and trades[0].stop == -97 and trades[0].reason == "target"


def test_no_trade_without_sweep():
    o, h, l, c, t = _bars(LONG_SETUP)
    p = Params(min_stop_atr=1, max_stop_atr=100)
    assert run_day(o, h, l, c, np.ones(len(o)), t, 0, 7, 7, {"ONL": 90}, {}, p) == []


def test_stop_out_is_minus_one_r_plus_slippage():
    rows = LONG_SETUP[:6] + [(110.5, 111, 96, 96.5)]
    o, h, l, c, t = _bars(rows)
    p = Params(min_stop_atr=1, max_stop_atr=100, stop_buffer=1)
    tr = run_day(o, h, l, c, np.ones(len(o)), t, 0, 6, 6, {"ONL": 100}, {}, p)[0]
    assert tr.reason == "stop" and tr.exit == 97 - 0.25


def _trade(day, pts, risk=20):
    return Trade(day, 1, "ONL", None, 100, 100 - risk, 0, None, 100 + pts, "x")


def test_prop_sizing_and_outcomes():
    rules = PropRules()
    assert contracts(20, rules) == 6
    win = simulate([_trade(i, 30) for i in range(20)], rules)
    assert win["status"] == "passed"
    lose = simulate([_trade(i, -20.25) for i in range(20)], rules)
    assert lose["status"] == "failed" and lose["trades_taken"] == 8
