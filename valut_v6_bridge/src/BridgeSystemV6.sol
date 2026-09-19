// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20V6 {
    function totalSupply() external view returns (uint256);
    function balanceOf(address) external view returns (uint256);
    function allowance(address,address) external view returns (uint256);
    function approve(address,uint256) external returns (bool);
    function transfer(address,uint256) external returns (bool);
    function transferFrom(address,address,uint256) external returns (bool);
    function decimals() external view returns (uint8);
}

contract SyntheticTokenV6 {
    string public name;
    string public symbol;
    uint8 public constant decimals = 18;
    uint256 public totalSupply;
    address public immutable minter;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    event Transfer(address indexed from,address indexed to,uint256 value);
    event Approval(address indexed owner,address indexed spender,uint256 value);

    modifier onlyMinter() { require(msg.sender == minter, "minter"); _; }

    constructor(string memory name_, string memory symbol_) {
        name = name_;
        symbol = symbol_;
        minter = msg.sender;
    }

    function approve(address spender,uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender,spender,amount);
        return true;
    }

    function transfer(address to,uint256 amount) external returns (bool) {
        _transfer(msg.sender,to,amount);
        return true;
    }

    function transferFrom(address from,address to,uint256 amount) external returns (bool) {
        uint256 a = allowance[from][msg.sender];
        if (a != type(uint256).max) {
            require(a >= amount, "allowance");
            allowance[from][msg.sender] = a - amount;
            emit Approval(from,msg.sender,a-amount);
        }
        _transfer(from,to,amount);
        return true;
    }

    function mint(address to,uint256 amount) external onlyMinter {
        require(to != address(0), "zero");
        totalSupply += amount;
        balanceOf[to] += amount;
        emit Transfer(address(0),to,amount);
    }

    function burn(address from,uint256 amount) external onlyMinter {
        require(balanceOf[from] >= amount, "balance");
        balanceOf[from] -= amount;
        totalSupply -= amount;
        emit Transfer(from,address(0),amount);
    }

    function _transfer(address from,address to,uint256 amount) internal {
        require(to != address(0) && balanceOf[from] >= amount, "transfer");
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        emit Transfer(from,to,amount);
    }
}

contract BridgeVaultV6 {
    uint256 public constant BPS = 10_000;
    uint256 public constant USDC_SCALE = 1e12;

    IERC20V6 public immutable usdc;
    IERC20V6 public immutable weth;
    SyntheticTokenV6 public immutable usds;
    SyntheticTokenV6 public immutable eths;

    address public owner;
    address public pendingOwner;
    uint256 public ethUsdPrice18;
    uint256 public minHFBps;
    bool public paused;
    bool private entered;

    event PriceUpdated(uint256 ethUsdPrice18);
    event CanonicalFunded(address indexed from,uint256 usdcRaw,uint256 wethWei);
    event Deposited(address indexed user,address indexed to,address indexed canonical,uint256 canonicalAmount,uint256 syntheticAmount18);
    event Redeemed(address indexed user,address indexed to,address indexed canonical,uint256 syntheticBurned18,uint256 canonicalAmount);
    event CompensationMinted(address indexed to,uint256 usdsAmount18,uint256 hfAfterBps);
    event OwnershipTransferStarted(address indexed owner,address indexed pendingOwner);
    event OwnershipTransferred(address indexed oldOwner,address indexed newOwner);
    event Paused(bool status);

    modifier onlyOwner() { require(msg.sender == owner, "owner"); _; }
    modifier whenNotPaused() { require(!paused, "paused"); _; }
    modifier nonReentrant() { require(!entered, "reentrant"); entered = true; _; entered = false; }

    constructor(address usdc_,address weth_,uint256 ethUsdPrice18_,uint256 minHFBps_) {
        require(usdc_ != address(0) && weth_ != address(0), "token");
        require(usdc_.code.length > 0 && weth_.code.length > 0, "code");
        usdc = IERC20V6(usdc_);
        weth = IERC20V6(weth_);
        require(usdc.decimals() == 6 && weth.decimals() == 18, "decimals");
        require(ethUsdPrice18_ > 0, "price");
        require(minHFBps_ >= BPS, "hf");
        ethUsdPrice18 = ethUsdPrice18_;
        minHFBps = minHFBps_;
        owner = msg.sender;
        usds = new SyntheticTokenV6("Synergy Synthetic USD", "USDS");
        eths = new SyntheticTokenV6("Synergy Synthetic ETH", "ETHS");
    }

    function transferOwnership(address next) external onlyOwner {
        require(next != address(0), "zero");
        pendingOwner = next;
        emit OwnershipTransferStarted(owner,next);
    }

    function acceptOwnership() external {
        require(msg.sender == pendingOwner, "pending");
        address old = owner;
        owner = msg.sender;
        pendingOwner = address(0);
        emit OwnershipTransferred(old,msg.sender);
    }

    function setPaused(bool status) external onlyOwner { paused = status; emit Paused(status); }
    function setEthUsdPrice18(uint256 p) external onlyOwner { require(p > 0, "price"); ethUsdPrice18 = p; emit PriceUpdated(p); }
    function setMinHFBps(uint256 bps) external onlyOwner { require(bps >= BPS && bps <= 50_000, "hf"); minHFBps = bps; }

    function canonicalAssetsUsd18() public view returns (uint256) {
        return usdc.balanceOf(address(this)) * USDC_SCALE
            + (weth.balanceOf(address(this)) * ethUsdPrice18) / 1e18;
    }

    function liabilitiesUsd18() public view returns (uint256) {
        return usds.totalSupply()
            + (eths.totalSupply() * ethUsdPrice18) / 1e18;
    }

    function equityUsd18() public view returns (int256) {
        return int256(canonicalAssetsUsd18()) - int256(liabilitiesUsd18());
    }

    function healthFactorBps() public view returns (uint256) {
        uint256 l = liabilitiesUsd18();
        if (l == 0) return type(uint256).max;
        return canonicalAssetsUsd18() * BPS / l;
    }

    function requiredUSDCToReachMinHFRaw() public view returns (uint256) {
        uint256 l = liabilitiesUsd18();
        uint256 target = _ceilDiv(l * minHFBps, BPS);
        uint256 a = canonicalAssetsUsd18();
        if (a >= target) return 0;
        return _ceilDiv(target-a, USDC_SCALE);
    }

    function requiredUSDCForAdditionalUSDSMintRaw(uint256 additionalUSDS18) public view returns (uint256) {
        uint256 l = liabilitiesUsd18() + additionalUSDS18;
        uint256 target = _ceilDiv(l * minHFBps, BPS);
        uint256 a = canonicalAssetsUsd18();
        if (a >= target) return 0;
        return _ceilDiv(target-a, USDC_SCALE);
    }

    function fundCanonicalUSDC(uint256 amountRaw) external whenNotPaused nonReentrant {
        require(amountRaw > 0, "amount");
        _pull(usdc,msg.sender,amountRaw);
        emit CanonicalFunded(msg.sender,amountRaw,0);
    }

    function fundCanonicalWETH(uint256 amountWei) external whenNotPaused nonReentrant {
        require(amountWei > 0, "amount");
        _pull(weth,msg.sender,amountWei);
        emit CanonicalFunded(msg.sender,0,amountWei);
    }

    function depositUSDC(uint256 amountRaw,address to) external whenNotPaused nonReentrant returns (uint256 minted18) {
        require(amountRaw > 0 && to != address(0), "deposit");
        _pull(usdc,msg.sender,amountRaw);
        minted18 = amountRaw * USDC_SCALE;
        usds.mint(to,minted18);
        emit Deposited(msg.sender,to,address(usdc),amountRaw,minted18);
    }

    function depositWETH(uint256 amountWei,address to) external whenNotPaused nonReentrant returns (uint256 minted18) {
        require(amountWei > 0 && to != address(0), "deposit");
        _pull(weth,msg.sender,amountWei);
        minted18 = amountWei;
        eths.mint(to,minted18);
        emit Deposited(msg.sender,to,address(weth),amountWei,minted18);
    }

    function redeemUSDS(uint256 amount18,address to) external whenNotPaused nonReentrant returns (uint256 usdcRaw,uint256 burned18) {
        require(amount18 >= USDC_SCALE && to != address(0), "redeem");
        usdcRaw = amount18 / USDC_SCALE;
        burned18 = usdcRaw * USDC_SCALE;
        require(usdc.balanceOf(address(this)) >= usdcRaw, "USDC reserve");
        usds.burn(msg.sender,burned18);
        require(usdc.transfer(to,usdcRaw), "USDC transfer");
        emit Redeemed(msg.sender,to,address(usdc),burned18,usdcRaw);
    }

    function redeemETHS(uint256 amount18,address to) external whenNotPaused nonReentrant returns (uint256 wethWei) {
        require(amount18 > 0 && to != address(0), "redeem");
        require(weth.balanceOf(address(this)) >= amount18, "WETH reserve");
        eths.burn(msg.sender,amount18);
        require(weth.transfer(to,amount18), "WETH transfer");
        emit Redeemed(msg.sender,to,address(weth),amount18,amount18);
        return amount18;
    }

    function mintCompensationUSDS(address to,uint256 amount18) external onlyOwner whenNotPaused {
        require(to != address(0) && amount18 > 0, "mint");
        uint256 a = canonicalAssetsUsd18();
        uint256 lAfter = liabilitiesUsd18() + amount18;
        require(a * BPS >= lAfter * minHFBps, "HF");
        usds.mint(to,amount18);
        emit CompensationMinted(to,amount18,a * BPS / lAfter);
    }

    function _pull(IERC20V6 token,address from,uint256 amount) internal {
        uint256 beforeBal = token.balanceOf(address(this));
        require(token.transferFrom(from,address(this),amount), "transferFrom");
        require(token.balanceOf(address(this)) == beforeBal + amount, "fee token");
    }

    function _ceilDiv(uint256 a,uint256 b) internal pure returns (uint256) {
        return a == 0 ? 0 : (a-1)/b + 1;
    }
}

contract InternalCPMMV6 {
    uint256 public constant BPS = 10_000;
    IERC20V6 public immutable eths;
    IERC20V6 public immutable usds;
    address public owner;
    uint256 public feeBps;
    bool public seeded;
    bool private entered;

    event Seeded(uint256 ethsAmount,uint256 usdsAmount);
    event SwapETHSToUSDS(address indexed trader,uint256 ethsIn,uint256 usdsOut);
    event SwapUSDSToETHS(address indexed trader,uint256 usdsIn,uint256 ethsOut);

    modifier onlyOwner(){ require(msg.sender == owner, "owner"); _; }
    modifier nonReentrant(){ require(!entered, "reentrant"); entered=true; _; entered=false; }

    constructor(address eths_,address usds_,uint256 feeBps_) {
        require(eths_ != address(0) && usds_ != address(0), "token");
        require(feeBps_ <= 1000, "fee");
        eths = IERC20V6(eths_);
        usds = IERC20V6(usds_);
        owner = msg.sender;
        feeBps = feeBps_;
    }

    function reserveETHS() public view returns(uint256){ return eths.balanceOf(address(this)); }
    function reserveUSDS() public view returns(uint256){ return usds.balanceOf(address(this)); }
    function spotPrice18() public view returns(uint256){ uint256 x=reserveETHS(); return x==0?0:reserveUSDS()*1e18/x; }
    function fairNAVUsd18(uint256 ethUsdPrice18) public view returns(uint256){ return reserveUSDS() + reserveETHS()*ethUsdPrice18/1e18; }

    function seed(uint256 ethsAmount,uint256 usdsAmount) external onlyOwner nonReentrant {
        require(!seeded && ethsAmount>0 && usdsAmount>0, "seed");
        require(eths.transferFrom(msg.sender,address(this),ethsAmount), "ETHS");
        require(usds.transferFrom(msg.sender,address(this),usdsAmount), "USDS");
        seeded=true;
        emit Seeded(ethsAmount,usdsAmount);
    }

    function quoteSellETHS(uint256 amountIn) public view returns(uint256 out) {
        uint256 x=reserveETHS(); uint256 y=reserveUSDS();
        require(x>0 && y>0 && amountIn>0, "liquidity");
        uint256 eff=amountIn*(BPS-feeBps)/BPS;
        out = y - (x*y)/(x+eff);
    }

    function quoteSellUSDS(uint256 amountIn) public view returns(uint256 out) {
        uint256 x=reserveETHS(); uint256 y=reserveUSDS();
        require(x>0 && y>0 && amountIn>0, "liquidity");
        uint256 eff=amountIn*(BPS-feeBps)/BPS;
        out = x - (x*y)/(y+eff);
    }

    function swapETHSToUSDS(uint256 amountIn,uint256 minOut,address to) external nonReentrant returns(uint256 out) {
        require(to!=address(0), "to");
        out=quoteSellETHS(amountIn); require(out>=minOut, "slippage");
        require(eths.transferFrom(msg.sender,address(this),amountIn), "ETHS in");
        require(usds.transfer(to,out), "USDS out");
        emit SwapETHSToUSDS(msg.sender,amountIn,out);
    }

    function swapUSDSToETHS(uint256 amountIn,uint256 minOut,address to) external nonReentrant returns(uint256 out) {
        require(to!=address(0), "to");
        out=quoteSellUSDS(amountIn); require(out>=minOut, "slippage");
        require(usds.transferFrom(msg.sender,address(this),amountIn), "USDS in");
        require(eths.transfer(to,out), "ETHS out");
        emit SwapUSDSToETHS(msg.sender,amountIn,out);
    }
}

interface IAerodromeRouterV6 {
    struct Route { address from; address to; bool stable; address factory; }
    function getAmountsOut(uint256 amountIn,Route[] memory routes) external view returns(uint256[] memory amounts);
    function swapExactTokensForTokens(uint256 amountIn,uint256 amountOutMin,Route[] calldata routes,address to,uint256 deadline)
        external returns(uint256[] memory amounts);
}

contract AerodromeCycleExecutorV6 {
    IERC20V6 public immutable usdc;
    IERC20V6 public immutable weth;
    SyntheticTokenV6 public immutable usds;
    SyntheticTokenV6 public immutable eths;
    BridgeVaultV6 public immutable bridge;
    InternalCPMMV6 public immutable amm;
    IAerodromeRouterV6 public immutable router;
    address public immutable aeroFactory;
    address public owner;
    bool private entered;

    event CycleA(uint256 usdcIn,uint256 wethOut,uint256 usdsOut,uint256 usdcFinal,int256 pnlRawUSDC);

    modifier onlyOwner(){ require(msg.sender==owner,"owner"); _; }
    modifier nonReentrant(){ require(!entered,"reentrant"); entered=true; _; entered=false; }

    constructor(address usdc_,address weth_,address bridge_,address amm_,address router_,address factory_) {
        owner=msg.sender;
        usdc=IERC20V6(usdc_); weth=IERC20V6(weth_);
        bridge=BridgeVaultV6(bridge_); amm=InternalCPMMV6(amm_);
        usds=bridge.usds(); eths=bridge.eths();
        router=IAerodromeRouterV6(router_); aeroFactory=factory_;
    }

    function executeCycleA(uint256 usdcIn,uint256 minWethOut,uint256 minUsdsOut,uint256 deadline)
        external onlyOwner nonReentrant returns(uint256 wethOut,uint256 usdsOut,uint256 usdcFinal,int256 pnlRawUSDC)
    {
        require(usdcIn>0 && usdc.balanceOf(address(this))==0, "input");
        _pull(usdc,msg.sender,usdcIn);
        _forceApprove(usdc,address(router),usdcIn);
        IAerodromeRouterV6.Route[] memory routes=new IAerodromeRouterV6.Route[](1);
        routes[0]=IAerodromeRouterV6.Route(address(usdc),address(weth),false,aeroFactory);
        uint256[] memory amounts=router.swapExactTokensForTokens(usdcIn,minWethOut,routes,address(this),deadline);
        wethOut=amounts[amounts.length-1];

        _forceApprove(weth,address(bridge),wethOut);
        bridge.depositWETH(wethOut,address(this));

        _forceApprove(IERC20V6(address(eths)),address(amm),wethOut);
        usdsOut=amm.swapETHSToUSDS(wethOut,minUsdsOut,address(this));

        bridge.redeemUSDS(usdsOut,address(this));
        uint256 dust=usds.balanceOf(address(this));
        if(dust>0) require(usds.transfer(msg.sender,dust),"dust");

        usdcFinal=usdc.balanceOf(address(this));
        pnlRawUSDC=int256(usdcFinal)-int256(usdcIn);
        require(usdc.transfer(msg.sender,usdcFinal),"return USDC");
        emit CycleA(usdcIn,wethOut,usdsOut,usdcFinal,pnlRawUSDC);
    }

    function _pull(IERC20V6 token,address from,uint256 amount) internal {
        uint256 b=token.balanceOf(address(this));
        require(token.transferFrom(from,address(this),amount),"pull");
        require(token.balanceOf(address(this))==b+amount,"fee token");
    }
    function _forceApprove(IERC20V6 token,address spender,uint256 amount) internal {
        require(token.approve(spender,0),"approve0");
        require(token.approve(spender,amount),"approve");
    }
}

contract ProfitDistributorV6 {
    IERC20V6 public immutable usdc;
    BridgeVaultV6 public immutable bridge;
    address public owner;
    uint256 public insuranceUSDC;
    uint256 public rebaseUSDC;
    bool private entered;

    event RevenueSettled(uint256 amount,uint256 mandatoryTopup,uint256 ownerShare,uint256 reserveShare,uint256 insuranceShare,uint256 rebaseShare);

    modifier onlyOwner(){ require(msg.sender==owner,"owner"); _; }
    modifier nonReentrant(){ require(!entered,"reentrant"); entered=true; _; entered=false; }

    constructor(address usdc_,address bridge_){ usdc=IERC20V6(usdc_); bridge=BridgeVaultV6(bridge_); owner=msg.sender; }

    function distributeRealizedRevenue(uint256 amountRaw) external nonReentrant {
        require(amountRaw>0,"amount");
        uint256 b=usdc.balanceOf(address(this));
        require(usdc.transferFrom(msg.sender,address(this),amountRaw),"pull");
        require(usdc.balanceOf(address(this))==b+amountRaw,"fee token");

        uint256 required=bridge.requiredUSDCToReachMinHFRaw();
        uint256 mandatory=amountRaw<required?amountRaw:required;
        if(mandatory>0){ _fundBridge(mandatory); }
        uint256 rem=amountRaw-mandatory;

        uint256 ownerShare;
        uint256 reserveShare;
        uint256 insuranceShare;
        uint256 rebaseShare;
        if(rem>0 && bridge.healthFactorBps()>=bridge.minHFBps()){
            ownerShare=rem*40/100;
            reserveShare=rem*30/100;
            insuranceShare=rem*20/100;
            rebaseShare=rem-ownerShare-reserveShare-insuranceShare;
            if(reserveShare>0) _fundBridge(reserveShare);
            if(ownerShare>0) require(usdc.transfer(owner,ownerShare),"owner pay");
            insuranceUSDC+=insuranceShare;
            rebaseUSDC+=rebaseShare;
        }
        emit RevenueSettled(amountRaw,mandatory,ownerShare,reserveShare,insuranceShare,rebaseShare);
    }

    function deployInsuranceToBridge(uint256 amountRaw) external onlyOwner nonReentrant {
        require(amountRaw<=insuranceUSDC,"insurance"); insuranceUSDC-=amountRaw; _fundBridge(amountRaw);
    }
    function deployRebaseToBridge(uint256 amountRaw) external onlyOwner nonReentrant {
        require(amountRaw<=rebaseUSDC,"rebase"); rebaseUSDC-=amountRaw; _fundBridge(amountRaw);
    }

    function _fundBridge(uint256 amountRaw) internal {
        require(usdc.approve(address(bridge),0),"approve0");
        require(usdc.approve(address(bridge),amountRaw),"approve");
        bridge.fundCanonicalUSDC(amountRaw);
    }
}
