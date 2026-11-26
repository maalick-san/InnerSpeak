"""Prop-evaluation rules: position sizing and a pass/fail simulation over a trade list."""
from dataclasses import dataclass
from math import floor


@dataclass(frozen=True)
class PropRules:
    start_balance: float = 50_000
    profit_target: float = 3_000
    max_drawdown: float = 2_000  # trailing, measured on end-of-day balance, locks at start balance
    daily_loss_limit: float | None = 1_000
    risk_per_trade: float = 250
    point_value: float = 2.0  # MNQ = $2/pt, NQ = $20/pt
    max_contracts: int = 50
    commission_rt: float = 1.24  # per contract, round trip


def contracts(risk_pts, rules):
    return min(rules.max_contracts, floor(rules.risk_per_trade / (risk_pts * rules.point_value)))


def simulate(trades, rules=PropRules()):
    bal = peak = rules.start_balance
    status, taken, skipped, day, day_pnl = "open", 0, 0, None, 0.0
    for t in trades:
        if t.day != day:
            peak = max(peak, bal)
            day, day_pnl = t.day, 0.0
        if rules.daily_loss_limit and day_pnl <= -rules.daily_loss_limit:
            continue
        n = contracts(t.risk, rules)
        if n < 1:
            skipped += 1
            continue
        pnl = n * (t.points * rules.point_value - rules.commission_rt)
        bal += pnl
        day_pnl += pnl
        taken += 1
        if bal <= min(peak - rules.max_drawdown, rules.start_balance):
            status = "failed"
            break
        if bal >= rules.start_balance + rules.profit_target:
            status = "passed"
            break
    return {"status": status, "balance": round(bal, 2), "trades_taken": taken,
            "skipped_stop_too_wide": skipped, "last_day": day}
