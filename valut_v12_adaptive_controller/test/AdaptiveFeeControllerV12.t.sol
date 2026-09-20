// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "../src/AdaptiveFeeControllerV12.sol";

contract AdaptiveFeeControllerV12Test {
    function testDirectionalFee() public {
        AdaptiveFeeControllerV12 c=new AdaptiveFeeControllerV12();
        uint256 heal=c.quoteFeeBps(-1,20e6,20e6);
        uint256 harm=c.quoteFeeBps(1,20e6,20e6);
        require(heal<harm,"directional fee");
    }

    function testBaseFeeAtEta002() public {
        AdaptiveFeeControllerV12 c=new AdaptiveFeeControllerV12();
        require(c.baseFeeBps()==60,"base fee");
    }

    function testQEIsBoundedVirtualCapacity() public {
        AdaptiveFeeControllerV12 c=new AdaptiveFeeControllerV12();
        require(c.qeCapacity(10e6)==500e6,"floor");
        require(c.qeCapacity(2000e6)==2400e6,"scaled");
        require(c.qeCapacity(3000e6)==2500e6,"cap");
    }
}
