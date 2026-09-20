// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @notice Policy-only controller. It never treats QE or escrow balances as canonical profit.
contract DynamicCentralBankV17 {
    uint256 public constant BPS=10_000;
    address public owner;

    uint256 public targetHFBps=18_000;
    uint256 public hardHFBps=15_000;
    uint256 public maxExternalTradeBps=1_000; // 10% canonical NAV
    uint256 public minSafetyEdgeBps=2;
    uint256 public qeMax=10_000e18;
    uint256 public escrowTargetBps=2_000;

    modifier onlyOwner(){require(msg.sender==owner,"owner");_;}

    constructor(){owner=msg.sender;}

    struct Quote {
        bool execute;
        uint256 tradeNotional;
        int256 expectedEdgeBps;
        uint256 qeTarget;
        uint256 escrowTarget;
    }

    function healthFactorBps(uint256 canonicalAssets,uint256 circulatingLiabilities)
        public pure returns(uint256)
    {
        if(circulatingLiabilities==0) return type(uint256).max;
        return canonicalAssets*BPS/circulatingLiabilities;
    }

    function expectedEdgeBps(
        uint256 winProbabilityBps,
        uint256 expectedAbsMoveBps,
        uint256 roundTripCostBps
    ) public pure returns(int256) {
        require(winProbabilityBps<=BPS,"p");
        int256 directional=int256(2*winProbabilityBps)-int256(BPS);
        int256 gross=directional*int256(expectedAbsMoveBps)/int256(BPS);
        return gross-int256(roundTripCostBps);
    }

    function quote(
        uint256 canonicalAssets,
        uint256 circulatingLiabilities,
        uint256 winProbabilityBps,
        uint256 expectedAbsMoveBps,
        uint256 roundTripCostBps,
        uint256 confidenceBps
    ) external view returns(Quote memory q) {
        uint256 hf=healthFactorBps(canonicalAssets,circulatingLiabilities);
        uint256 notional=canonicalAssets*maxExternalTradeBps/BPS;
        int256 edge=expectedEdgeBps(winProbabilityBps,expectedAbsMoveBps,roundTripCostBps);

        uint256 qe=qeMax*confidenceBps/BPS;
        uint256 escrow=canonicalAssets*escrowTargetBps/BPS;

        bool ok=hf>=hardHFBps && edge>int256(minSafetyEdgeBps);
        q=Quote(ok,notional,edge,qe,escrow);
    }

    function setRisk(
        uint256 targetHF,
        uint256 hardHF,
        uint256 maxTrade,
        uint256 minEdge
    ) external onlyOwner {
        require(targetHF>=hardHF && hardHF>=BPS,"hf");
        require(maxTrade<=1_000,"trade");
        targetHFBps=targetHF;
        hardHFBps=hardHF;
        maxExternalTradeBps=maxTrade;
        minSafetyEdgeBps=minEdge;
    }
}
