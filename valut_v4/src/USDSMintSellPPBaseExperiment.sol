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
    address public pendingOwner;
    bool public paused;
    bool private entered;
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
    event OwnershipTransferStarted(address indexed owner,address indexed pendingOwner);
    event OwnershipTransferred(address indexed oldOwner,address indexed newOwner);
    event Paused(bool status);
    event EmergencyExit(address indexed recipient,uint256 amount);

    modifier onlyOwner(){require(msg.sender==owner,"owner");_;}
    modifier whenNotPaused(){require(!paused,"paused");_;}
    modifier nonReentrant(){require(!entered,"reentrant");entered=true;_;entered=false;}
    constructor(address usdc_){require(usdc_!=address(0) && usdc_.code.length>0,"USDC");owner=msg.sender;usdc=IERC20BaseExp(usdc_);require(usdc.decimals()==6,"USDC6");}

    function transferOwnership(address next) external onlyOwner {require(next!=address(0),"zero");pendingOwner=next;emit OwnershipTransferStarted(owner,next);}
    function acceptOwnership() external {require(msg.sender==pendingOwner,"pending");address old=owner;owner=msg.sender;pendingOwner=address(0);emit OwnershipTransferred(old,msg.sender);}
    function setPaused(bool status) external onlyOwner {paused=status;emit Paused(status);}

    function _pull(address from,uint256 amount) internal {
        uint256 beforeBalance=usdc.balanceOf(address(this));
        require(usdc.transferFrom(from,address(this),amount),"transfer");
        require(usdc.balanceOf(address(this))==beforeBalance+amount,"fee token");
    }

    function seed(uint256 usds,uint256 usdcRaw,uint256 bufferRaw) external onlyOwner whenNotPaused nonReentrant {
        require(reserveUSDS==0 && usds>0 && usdcRaw>0 && bufferRaw>0,"seed");
        _pull(msg.sender,usdcRaw+bufferRaw);
        reserveUSDS=usds; reserveUSDC=usdcRaw; ppBufferUSDC=bufferRaw; totalSupplyUSDS=usds;
    }
    function fundPPBuffer(uint256 amount) external whenNotPaused nonReentrant {require(amount>0,"amount");_pull(msg.sender,amount);ppBufferUSDC+=amount;}
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
    function mintSellRestore(uint256 mintUSDS,uint256 maxTopupUSDC) external onlyOwner whenNotPaused nonReentrant returns(uint256 saleProceeds,uint256 ppTopup){
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
    function depositRealizedValueAdded(uint256 amount,uint256 replenishTarget) external onlyOwner whenNotPaused nonReentrant returns(uint256 replenished,uint256 surplus){
        require(amount>0,"amount");_pull(msg.sender,amount);
        cumulativeRealizedValueAddedUSDC += amount;
        replenished=amount<replenishTarget?amount:replenishTarget;
        ppBufferUSDC += replenished;
        surplus=amount-replenished;
        cumulativeSurplusUSDC += surplus;
        emit ValueAdded(amount,replenished,surplus);
    }

    /** Paused-only recovery. This irreversibly closes accounting before transferring all USDC. */
    function emergencyExit(address recipient) external onlyOwner nonReentrant returns(uint256 amount) {
        require(paused && recipient!=address(0),"exit");
        amount=usdc.balanceOf(address(this));
        reserveUSDS=0;reserveUSDC=0;ppBufferUSDC=0;productiveUSDC=0;cumulativeSurplusUSDC=0;
        totalSupplyUSDS=0;
        require(usdc.transfer(recipient,amount),"transfer");
        require(usdc.balanceOf(address(this))==0,"balance");
        emit EmergencyExit(recipient,amount);
    }
}
