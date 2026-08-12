from dataclasses import dataclass
import csv, math
from pathlib import Path

FEE_BPS=30
PROTO_BPS=10
TARGET=1.0

@dataclass
class Cycle:
    cycle:int
    q:float
    x0:float
    y0:float
    minted:float
    sale_proceeds:float
    x_after_sell:float
    y_after_sell:float
    p_after_sell:float
    topup_to_peg:float
    min_value_added:float
    value_added:float
    gas:float
    surplus:float
    x_final:float
    y_final:float
    p_final:float


def sell_minted_and_restore(x,y,q,value_added_multiple=3.0,gas=0.01):
    # mirrors V4 sell math in continuous-dollar units at target=$1
    e=x*q
    total_fee=e*FEE_BPS/10000
    pfee=e*PROTO_BPS/10000
    curve_in=e-total_fee
    to_pool=e-pfee
    k=x*y
    y_curve_new=k/(x+curve_in)
    out=y-y_curve_new
    x2=x+to_pool
    y2=y-out
    p2=y2/x2
    # one-sided real stable top-up needed to restore exactly $1 while leaving emitted USDS in LP
    topup=max(0.0, x2*TARGET-y2)
    # proceeds are available capital; only topup-proceeds must be NEW value added
    min_va=max(0.0, topup+gas)  # if sale proceeds remain deployed as productive principal
    va=value_added_multiple*out
    available=va  # only NEW value-added is used to replenish the PP buffer
    surplus=available-topup-gas
    y3=y2+topup
    return e,out,x2,y2,p2,topup,min_va,va,surplus,x2,y3,y3/x2


def run(q=0.01, cycles=100, m=3.0, gas=0.01, initial=1_000_000.0, pp_buffer=None):
    if pp_buffer is None:
        pp_buffer = initial
    initial_external_capital = initial + pp_buffer
    x=y=initial
    rows=[]
    total_mint=total_sale=total_va=total_topup=total_gas=total_surplus=0.0
    for i in range(1,cycles+1):
        vals=sell_minted_and_restore(x,y,q,m,gas)
        e,out,x2,y2,p2,topup,min_va,va,surplus,xf,yf,pf=vals
        rows.append(Cycle(i,q,x,y,e,out,x2,y2,p2,topup,min_va,va,gas,surplus,xf,yf,pf))
        total_mint+=e; total_sale+=out; total_va+=va; total_topup+=topup; total_gas+=gas; total_surplus+=surplus
        x,y=xf,yf
    return rows, {
      'q':q,'cycles':cycles,'value_added_multiple':m,'gas_per_cycle_usd':gas,
      'initial_pool_usdc':initial,
      'initial_pp_buffer_usdc':pp_buffer,
      'initial_external_capital':initial_external_capital,
      'final_pool_external_usdc':y,
      'final_display_tvl':2*y,
      'cumulative_minted_usds':total_mint,
      'cumulative_sale_proceeds_usdc':total_sale,
      'cumulative_value_added_usdc':total_va,
      'cumulative_topup_usdc':total_topup,
      'cumulative_gas_usd':total_gas,
      'cumulative_surplus_usdc':total_surplus,
      'mint_per_initial_external_dollar':total_mint/initial_external_capital,
      'sale_proceeds_per_initial_external_dollar':total_sale/initial_external_capital,
      'value_added_per_initial_external_dollar':total_va/initial_external_capital,
      'distributable_surplus_per_initial_external_dollar':total_surplus/initial_external_capital,
      'final_price':y/x,
    }

if __name__=='__main__':
    scenarios=[]
    for q in [0.001,0.005,0.01,0.02,0.05]:
      for m in [1.0,2.0,3.0,5.0]:
        for gas in [0.01,0.05,0.10]:
          rows,s=run(q=q,cycles=100,m=m,gas=gas)
          scenarios.append(s)
    out=Path(__file__).with_name('base_v5_mint_sell_pp_stress.csv')
    with open(out,'w',newline='') as f:
      w=csv.DictWriter(f,fieldnames=scenarios[0].keys(),lineterminator='\n');w.writeheader();w.writerows(scenarios)

    print('BASE MINT->SELL->VALUE->RESTORE PP MODEL')
    print('Fee 30bp, protocol token burn 10bp, initial pool $1m USDS / $1m USDC')
    for q in [0.001,0.005,0.01,0.02,0.05]:
      rows,s=run(q=q,cycles=100,m=3.0,gas=0.01)
      r=rows[0]
      print(f"q={q*100:5.2f}% | first sale=${r.sale_proceeds:,.2f} | P_after={r.p_after_sell:.6f} | topup=${r.topup_to_peg:,.2f} | minVA/sale={r.min_value_added/r.sale_proceeds:.4f}x | surplus@3x=${r.surplus:,.2f} | 100cy surplus/init$={s['distributable_surplus_per_initial_external_dollar']:.3f}x | finalP={s['final_price']:.12f}")
    print('\nThe denominator is $2m of external USDC: $1m pool reserve + $1m PP buffer. The x3 value-added is an input assumption, not profit produced by minting.')
