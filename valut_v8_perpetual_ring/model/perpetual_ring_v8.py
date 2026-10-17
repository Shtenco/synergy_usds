from dataclasses import dataclass
import math

BPS=10_000

@dataclass
class Epoch:
    executed: bool
    volume: float
    gross_external_revenue: float
    operating_cost: float
    net_external_revenue: float
    owner_payout: float
    assets: float
    liabilities: float
    hf: float
    safety_surplus: float

class PerpetualBridgeRing:
    def __init__(self, assets=100.0, liabilities=50.0, hard_hf=1.50, soft_hf=1.70, target_hf=1.80, payout_gate_hf=2.00, owner_share=0.40, min_edge_multiplier=1.25):
        self.A=float(assets); self.L=float(liabilities); self.owner=0.0
        self.hard_hf=hard_hf; self.soft_hf=soft_hf; self.target_hf=target_hf
        self.payout_gate_hf=payout_gate_hf; self.owner_share=owner_share
        self.min_edge_multiplier=min_edge_multiplier; self.paused=False; self.epochs=0

    @property
    def hf(self): return math.inf if self.L<=0 else self.A/self.L

    @property
    def safety_surplus(self): return self.A-self.target_hf*self.L

    def quote_net_external_revenue(self, external_volume, fee_margin_bps, genuine_alpha_bps=0.0, variable_cost_bps=0.0, fixed_cost=0.0):
        gross=external_volume*(fee_margin_bps+genuine_alpha_bps)/BPS
        costs=external_volume*variable_cost_bps/BPS+fixed_cost
        return gross,costs,gross-costs

    def should_execute(self,gross,costs):
        return gross>0 and gross >= costs*self.min_edge_multiplier

    def add_matched_deposit(self,canonical_in,synthetic_liability_out):
        A2=self.A+canonical_in; L2=self.L+synthetic_liability_out
        if L2>0 and A2/L2 < self.target_hf: raise ValueError('target HF')
        self.A=A2; self.L=L2

    def max_one_to_one_liability_growth(self):
        if self.target_hf<=1: return math.inf
        return max(0.0,self.safety_surplus/(self.target_hf-1))

    def step(self, external_volume, fee_margin_bps, genuine_alpha_bps=0.0, variable_cost_bps=0.0, fixed_cost=0.0):
        gross,costs,net=self.quote_net_external_revenue(external_volume,fee_margin_bps,genuine_alpha_bps,variable_cost_bps,fixed_cost)
        if self.paused or not self.should_execute(gross,costs):
            return Epoch(False,external_volume,gross,costs,0.0,0.0,self.A,self.L,self.hf,self.safety_surplus)
        self.A += net
        payout=0.0
        if net>0 and self.hf>=self.payout_gate_hf:
            candidate=self.owner_share*net
            max_safe=max(0.0,self.A-self.payout_gate_hf*self.L)
            payout=min(candidate,max_safe)
            self.A-=payout; self.owner+=payout
        self.epochs+=1
        if self.hf < self.hard_hf: self.paused=True
        return Epoch(True,external_volume,gross,costs,net,payout,self.A,self.L,self.hf,self.safety_surplus)

def break_even_volume(fixed_cost,net_variable_margin_bps):
    if net_variable_margin_bps<=0: return math.inf
    return fixed_cost/(net_variable_margin_bps/BPS)

def perpetual_condition(owner_share,target_hf,net_external_revenue,net_liability_growth):
    return (1-owner_share)*net_external_revenue-(target_hf-1)*net_liability_growth

def demo_100usd(cycles=10_000):
    ring=PerpetualBridgeRing()
    for _ in range(cycles):
        ring.step(external_volume=5.0, fee_margin_bps=10.0, genuine_alpha_bps=5.0, variable_cost_bps=5.0, fixed_cost=0.002)
    return {'cycles':cycles,'assets':ring.A,'liabilities':ring.L,'hf':ring.hf,'owner_paid':ring.owner,'target_surplus':ring.safety_surplus,'paused':ring.paused}

if __name__=='__main__':
    print('break_even_5bp',break_even_volume(0.002,5))
    print('break_even_10bp',break_even_volume(0.002,10))
    print('demo',demo_100usd())