// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract AdaptiveFeeControllerV12 {
    uint256 public constant BPS=10_000;
    address public owner;

    uint256 public refFeeBps=10;
    uint256 public etaPpm=20_000; // eta=0.020 represented in ppm
    uint256 public minFeeBps=10;
    uint256 public maxFeeBps=120;
    uint256 public healDiscountBps=15;
    uint256 public worsenSurchargeBps=20;

    modifier onlyOwner(){require(msg.sender==owner,"owner");_;}

    constructor(){owner=msg.sender;}

    function setEtaPpm(uint256 x) external onlyOwner {
        require(x>=1_000 && x<=100_000,"eta");
        etaPpm=x;
    }

    function baseFeeBps() public view returns(uint256) {
        // ref + 1/eta. etaPpm = eta*1e6.
        uint256 inv=1_000_000/etaPpm;
        uint256 f=refFeeBps+inv;
        if(f<minFeeBps) return minFeeBps;
        if(f>maxFeeBps) return maxFeeBps;
        return f;
    }

    function quoteFeeBps(int256 direction,int256 skew,uint256 band) external view returns(uint256) {
        require(direction==1 || direction==-1,"direction");
        uint256 f=baseFeeBps();
        if(skew==0 || band==0) return f;
        uint256 a=uint256(skew>0?skew:-skew);
        uint256 intensity=a>=band?BPS:a*BPS/band;
        bool worsens=(direction>0 && skew>0)||(direction<0 && skew<0);
        if(worsens){
            f += worsenSurchargeBps*intensity/BPS;
            if(f>maxFeeBps) f=maxFeeBps;
        } else {
            uint256 d=healDiscountBps*intensity/BPS;
            f=f>d?f-d:minFeeBps;
            if(f<minFeeBps) f=minFeeBps;
        }
        return f;
    }

    function qeCapacity(uint256 requestedGross) external pure returns(uint256) {
        uint256 q=requestedGross*120/100;
        if(q<500e6) return 500e6;
        if(q>2500e6) return 2500e6;
        return q;
    }

    function inventoryBand(uint256 hfBps) external pure returns(uint256) {
        if(hfBps>=22_000) return 30e6;
        if(hfBps>=20_000) return 25e6;
        if(hfBps>=18_000) return 20e6;
        if(hfBps>=17_000) return 15e6;
        return 10e6;
    }
}
