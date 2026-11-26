"""PB-style mechanical model on NQ 5m bars: liquidity sweep -> inverted FVG -> retest entry."""
from dataclasses import dataclass

import numpy as np
import pandas as pd

TICK = 0.25


@dataclass(frozen=True)
class Params:
    window_start: str = "09:30"
    window_end: str = "11:00"
    flat_time: str = "15:55"
    reclaim_bars: int = 3
    fvg_max_age: int = 24
    ifvg_max_bars: int = 20
    retest_max_bars: int = 12
    entry_mode: str = "edge"  # "edge" = near edge of the inverted gap, "ce" = its midpoint
    stop_buffer: float = 2.0
    atr_len: int = 14
    min_stop_atr: float = 0.5  # stop distance bounds, in multiples of 5m ATR
    max_stop_atr: float = 3.0
    rr: float = 1.5
    require_htf_bias: bool = False
    htf_ema: int = 50
    max_trades_per_day: int = 1
    slippage: float = TICK


@dataclass
class Trade:
    day: object
    side: int
    level: str
    entry_time: pd.Timestamp
    entry: float
    stop: float
    target: float
    exit_time: pd.Timestamp
    exit: float
    reason: str

    @property
    def risk(self):
        return abs(self.entry - self.stop)

    @property
    def points(self):
        return self.side * (self.exit - self.entry)

    @property
    def r(self):
        return self.points / self.risk


class _Side:
    """Long-only logic. The short side runs the same code on a price-negated view."""

    def __init__(self, sign, o, h, l, c, atr, levels, p):
        self.sign = sign
        if sign == 1:
            self.o, self.h, self.l, self.c = o, h, l, c
        else:
            self.o, self.h, self.l, self.c = -o, -l, -h, -c
        self.levels = {n: sign * v for n, v in levels.items()}
        self.p = p
        self.atr = atr
        self.breach = {}
        self.done = set()
        self.sweep = None
        self.fvgs = []
        self.pending = None

    def add_fvg(self, i):
        if i >= 2 and self.h[i] < self.l[i - 2]:
            self.fvgs.append((self.h[i], self.l[i - 2], i))

    def step(self, i, in_window):
        p = self.p
        if self.sweep and self.l[i] < self.sweep["ext"]:
            self.sweep = None
            self.pending = None

        if in_window:
            for name, lvl in self.levels.items():
                if name in self.done:
                    continue
                b = self.breach.get(name)
                if b is None:
                    if self.l[i] >= lvl:
                        continue
                    b = self.breach[name] = [i, self.l[i]]
                b[1] = min(b[1], self.l[i])
                if self.c[i] > lvl:
                    self.sweep = {"level": name, "ext": b[1], "idx": i, "used": False}
                    self.pending = None
                    self.done.add(name)
                elif i - b[0] + 1 >= p.reclaim_bars:
                    self.done.add(name)

        self.fvgs = [f for f in self.fvgs if i - f[2] <= p.fvg_max_age]
        inverted = [f for f in self.fvgs if f[2] < i and self.c[i] > f[1]]
        self.fvgs = [f for f in self.fvgs if f not in inverted]
        s = self.sweep
        if (in_window and inverted and s and not s["used"] and self.pending is None
                and i - s["idx"] <= p.ifvg_max_bars):
            cands = [f for f in inverted if f[1] > s["ext"]]
            if cands:
                bot, top, _ = max(cands, key=lambda f: f[2])
                entry = top if p.entry_mode == "edge" else (top + bot) / 2
                stop = s["ext"] - p.stop_buffer
                risk = entry - stop
                s["used"] = True
                if p.min_stop_atr * self.atr[i] <= risk <= p.max_stop_atr * self.atr[i]:
                    self.pending = {"entry": entry, "stop": stop, "target": entry + p.rr * risk,
                                    "zone_bot": bot, "created": i, "level": s["level"]}
        self.add_fvg(i)


def run_day(o, h, l, c, atr, times, i0, i_win_end, i_flat, levels_long, levels_short, p, bias=0, day=None):
    sides = [_Side(1, o, h, l, c, atr, levels_long, p), _Side(-1, o, h, l, c, atr, levels_short, p)]
    if p.require_htf_bias:
        sides = [s for s in sides if s.sign == bias]
    for s in sides:
        for j in range(max(2, i0 - p.fvg_max_age), i0):
            s.add_fvg(j)

    trades, pos = [], None

    def close(sd, i, view_price, reason):
        nonlocal pos
        trades.append(Trade(day, sd.sign, pos["level"], pos["time"], sd.sign * pos["entry"],
                            sd.sign * pos["stop"], sd.sign * pos["target"], times[i],
                            sd.sign * view_price, reason))
        pos = None

    for i in range(i0, i_flat + 1):
        in_window = i <= i_win_end
        if pos:
            sd = pos["side"]
            if sd.l[i] <= pos["stop"]:
                close(sd, i, min(pos["stop"], sd.o[i]) - p.slippage, "stop")
            elif sd.h[i] >= pos["target"]:
                close(sd, i, pos["target"], "target")
            elif i == i_flat:
                close(sd, i, sd.c[i] - p.slippage, "time")
        elif len(trades) < p.max_trades_per_day:
            for sd in sides:
                pend = sd.pending
                if not pend or i <= pend["created"]:
                    continue
                if not in_window or i - pend["created"] > p.retest_max_bars:
                    sd.pending = None
                elif sd.l[i] <= pend["entry"]:
                    pos = {"side": sd, "entry": min(pend["entry"], sd.o[i]), "stop": pend["stop"],
                           "target": pend["target"], "level": pend["level"], "time": times[i]}
                    for other in sides:
                        other.pending = None
                    if sd.l[i] <= pos["stop"]:
                        close(sd, i, pos["stop"] - p.slippage, "stop")
                    break
                elif sd.c[i] < pend["zone_bot"]:
                    sd.pending = None
        for sd in sides:
            sd.step(i, in_window)
    return trades


def _hm(s):
    hh, mm = s.split(":")
    return pd.Timedelta(hours=int(hh), minutes=int(mm))


def run(df, p=Params()):
    """df: 5m OHLC with a tz-aware America/New_York index covering the overnight session."""
    df = df.sort_index()
    idx = df.index
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    prev_c = np.roll(c, 1)
    prev_c[0] = c[0]
    tr = np.maximum(h, prev_c) - np.minimum(l, prev_c)
    atr = pd.Series(tr).rolling(p.atr_len, min_periods=1).mean().to_numpy()
    hourly = df["close"].resample("1h", label="right", closed="left").last().dropna()
    bias_series = np.sign(hourly - hourly.ewm(span=p.htf_ema, adjust=False).mean())

    days = sorted(set(idx.normalize()))
    prev_rth, trades = None, []
    for d in days:
        open_t = d + _hm(p.window_start)
        rth = (idx >= d + _hm("09:30")) & (idx < d + _hm("16:00"))
        if rth.sum() < 60:
            continue
        on = (idx >= d - pd.Timedelta(hours=6)) & (idx < d + _hm("09:30"))
        if prev_rth is not None and on.sum() >= 30:
            onh, onl = h[on].max(), l[on].min()
            pdh, pdl = h[prev_rth].max(), l[prev_rth].min()
            long_lv, short_lv = {"ONL": onl}, {"ONH": onh}
            if pdl < onl:
                long_lv["PDL"] = pdl
            if pdh > onh:
                short_lv["PDH"] = pdh
            i0 = idx.searchsorted(open_t)
            i_win_end = idx.searchsorted(d + _hm(p.window_end)) - 1
            i_flat = idx.searchsorted(d + _hm(p.flat_time)) - 1
            b = bias_series[bias_series.index <= open_t]
            bias = int(b.iloc[-1]) if len(b) else 0
            trades += run_day(o, h, l, c, atr, idx, i0, i_win_end, i_flat, long_lv, short_lv, p, bias, d.date())
        prev_rth = rth
    return trades
