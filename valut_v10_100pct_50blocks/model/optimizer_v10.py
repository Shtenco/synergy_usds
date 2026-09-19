import math

def required_net_margin_for_target(target_multiple=2.0, blocks=50, rotations_per_block=1, utilization=0.10):
    return (target_multiple**(1/(blocks*rotations_per_block))-1)/utilization

def required_rotations_for_margin(net_margin, target_multiple=2.0, blocks=50, utilization=0.10):
    return math.log(target_multiple)/(blocks*math.log(1+utilization*net_margin))

def simulate(initial_nav=100.0, blocks=50, rotations_per_block=87, utilization=0.10, net_margin=0.0016):
    nav=initial_nav; gross=0.0
    for _ in range(blocks):
        for _ in range(rotations_per_block):
            v=utilization*nav
            gross += v
            nav += v*net_margin
    return {'final_nav':nav,'profit':nav-initial_nav,'gross_volume':gross,'roi':nav/initial_nav-1}

def bridge_net_margin(bridge_fee_bps=20, net_settlement_ratio=.10, external_fee_bps=30,
                      external_slippage_bps=0, gas_per_gross_bps=1):
    # Per $1 gross external/user flow. Netting means DEX fee/slippage only on residual settlement.
    return (bridge_fee_bps - net_settlement_ratio*(external_fee_bps+external_slippage_bps) - gas_per_gross_bps)/10000

def qe_recharge_capacity(retained_canonical_revenue, target_hf=1.80):
    # qUSDS/qETHS can be virtual without senior debt. This returns only the amount that can be seniorized safely.
    return retained_canonical_revenue/target_hf

if __name__=='__main__':
    for k in [1,2,5,10,20,50,100]:
        m=required_net_margin_for_target(rotations_per_block=k)
        print(f'k={k:3d} required_net_margin={100*m:8.4f}% ({m*10000:8.2f} bp)')
    mu=bridge_net_margin()
    k=required_rotations_for_margin(mu)
    print('bridge_net_margin=',mu,mu*10000,'bp')
    print('required_rotations_per_block=',k)
    print('87 rotations demo=',simulate(rotations_per_block=87,net_margin=mu))