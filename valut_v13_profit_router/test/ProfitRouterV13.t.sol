// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "../src/ProfitRouterV13.sol";

contract ProfitRouterV13Test {
    function testHealingDiscount() public {
        ProfitRouterV13 r=new ProfitRouterV13();
        ProfitRouterV13.Quote memory heal=r.quote(10e6,-1,20e6,20e6);
        ProfitRouterV13.Quote memory harm=r.quote(10e6,1,20e6,20e6);
        require(heal.feeBps<harm.feeBps,"discount");
    }

    function testInternalOrderNeedsNoExternalSettlement() public {
        ProfitRouterV13 r=new ProfitRouterV13();
        ProfitRouterV13.Quote memory q=r.quote(10e6,1,0,20e6);
        require(q.externalAmount==0,"external");
    }

    function testOversizedOrderGetsSplit() public {
        ProfitRouterV13 r=new ProfitRouterV13();
        ProfitRouterV13.Quote memory q=r.quote(100e6,1,20e6,20e6);
        require(q.externalAmount>0,"residual");
        require(q.internalAmount+q.externalAmount==100e6,"conservation");
    }
}
