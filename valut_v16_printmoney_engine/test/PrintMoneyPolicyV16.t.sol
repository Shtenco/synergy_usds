// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "../src/PrintMoneyPolicyV16.sol";

contract PrintMoneyPolicyV16Test {
    function engine() internal returns (PrintMoneyPolicyV16 e) {
        e = new PrintMoneyPolicyV16(100e18, 50e18);
    }

    function testQEExpansionDoesNotChangeHF() public {
        PrintMoneyPolicyV16 e=engine();
        uint256 h=e.hfWad();
        e.expandQeUsds(1000e18);
        require(e.hfWad()==h,"hf");
        require(e.externalSeniorLiabilities()==50e18,"liability");
    }

    function testInternalBufferDoesNotCreateExternalLiability() public {
        PrintMoneyPolicyV16 e=engine();
        e.fill(500e18);
        require(e.escrowedSenior()==500e18,"buffer");
        require(e.externalSeniorLiabilities()==50e18,"liability");
    }

    function testReleaseAtTargetHF() public {
        PrintMoneyPolicyV16 e=engine();
        e.fill(12.5e18);
        e.releaseAgainstCanonical(12.5e18,12.5e18);
        require(e.hfWad()==1.8e18,"hf");
    }

    function testProfitOrRevert() public {
        PrintMoneyPolicyV16 e=engine();
        bool failed;
        try e.bookExternalProfit(.002e18,.0015e18) { failed=false; } catch { failed=true; }
        require(failed,"must revert");
        uint256 net=e.bookExternalProfit(.05e18,.02e18);
        require(net==.03e18,"net");
        require(e.canonicalAssets()==100.03e18,"assets");
    }
}
