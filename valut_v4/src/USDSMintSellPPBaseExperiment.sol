// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20BaseExp {
    function transfer(address to,uint256 amount) external returns(bool);
    function transferFrom(address from,address to,uint256 amount) external returns(bool);
    function balanceOf(address a) external view returns(uint256);
    function decimals() external view returns(uint8);
}

/**
 * @notice Research-only Base fork experiment for the target problem:
 *         MINT USDS -> SELL into CPMM -> keep sale proceeds productive -> restore final pool price to $1
 *         from a pre-funded PP buffer. No virtual NAV accounting.
 *
 * The sale proceeds remain in productiveUSDC. Therefore the PP buffer must fund the ENTIRE
 * stable top-up required to restore the AMM price, not merely topup minus sale proceeds.
 */
contract USDSMintSellPPBaseExperiment {
    IERC20BaseExp public immutable usdc;
    address public owner;
    uint256 public reserveUSDS; // 18d
    uint256 public reserveUSDC; // raw 6d on Base native USDC
    uint256 public ppBufferUSDC;
    uint256 public productiveUSDC;
    uint256 public totalSupplyUSDS;
    uint256 public cumulativeMinted;
    uint256 public cumulativeSaleProceedsUSDC;
    uint256 public cumulativePPTopupUSDC;
    uint256 public cumulativeRealizedValueAddedUSDC;
    uint256 public cumulativeSurplusUSDC;
    uint256 public swapFeeBps=30;
    uint256 public protocolFeeBps=10;
    uint256 constant ONE=1e18;

    event Cycle(uint256 minted,uint256 saleProceeds,uint256 ppTopup,uint256 priceAfterSell,uint256 priceFinal);
    event ValueAdded(uint256 amount,uint256 bufferReplenished,uint256 surplus);

    modifier onlyOwner(){require(msg.sender==owner,"owner");_;}
    constructor(address usdc_){owner=msg.sender;usdc=IERC20BaseExp(usdc_);require(usdc.decimals()==6,"USDC6");}

    function seed(uint256 usds,uint256 usdcRaw,uint256 bufferRaw) external onlyOwner {
        require(reserveUSDS==0,"seeded");
        require(usdc.transferFrom(msg.sender,address(this),usdcRaw+bufferRaw),"transfer");
        reserveUSDS=usds; reserveUSDC=usdcRaw; ppBufferUSDC=bufferRaw; totalSupplyUSDS=usds;
    }
    function fundPPBuffer(uint256 amount) external {require(usdc.transferFrom(msg.sender,address(this),amount),"transfer");ppBufferUSDC+=amount;}
    function getPrice() public view returns(uint256){return reserveUSDS==0?0:(reserveUSDC*1e12*ONE)/reserveUSDS;}
    function externalNAVUSDC() public view returns(uint256){return reserveUSDC+ppBufferUSDC+productiveUSDC+cumulativeSurplusUSDC;}

    function quoteMintSell(uint256 mintUSDS) public view returns(uint256 saleProceeds,uint256 priceAfterSell,uint256 ppTopup){
        uint256 totalFee=mintUSDS*swapFeeBps/10000;
        uint256 pFee=mintUSDS*protocolFeeBps/10000;
        uint256 curveIn=mintUSDS-totalFee;
        uint256 toPool=mintUSDS-pFee;
        uint256 y18=reserveUSDC*1e12;
        uint256 k=reserveUSDS*y18;
        uint256 newY18=k/(reserveUSDS+curveIn);
        saleProceeds=(y18-newY18)/1e12;
        uint256 x2=reserveUSDS+toPool;
        uint256 y2=reserveUSDC-saleProceeds;
        priceAfterSell=(y2*1e12*ONE)/x2;
        uint256 targetYRaw=x2/1e12; // $1 target, 18d USDS -> raw 6d USDC
        ppTopup=targetYRaw>y2?targetYRaw-y2:0;
    }

    /** Atomic final-state peg restoration. The protocol retains sale proceeds as productive capital. */
    function mintSellRestore(uint256 mintUSDS,uint256 maxTopupUSDC) external onlyOwner returns(uint256 saleProceeds,uint256 ppTopup){
        require(mintUSDS>0,"mint");
        uint256 priceAfter;
        (saleProceeds,priceAfter,ppTopup)=quoteMintSell(mintUSDS);
        require(ppTopup<=maxTopupUSDC && ppTopup<=ppBufferUSDC,"buffer");

        uint256 pFee=mintUSDS*protocolFeeBps/10000;
        uint256 toPool=mintUSDS-pFee;
        totalSupplyUSDS += mintUSDS-pFee; // protocol token fee is treated as immediate burn
        reserveUSDS += toPool;
        reserveUSDC -= saleProceeds;
        productiveUSDC += saleProceeds;
        ppBufferUSDC -= ppTopup;
        reserveUSDC += ppTopup;

        cumulativeMinted += mintUSDS;
        cumulativeSaleProceedsUSDC += saleProceeds;
        cumulativePPTopupUSDC += ppTopup;
        emit Cycle(mintUSDS,saleProceeds,ppTopup,priceAfter,getPrice());
        require(getPrice()>=999999e12 && getPrice()<=1000001e12,"PP not restored");
    }

    /** Real external value added enters later and replenishes PP buffer first. */
    function depositRealizedValueAdded(uint256 amount,uint256 replenishTarget) external onlyOwner returns(uint256 replenished,uint256 surplus){
        require(usdc.transferFrom(msg.sender,address(this),amount),"transfer");
        cumulativeRealizedValueAddedUSDC += amount;
        replenished=amount<replenishTarget?amount:replenishTarget;
        ppBufferUSDC += replenished;
        surplus=amount-replenished;
        cumulativeSurplusUSDC += surplus;
        emit ValueAdded(amount,replenished,surplus);
    }
}
