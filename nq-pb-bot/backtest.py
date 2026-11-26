"""Backtest the PB-style NQ model. Usage: python backtest.py [--csv bars.csv] [--rr 1.5] [--bias]"""
import argparse
from dataclasses import replace

import pandas as pd

from pb_nq.model import Params, run
from pb_nq.prop import PropRules, simulate

NY = "America/New_York"


def load(csv=None):
    if csv:
        df = pd.read_csv(csv, parse_dates=[0], index_col=0)
        df.columns = [c.lower() for c in df.columns]
        df.index = pd.to_datetime(df.index, utc=True)
    else:
        import yfinance as yf
        df = yf.download("NQ=F", interval="5m", period="60d", auto_adjust=False, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]
    return df.tz_convert(NY)[["open", "high", "low", "close"]].dropna()


def stats(trades):
    if not trades:
        return {"trades": 0}
    r = pd.Series([t.r for t in trades])
    wins, losses = r[r > 0], r[r <= 0]
    eq = r.cumsum()
    return {
        "trades": len(r),
        "win_rate": round(len(wins) / len(r), 3),
        "avg_R": round(r.mean(), 3),
        "total_R": round(r.sum(), 2),
        "profit_factor": round(wins.sum() / -losses.sum(), 2) if losses.sum() < 0 else float("inf"),
        "max_dd_R": round((eq.cummax() - eq).max(), 2),
        "points": round(sum(t.points for t in trades), 2),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv")
    ap.add_argument("--rr", type=float, default=1.5)
    ap.add_argument("--bias", action="store_true", help="only trade with the 1H EMA bias")
    ap.add_argument("--entry", choices=["edge", "ce"], default="edge")
    args = ap.parse_args()

    df = load(args.csv)
    p = Params(rr=args.rr, require_htf_bias=args.bias, entry_mode=args.entry)
    trades = run(df, p)
    print(f"Data: {df.index[0]} -> {df.index[-1]}  ({len(df)} bars)")
    print("Model:", stats(trades))
    for t in trades:
        print(f"  {t.day} {'LONG ' if t.side > 0 else 'SHORT'} {t.level} "
              f"in {t.entry:.2f} stop {t.stop:.2f} ({t.risk:.0f} pts) out {t.exit:.2f} {t.reason:6} {t.r:+.2f}R")
    for risk in (250, 400):
        print(f"Prop eval (50k, MNQ, ${risk} risk/trade):", simulate(trades, PropRules(risk_per_trade=risk)))

    print("\nSensitivity (not an optimisation; do not pick the best row):")
    for rr in (1.0, 1.5, 2.0):
        for bias in (False, True):
            s = stats(run(df, replace(p, rr=rr, require_htf_bias=bias)))
            print(f"  rr={rr} bias={bias!s:5} {s}")


if __name__ == "__main__":
    main()
