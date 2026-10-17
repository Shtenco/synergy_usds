from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, List

BPS = 10_000

@dataclass
class CPMM:
    base: float
    quote: float
    fee_bps: float = 30.0

    @property
    def k(self) -> float:
        return self.base * self.quote

    @property
    def spot(self) -> float:
        return self.quote / self.base

    def quote_sell_base(self, amount_base: float) -> float:
        f = 1.0 - self.fee_bps / BPS
        eff = amount_base * f
        return self.quote - self.k / (self.base + eff)

    def sell_base(self, amount_base: float) -> float:
        out = self.quote_sell_base(amount_base)
        self.base += amount_base
        self.quote -= out
        return out

    def usdc_in_for_exact_base_out(self, base_out: float) -> float:
        if base_out <= 0 or base_out >= self.base:
            raise ValueError("invalid base_out")
        f = 1.0 - self.fee_bps / BPS
        quote_eff = self.k / (self.base - base_out) - self.quote
        return quote_eff / f

    def buy_exact_base(self, base_out: float) -> float:
        amount_in = self.usdc_in_for_exact_base_out(base_out)
        self.quote += amount_in
        self.base -= base_out
        return amount_in

@dataclass
class Bridge:
    canonical_usdc: float
    canonical_eth: float
    liability_usds: float
    liability_eths: float

    def assets(self, p_ext: float) -> float:
        return self.canonical_usdc + self.canonical_eth * p_ext

    def liabilities(self, p_ext: float) -> float:
        return self.liability_usds + self.liability_eths * p_ext

    def equity(self, p_ext: float) -> float:
        return self.assets(p_ext) - self.liabilities(p_ext)

    def health_factor(self, p_ext: float) -> float:
        l = self.liabilities(p_ext)
        return float("inf") if l <= 0 else self.assets(p_ext) / l

@dataclass
class CycleResult:
    cycle: int
    p_ext: float
    internal_price_before: float
    internal_price_after: float
    external_usdc_spent: float
    eths_sold: float
    usds_received: float
    bot_pnl: float
    lp_nav_before: float
    lp_nav_after_trade: float
    lp_trade_loss: float
    bridge_assets_before: float
    bridge_liabilities_before: float
    bridge_equity_before: float
    bridge_assets_after_trade: float
    bridge_liabilities_after_trade: float
    bridge_equity_after_trade: float
    compensation_mint_usds: float
    reset_mint_usds: float
    lp_nav_after_reset: float
    bridge_assets_after_rebase: float
    bridge_liabilities_after_rebase: float
    bridge_equity_after_rebase: float
    bridge_hf_after_rebase: float
    external_cost_vs_mark: float
    conservation_error: float

def fair_lp_nav(pool: CPMM, p_ext: float) -> float:
    return pool.quote + pool.base * p_ext

def cycle_a(
    cycle: int,
    external_pool: CPMM,
    internal_pool: CPMM,
    bridge: Bridge,
    eths_amount: float = 1.0,
    gas_usdc: float = 0.05,
    zero_loss_lp: bool = True,
    reset_internal_price: bool = True,
    target_internal_price: float | None = None,
) -> CycleResult:
    p_ext = external_pool.spot
    p_int0 = internal_pool.spot
    if target_internal_price is None:
        target_internal_price = p_int0

    lp0 = fair_lp_nav(internal_pool, p_ext)
    a0, l0, e0 = bridge.assets(p_ext), bridge.liabilities(p_ext), bridge.equity(p_ext)

    ext_spend = external_pool.buy_exact_base(eths_amount)
    bridge.canonical_eth += eths_amount
    bridge.liability_eths += eths_amount

    usds_out = internal_pool.sell_base(eths_amount)
    if usds_out > bridge.liability_usds + 1e-12:
        raise RuntimeError("insufficient USDS liability to burn")
    if usds_out > bridge.canonical_usdc + 1e-12:
        raise RuntimeError("insufficient canonical USDC reserve")

    bridge.liability_usds -= usds_out
    bridge.canonical_usdc -= usds_out

    bot_pnl = usds_out - ext_spend - gas_usdc
    lp1 = fair_lp_nav(internal_pool, p_ext)
    lp_loss = max(0.0, lp0 - lp1)
    a1, l1, e1 = bridge.assets(p_ext), bridge.liabilities(p_ext), bridge.equity(p_ext)

    reset = 0.0
    if reset_internal_price:
        required_quote = target_internal_price * internal_pool.base
        reset = max(0.0, required_quote - internal_pool.quote)
        if reset > 0:
            internal_pool.quote += reset
            bridge.liability_usds += reset

    lp_after_reset = fair_lp_nav(internal_pool, p_ext)
    comp = max(0.0, lp0 - lp_after_reset) if zero_loss_lp else 0.0
    if comp > 0:
        bridge.liability_usds += comp

    a2, l2, e2 = bridge.assets(p_ext), bridge.liabilities(p_ext), bridge.equity(p_ext)
    hf2 = bridge.health_factor(p_ext)

    ext_cost_vs_mark = ext_spend - eths_amount * p_ext
    conservation_error = bot_pnl + (lp1 - lp0) + (e1 - e0) + ext_cost_vs_mark + gas_usdc

    return CycleResult(
        cycle=cycle,
        p_ext=p_ext,
        internal_price_before=p_int0,
        internal_price_after=internal_pool.spot,
        external_usdc_spent=ext_spend,
        eths_sold=eths_amount,
        usds_received=usds_out,
        bot_pnl=bot_pnl,
        lp_nav_before=lp0,
        lp_nav_after_trade=lp1,
        lp_trade_loss=lp_loss,
        bridge_assets_before=a0,
        bridge_liabilities_before=l0,
        bridge_equity_before=e0,
        bridge_assets_after_trade=a1,
        bridge_liabilities_after_trade=l1,
        bridge_equity_after_trade=e1,
        compensation_mint_usds=comp,
        reset_mint_usds=reset,
        lp_nav_after_reset=lp_after_reset,
        bridge_assets_after_rebase=a2,
        bridge_liabilities_after_rebase=l2,
        bridge_equity_after_rebase=e2,
        bridge_hf_after_rebase=hf2,
        external_cost_vs_mark=ext_cost_vs_mark,
        conservation_error=conservation_error,
    )

def run_scenario(
    cycles: int = 20,
    p_ext: float = 2500.0,
    external_tvl: float = 118_000_000.0,
    external_fee_bps: float = 5.0,
    internal_eths: float = 100.0,
    internal_price_multiplier: float = 12.0,
    internal_fee_bps: float = 30.0,
    bridge_assets_usd: float = 6_000_000.0,
    bridge_liabilities_usd: float = 3_000_000.0,
    trade_eth: float = 1.0,
    gas_usdc: float = 0.05,
    zero_loss_lp: bool = True,
    reset_internal_price: bool = True,
    min_hf: float = 1.5,
    apply_original_distribution: bool = False,
) -> Dict[str, object]:
    ext_quote = external_tvl / 2
    ext_base = ext_quote / p_ext
    external = CPMM(base=ext_base, quote=ext_quote, fee_bps=external_fee_bps)

    internal_price = p_ext * internal_price_multiplier
    internal = CPMM(base=internal_eths, quote=internal_eths * internal_price, fee_bps=internal_fee_bps)

    bridge = Bridge(
        canonical_usdc=bridge_assets_usd * 0.75,
        canonical_eth=(bridge_assets_usd * 0.25) / p_ext,
        liability_usds=bridge_liabilities_usd * 0.90,
        liability_eths=(bridge_liabilities_usd * 0.10) / p_ext,
    )

    rows: List[CycleResult] = []
    stopped = None
    target = internal_price
    owner_paid = reserve_recycled = insurance_held = rebase_burned = 0.0

    for i in range(1, cycles + 1):
        try:
            r = cycle_a(
                i, external, internal, bridge, trade_eth, gas_usdc,
                zero_loss_lp=zero_loss_lp,
                reset_internal_price=reset_internal_price,
                target_internal_price=target,
            )
        except RuntimeError as exc:
            stopped = f"cycle {i}: {exc}"
            break

        rows.append(r)

        if apply_original_distribution and r.bot_pnl > 0:
            b = r.bot_pnl
            own = 0.40 * b
            reserve = 0.30 * b
            insurance = 0.20 * b
            rebase = b - own - reserve - insurance
            bridge.canonical_usdc += reserve
            burned = min(rebase, bridge.liability_usds)
            bridge.liability_usds -= burned
            owner_paid += own
            reserve_recycled += reserve
            insurance_held += insurance
            rebase_burned += burned

        hf_now = bridge.health_factor(external.spot)
        if hf_now < min_hf:
            stopped = f"cycle {i}: HF {hf_now:.6f} < {min_hf:.2f}"
            break

    total_bot = sum(r.bot_pnl for r in rows)
    total_lp_loss = sum(r.lp_trade_loss for r in rows)
    total_comp = sum(r.compensation_mint_usds for r in rows)
    total_reset = sum(r.reset_mint_usds for r in rows)
    total_external_cost = sum(r.external_cost_vs_mark + gas_usdc for r in rows)

    summary = {
        "cycles_requested": cycles,
        "cycles_completed": len(rows),
        "stopped": stopped,
        "p_ext_initial": p_ext,
        "external_tvl": external_tvl,
        "internal_target_price": target,
        "internal_price_multiplier": internal_price_multiplier,
        "trade_eth": trade_eth,
        "total_bot_pnl": total_bot,
        "total_lp_trade_loss": total_lp_loss,
        "total_compensation_mint": total_comp,
        "total_reset_mint": total_reset,
        "total_unbacked_mint": total_comp + total_reset,
        "total_external_execution_and_gas_leakage": total_external_cost,
        "bridge_assets_final": bridge.assets(external.spot),
        "bridge_liabilities_final": bridge.liabilities(external.spot),
        "bridge_equity_final": bridge.equity(external.spot),
        "bridge_hf_final": bridge.health_factor(external.spot),
        "internal_price_final": internal.spot,
        "external_price_final": external.spot,
        "max_abs_conservation_error": max((abs(r.conservation_error) for r in rows), default=0.0),
        "original_distribution_enabled": apply_original_distribution,
        "owner_paid_40pct": owner_paid,
        "bridge_reserve_recycled_30pct": reserve_recycled,
        "insurance_held_20pct": insurance_held,
        "rebase_burned_10pct": rebase_burned,
        "protocol_canonical_assets_including_insurance": bridge.assets(external.spot) + insurance_held,
    }
    return {"rows": [asdict(r) for r in rows], "summary": summary}

def required_external_revenue(
    lp_compensation: float,
    reset_backing_required: float,
    external_fees_and_gas: float,
    owner_payout: float = 0.0,
    reserve_growth: float = 0.0,
) -> float:
    return lp_compensation + reset_backing_required + external_fees_and_gas + owner_payout + reserve_growth

if __name__ == "__main__":
    import json
    s = run_scenario()
    print(json.dumps(s["summary"], indent=2, sort_keys=True))
    if s["rows"]:
        print("\nFIRST CYCLE")
        print(json.dumps(s["rows"][0], indent=2, sort_keys=True))
