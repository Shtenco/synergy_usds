// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "../src/DynamicCentralBankV17.sol";

contract DynamicCentralBankV17Test {
    function testExpectedEdge() public {
        DynamicCentralBankV17 c=new DynamicCentralBankV17();
        // p=65%, move=1%, cost=14bp => (0.30*100bp)-14bp = 16bp.
        require(c.expectedEdgeBps(6500,100,14)==16,"edge");
    }

    function testTenPercentCap() public {
        DynamicCentralBankV17 c=new DynamicCentralBankV17();
        DynamicCentralBankV17.Quote memory q=c.quote(100e18,50e18,9000,500,14,9000);
        require(q.tradeNotional==10e18,"cap");
        require(q.execute,"execute");
    }

    function testNoEdgeNoTrade() public {
        DynamicCentralBankV17 c=new DynamicCentralBankV17();
        DynamicCentralBankV17.Quote memory q=c.quote(100e18,50e18,5500,10,14,5000);
        require(!q.execute,"should skip");
    }
}
