// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract ProfitRouterV13 {
    enum Path { INTERNAL_NET, HOT_INVENTORY, EXTERNAL_RESIDUAL }

    struct Quote {
        Path path;
        uint256 feeBps;
        uint256 internalAmount;
        uint256 externalAmount;
        int256 inventoryAfter;
    }

    uint256 public constant BPS=10_000;
    uint256 public baseFeeBps=60;
    uint256 public healDiscountBps=10;
    address public owner;

    modifier onlyOwner(){require(msg.sender==owner,"owner");_;}

    constructor(){owner=msg.sender;}

    function setFees(uint256 base,uint256 healDiscount) external onlyOwner {
        require(base>=10 && base<=120,"base");
        require(healDiscount<=base-10,"discount");
        baseFeeBps=base; healDiscountBps=healDiscount;
    }

    function quote(
        uint256 amount,
        int256 direction,
        int256 inventorySkew,
        uint256 inventoryBand
    ) external view returns(Quote memory q) {
        require(direction==1 || direction==-1,"direction");
        require(amount>0 && inventoryBand>0,"amount");

        uint256 f=baseFeeBps;
        if(inventorySkew!=0 && direction*inventorySkew<0){
            uint256 a=uint256(inventorySkew>0?inventorySkew:-inventorySkew);
            uint256 intensity=a>=inventoryBand?BPS:a*BPS/inventoryBand;
            uint256 d=healDiscountBps*intensity/BPS;
            f=f>d?f-d:10;
            if(f<10) f=10;
        }

        int256 proposed=inventorySkew+direction*int256(amount);
        uint256 absProposed=uint256(proposed>=0?proposed:-proposed);

        if(absProposed<=inventoryBand){
            q=Quote(
                inventorySkew!=0 && uint256(inventorySkew>0?inventorySkew:-inventorySkew)>absProposed
                    ? Path.INTERNAL_NET : Path.HOT_INVENTORY,
                f,amount,0,proposed
            );
            return q;
        }

        uint256 target=inventoryBand/2;
        uint256 externalAmount=absProposed-target;
        int256 after=proposed>=0?int256(target):-int256(target);
        q=Quote(Path.EXTERNAL_RESIDUAL,f,amount-externalAmount,externalAmount,after);
    }
}
