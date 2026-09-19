// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../src/BridgeSystemV6.sol";

interface VmV6 {
    function envString(string calldata) external returns(string memory);
    function envOr(string calldata,address defaultValue) external returns(address);
    function createSelectFork(string calldata) external returns(uint256);
    function prank(address) external;
}

contract BaseForkBridgeV6Test {
    VmV6 constant vm=VmV6(address(uint160(uint256(keccak256("hevm cheat code")))));

    address constant BASE_USDC=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913;
    address constant BASE_WETH=0x4200000000000000000000000000000000000006;
    address constant AERO_ROUTER=0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43;
    address constant AERO_FACTORY=0x420DD381b31aEf6683db6B902084cB0FFECe40Da;
    address constant DEFAULT_FUNDING_POOL=0x3fe04a59ebD38CF06080A6f60A98D124Eb59392A;

    uint256 constant U=1e6;
    uint256 constant D=1e18;

    IERC20V6 usdc;
    IERC20V6 weth;
    IAerodromeRouterV6 router;
    BridgeVaultV6 bridge;
    InternalCPMMV6 amm;
    AerodromeCycleExecutorV6 executor;
    SyntheticTokenV6 usds;
    SyntheticTokenV6 eths;
    uint256 externalPrice18;
    uint256 targetInternalPrice18;

    event Snapshot(string tag,uint256 a,uint256 b,uint256 c,uint256 d);

    function setUp() public {
        vm.createSelectFork(vm.envString("BASE_RPC_URL"));
        require(block.chainid==8453,"not Base mainnet fork");
        require(BASE_USDC.code.length>0 && BASE_WETH.code.length>0 && AERO_ROUTER.code.length>0,"Base contracts missing");

        usdc=IERC20V6(BASE_USDC);
        weth=IERC20V6(BASE_WETH);
        router=IAerodromeRouterV6(AERO_ROUTER);
        require(usdc.decimals()==6 && weth.decimals()==18,"decimals");

        IAerodromeRouterV6.Route[] memory priceRoute=new IAerodromeRouterV6.Route[](1);
        priceRoute[0]=IAerodromeRouterV6.Route(BASE_WETH,BASE_USDC,false,AERO_FACTORY);
        uint256[] memory q=router.getAmountsOut(1 ether,priceRoute);
        require(q.length==2 && q[1]>1_000*U,"bad external quote");
        externalPrice18=q[1]*1e12;

        address funding=vm.envOr("BASE_FUNDING_POOL",DEFAULT_FUNDING_POOL);
        require(usdc.balanceOf(funding)>=60_000*U,"funding USDC too small");
        require(weth.balanceOf(funding)>=2 ether,"funding WETH too small");
        vm.prank(funding); require(usdc.transfer(address(this),60_000*U),"fund USDC");
        vm.prank(funding); require(weth.transfer(address(this),2 ether),"fund WETH");

        bridge=new BridgeVaultV6(BASE_USDC,BASE_WETH,externalPrice18,15_000);
        usds=bridge.usds(); eths=bridge.eths();
        require(usdc.approve(address(bridge),type(uint256).max),"approve bridge USDC");
        require(weth.approve(address(bridge),type(uint256).max),"approve bridge WETH");

        bridge.depositUSDC(30_000*U,address(this));
        bridge.depositWETH(1 ether,address(this));
        amm=new InternalCPMMV6(address(eths),address(usds),30);
        require(eths.approve(address(amm),type(uint256).max),"approve ETHS");
        require(usds.approve(address(amm),type(uint256).max),"approve USDS");
        amm.seed(1 ether,30_000*D);
        targetInternalPrice18=amm.spotPrice18();
        require(targetInternalPrice18==30_000*D,"target price");

        uint256 topup=bridge.requiredUSDCToReachMinHFRaw();
        if(topup>0) bridge.fundCanonicalUSDC(topup);
        require(bridge.healthFactorBps()>=15_000,"initial HF");

        executor=new AerodromeCycleExecutorV6(BASE_USDC,BASE_WETH,address(bridge),address(amm),AERO_ROUTER,AERO_FACTORY);
    }

    function testCycleA_ProfitIsLPTransfer_ResetNeedsRealBacking() public {
        uint256 lpBefore=amm.fairNAVUsd18(externalPrice18);
        int256 equityBefore=bridge.equityUsd18();
        uint256 hfBefore=bridge.healthFactorBps();
        uint256 usdcBefore=usdc.balanceOf(address(this));

        uint256 amountIn=25*U;
        require(usdc.approve(address(executor),amountIn),"approve executor");
        (uint256 wethOut,uint256 usdsOut,uint256 finalUSDC,int256 pnlRaw)=executor.executeCycleA(
            amountIn,0,0,block.timestamp+60
        );
        require(wethOut>0 && usdsOut>0,"cycle empty");
        require(finalUSDC>amountIn && pnlRaw>0,"expected apparent arb profit");

        uint256 lpAfterTrade=amm.fairNAVUsd18(externalPrice18);
        require(lpAfterTrade<lpBefore,"LP must lose fair NAV");
        uint256 lpLoss18=lpBefore-lpAfterTrade;
        require(lpLoss18/1e12>uint256(pnlRaw),"LP loss should exceed bot PnL after external costs");
        require(bridge.equityUsd18()==equityBefore,"par bridge changed equity");
        require(usdc.balanceOf(address(this))==usdcBefore+uint256(pnlRaw),"bot PnL accounting");

        uint256 targetQuote=amm.reserveETHS()*targetInternalPrice18/1e18;
        require(targetQuote>amm.reserveUSDS(),"no reset needed");
        uint256 resetMint18=targetQuote-amm.reserveUSDS();
        require(resetMint18>usdsOut,"reset should cost more than one sale output");

        bool reverted;
        try bridge.mintCompensationUSDS(address(amm),resetMint18) { reverted=false; } catch { reverted=true; }
        require(reverted,"unbacked reset unexpectedly allowed");

        uint256 realTopupRaw=bridge.requiredUSDCForAdditionalUSDSMintRaw(resetMint18);
        require(realTopupRaw>0,"expected real topup");
        bridge.fundCanonicalUSDC(realTopupRaw);
        bridge.mintCompensationUSDS(address(amm),resetMint18);

        require(bridge.healthFactorBps()>=15_000,"HF after backed reset");
        require(amm.spotPrice18()==targetInternalPrice18,"price not reset");
        require(amm.fairNAVUsd18(externalPrice18)>=lpBefore,"reset mint already cures LP loss");

        emit Snapshot("cycle",uint256(pnlRaw),lpLoss18/1e12,resetMint18/1e12,realTopupRaw);
        emit Snapshot("hf",hfBefore,bridge.healthFactorBps(),externalPrice18/1e12,targetInternalPrice18/1e18);
    }

    function testExternalDirectionIsInvertedFromOriginalSpec() public view {
        require(targetInternalPrice18>externalPrice18,"test requires internal premium");
    }
}
