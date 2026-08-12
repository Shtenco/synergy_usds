// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "../src/USDSMintSellPPBaseExperiment.sol";

interface VmBase {
    function envString(string calldata) external returns(string memory);
    function envAddress(string calldata) external returns(address);
    function createSelectFork(string calldata) external returns(uint256);
    function prank(address) external;
    function txGasPrice(uint256) external;
}

contract BaseForkMintSellPPTest {
    VmBase constant vm=VmBase(address(uint160(uint256(keccak256("hevm cheat code")))));
    address constant BASE_USDC=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913;
    IERC20BaseExp usdc;
    USDSMintSellPPBaseExperiment e;
    uint256 constant U=1e6;
    uint256 constant D=1e18;
    event GasMeasured(string action,uint256 gasUsed,uint256 gasPriceWei);

    function setUp() public {
        vm.createSelectFork(vm.envString("BASE_RPC_URL"));
        // Latest accessible BaseScan snapshot was ~0.026 gwei; use 0.03 gwei execution stress.
        // Note: OP-stack L1 data fee is separate and must be added from GasPriceOracle / receipt.
        vm.txGasPrice(0.03 gwei);
        address whale=vm.envAddress("BASE_USDC_WHALE");
        usdc=IERC20BaseExp(BASE_USDC);
        require(address(usdc).code.length>0,"USDC missing");
        vm.prank(whale);
        require(usdc.transfer(address(this),5_000_000*U),"whale fund");
        e=new USDSMintSellPPBaseExperiment(BASE_USDC);
        require(usdc.approve(address(e),type(uint256).max),"approve");
        // $1m actual pool reserve + $1m PP working-capital buffer.
        e.seed(1_000_000*D,1_000_000*U,1_000_000*U);
    }

    function testMintSell1Pct_FinalPP100_ThenX3ValueAdded() public {
        uint256 mintAmt=e.reserveUSDS()/100;
        (uint256 sale,,uint256 topup)=e.quoteMintSell(mintAmt);
        require(topup*10000/sale>20000,"expected ~2x buffer ratio");
        uint256 g0=gasleft();
        e.mintSellRestore(mintAmt,topup);
        emit GasMeasured("mintSellRestore_1pct",g0-gasleft(),tx.gasprice);
        require(e.getPrice()>=999999e12 && e.getPrice()<=1000001e12,"not $1 final PP");
        require(e.productiveUSDC()==sale,"sale proceeds not retained");

        // Synthetic x3 realized value added from a real fork-state USDC holder.
        // This validates accounting/mechanics, NOT that the value engine itself can earn x3.
        uint256 valueAdded=3*sale;
        uint256 bufferBefore=e.ppBufferUSDC();
        uint256 replenish=topup;
        g0=gasleft();
        e.depositRealizedValueAdded(valueAdded,replenish);
        emit GasMeasured("deposit_x3_value_added",g0-gasleft(),tx.gasprice);
        require(e.ppBufferUSDC()>=bufferBefore+topup,"buffer not replenished");
        require(e.cumulativeSurplusUSDC()>0,"no surplus at x3");
        require(usdc.balanceOf(address(e))==e.externalNAVUSDC(),"USDC/accounting mismatch");
    }

    function testTenCycles_PegAndUSDCAccountingRemainSound() public {
        for (uint256 i; i<10; ++i) {
            uint256 mintAmt=e.reserveUSDS()/100;
            (uint256 sale,,uint256 topup)=e.quoteMintSell(mintAmt);
            e.mintSellRestore(mintAmt,topup);
            e.depositRealizedValueAdded(3*sale,topup);

            require(e.getPrice()>=999999e12 && e.getPrice()<=1000001e12,"peg drift");
            require(usdc.balanceOf(address(e))==e.externalNAVUSDC(),"USDC/accounting mismatch");
        }

        require(e.cumulativeMinted()>0,"no mint volume");
        require(e.cumulativeSurplusUSDC()>0,"no cumulative surplus");
    }
}
