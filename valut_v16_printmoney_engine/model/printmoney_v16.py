from __future__ import annotations
from dataclasses import dataclass
import math

@dataclass
class Ledger:
    canonical_assets: float = 100.0
    external_senior_liabilities: float = 50.0
    escrowed_senior: float = 0.0
    q_usds: float = 0.0
    q_eths_usd: float = 0.0
    canonical_profit: float = 0.0
    external_costs: float = 0.0

class PrintMoneyEngineV16:
    """
    Consolidated owner-only accounting.

    q_*: virtual/junior liquidity. Never redeemable.
    escrowed_senior: protocol-controlled inventory. It is not an external
    liability until released outside the protocol.
    external_senior_liabilities: actual senior redeemable claims outside the
    protocol boundary.
    """
    def __init__(
        self,
        ledger: Ledger|None=None,
        target_hf: float=1.80,
        hard_hf: float=1.50,
        qe_ceiling: float=100_000.0,
        escrow_ceiling: float=10_000.0,
        min_profit_usd: float=0.001,
    ):
        self.s=ledger or Ledger()
        self.target_hf=target_hf
        self.hard_hf=hard_hf
        self.qe_ceiling=qe_ceiling
        self.escrow_ceiling=escrow_ceiling
        self.min_profit_usd=min_profit_usd

    @property
    def hf(self) -> float:
        L=self.s.external_senior_liabilities
        return math.inf if L<=0 else self.s.canonical_assets/L

    @property
    def safety_surplus(self) -> float:
        return self.s.canonical_assets-self.target_hf*self.s.external_senior_liabilities

    def consolidated_nav(self) -> float:
        # Deliberately excludes q-assets and protocol-internal escrowed claims.
        return self.s.canonical_assets

    # ------------------------------
    # Inverse-Fed style policy
    # ------------------------------
    def qe_expansion(self, amount: float, side: str="usds") -> None:
        if amount < 0: raise ValueError("negative")
        if self.s.q_usds+self.s.q_eths_usd+amount > self.qe_ceiling:
            raise ValueError("QE ceiling")
        if side=="usds": self.s.q_usds += amount
        elif side=="eths": self.s.q_eths_usd += amount
        else: raise ValueError("side")

    def qe_contraction(self, amount: float, side: str="usds") -> None:
        if amount < 0: raise ValueError("negative")
        if side=="usds": self.s.q_usds=max(0.0,self.s.q_usds-amount)
        elif side=="eths": self.s.q_eths_usd=max(0.0,self.s.q_eths_usd-amount)
        else: raise ValueError("side")

    # ------------------------------
    # Maker/Sky style pre-minted buffer
    # ------------------------------
    def fill_escrow_buffer(self, amount: float) -> None:
        if amount < 0: raise ValueError("negative")
        if self.s.escrowed_senior+amount > self.escrow_ceiling:
            raise ValueError("escrow ceiling")
        # Internal locked accounting unit: no NAV and no external L change.
        self.s.escrowed_senior += amount

    def trim_escrow_buffer(self, amount: float) -> None:
        if amount < 0 or amount > self.s.escrowed_senior:
            raise ValueError("amount")
        self.s.escrowed_senior -= amount

    def max_one_to_one_release(self) -> float:
        # Release x against x canonical inflow while preserving target HF:
        # (A+x)/(L+x) >= h  -> x <= (A-hL)/(h-1)
        if self.target_hf<=1: return math.inf
        return max(0.0,self.safety_surplus/(self.target_hf-1))

    def release_escrow_against_canonical(self, amount: float, canonical_in: float|None=None) -> None:
        if canonical_in is None: canonical_in=amount
        if amount < 0 or canonical_in < 0 or amount > self.s.escrowed_senior:
            raise ValueError("amount")
        A2=self.s.canonical_assets+canonical_in
        L2=self.s.external_senior_liabilities+amount
        if L2>0 and A2/L2 < self.target_hf:
            raise ValueError("target HF")
        self.s.escrowed_senior-=amount
        self.s.canonical_assets=A2
        self.s.external_senior_liabilities=L2

    def redeem_external_senior(self, amount: float) -> None:
        if amount<0 or amount>self.s.external_senior_liabilities:
            raise ValueError("amount")
        if amount>self.s.canonical_assets:
            raise ValueError("insolvent")
        self.s.canonical_assets-=amount
        self.s.external_senior_liabilities-=amount

    # ------------------------------
    # Beanstalk-style state dependent "Sunrise"
    # ------------------------------
    def sunrise(self, delta_quote_usd: float, throughput_need_usd: float=0.0) -> dict:
        """
        delta_quote_usd > 0 : internal quote side needs virtual expansion.
        delta_quote_usd < 0 : contract virtual quote side.
        Escrow target is a throughput buffer, not profit.
        """
        action={"qe_expand":0.0,"qe_contract":0.0,"buffer_fill":0.0,"buffer_trim":0.0}
        if delta_quote_usd>0:
            amt=min(delta_quote_usd,self.qe_ceiling-(self.s.q_usds+self.s.q_eths_usd))
            if amt>0:
                self.qe_expansion(amt,"usds"); action["qe_expand"]=amt
        elif delta_quote_usd<0:
            amt=min(-delta_quote_usd,self.s.q_usds)
            self.qe_contraction(amt,"usds"); action["qe_contract"]=amt

        target=min(self.escrow_ceiling,max(0.0,throughput_need_usd))
        if self.s.escrowed_senior<target:
            amt=target-self.s.escrowed_senior
            self.fill_escrow_buffer(amt); action["buffer_fill"]=amt
        elif self.s.escrowed_senior>target:
            amt=self.s.escrowed_senior-target
            self.trim_escrow_buffer(amt); action["buffer_trim"]=amt
        return action

    # ------------------------------
    # MoneyPrinter profit-or-revert gate
    # ------------------------------
    def execute_external_profit(self, gross_external_gain: float, external_cost: float) -> float:
        """
        Called only for REAL external gain, e.g. user-paid fee or genuine
        cross-venue arbitrage. Internal gradients must never be passed here.
        """
        if gross_external_gain<0 or external_cost<0:
            raise ValueError("negative")
        net=gross_external_gain-external_cost
        if net < self.min_profit_usd:
            raise ValueError("profit-or-revert")
        self.s.canonical_assets += net
        self.s.canonical_profit += net
        self.s.external_costs += external_cost
        return net

    def safe_seniorize_from_new_profit(self, requested: float) -> float:
        """
        Convert internal escrow/junior capacity into external senior capacity
        only to the extent that already-realized canonical profit supports it.
        """
        if requested<0: raise ValueError("negative")
        # To avoid consuming pre-existing safety surplus, use profit/h as fresh
        # senior capacity.
        capacity=max(0.0,self.s.canonical_profit/self.target_hf)
        return min(requested,capacity,self.s.escrowed_senior)

    def invariant(self) -> dict:
        return {
            "nav":self.consolidated_nav(),
            "hf":self.hf,
            "safety_surplus":self.safety_surplus,
            "qe_virtual":self.s.q_usds+self.s.q_eths_usd,
            "escrowed_internal":self.s.escrowed_senior,
            "external_liabilities":self.s.external_senior_liabilities,
            "hard_hf_ok":self.hf>=self.hard_hf,
        }

def demo():
    e=PrintMoneyEngineV16()
    before=e.invariant()
    e.sunrise(delta_quote_usd=200.0,throughput_need_usd=500.0)
    after_qe=e.invariant()
    # Real external profit example only; not a forecast.
    e.execute_external_profit(gross_external_gain=.10,external_cost=.03)
    after_profit=e.invariant()
    return {"before":before,"after_qe":after_qe,"after_profit":after_profit}

if __name__=="__main__":
    print(demo())
