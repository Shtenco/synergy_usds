from dataclasses import dataclass

BPS=10_000

@dataclass
class ExternalPool:
    price: float = 2491.40
    tvl: float = 128_614_644.53
    fee_bps: float = 30.0

    def buy_weth_with_usdc(self, usdc_in: float) -> float:
        # For $10 versus >$100m TVL, price impact is negligible compared with the fee.
        return usdc_in*(1-self.fee_bps/BPS)/self.price

@dataclass
class QEForkPool:
    fair_nav: float = 50.0
    target_multiple: float = 16.4
    internal_fee_bps: float = 30.0
    external_price: float = 2491.40

    def __post_init__(self):
        self.eths = self.fair_nav/((1+self.target_multiple)*self.external_price)
        self.senior_usds = self.target_multiple*self.external_price*self.eths
        self.qe_usds = 0.0

    @property
    def total_quote(self): return self.senior_usds+self.qe_usds
    @property
    def price(self): return self.total_quote/self.eths

    def sell_eths_and_qe_reset(self, eths_in: float):
        y=self.total_quote
        k=self.eths*y
        eff=eths_in*(1-self.internal_fee_bps/BPS)
        out_total=y-k/(self.eths+eff)
        senior_share=0.0 if y<=0 else self.senior_usds/y
        senior_out=out_total*senior_share
        qe_out=out_total-senior_out
        self.eths += eths_in
        self.senior_usds -= senior_out
        self.qe_usds -= qe_out
        target_quote=self.target_multiple*self.external_price*self.eths
        qe_mint=max(0.0,target_quote-self.total_quote)
        self.qe_usds += qe_mint
        return {
            'total_out':out_total,
            'senior_redeemable_out':senior_out,
            'junior_qe_out':qe_out,
            'qe_mint':qe_mint,
            'price_after_reset':self.price,
            'senior_reserve':self.senior_usds,
            'qe_reserve':self.qe_usds,
        }

def bridge_ring_revenue(gross_volume=10.0, bridge_fee_bps=20.0,
                        net_settlement_ratio=0.10, external_fee_bps=30.0,
                        fixed_batch_gas=0.001):
    fee_income=gross_volume*bridge_fee_bps/BPS
    external_settlement=gross_volume*net_settlement_ratio
    external_fee=external_settlement*external_fee_bps/BPS
    net=fee_income-external_fee-fixed_batch_gas
    return {
        'gross_volume':gross_volume,
        'fee_income':fee_income,
        'external_settlement':external_settlement,
        'external_fee':external_fee,
        'fixed_batch_gas':fixed_batch_gas,
        'net_canonical_revenue':net,
    }

def safe_senior_recharge(retained_canonical_revenue: float, target_hf=1.80):
    # New canonical revenue can support at most R/h of new senior liabilities
    # without decreasing B=A-hL.
    return max(0.0,retained_canonical_revenue/target_hf)

def run_qe_demo(cycles=10, trade_usdc=10.0, target_multiple=16.4):
    ext=ExternalPool()
    pool=QEForkPool(target_multiple=target_multiple)
    rows=[]
    for i in range(1,cycles+1):
        q=ext.buy_weth_with_usdc(trade_usdc)
        r=pool.sell_eths_and_qe_reset(q)
        r['cycle']=i
        r['external_trade_usdc']=trade_usdc
        r['external_weth']=q
        rows.append(r)
    return rows

def sustainable_fee_scenario(cycles=10_000, owner_share=.40):
    A=100.0; L=50.0; owner=0.0
    for _ in range(cycles):
        r=bridge_ring_revenue()
        if r['net_canonical_revenue']<=0: continue
        owner_cut=owner_share*r['net_canonical_revenue']
        retained=r['net_canonical_revenue']-owner_cut
        A += retained
        owner += owner_cut
    return {'cycles':cycles,'assets':A,'liabilities':L,'hf':A/L,'owner':owner}

if __name__=='__main__':
    rows=run_qe_demo(3)
    for r in rows: print(r)
    print(bridge_ring_revenue())
    print(sustainable_fee_scenario())