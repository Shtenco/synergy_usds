// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "../src/BasePoolRegistryV11.sol";

interface VmV11 {
    function envString(string calldata) external returns(string memory);
    function createSelectFork(string calldata) external returns(uint256);
}
interface IERC20ViewV11 { function balanceOf(address) external view returns(uint256); }

contract BaseForkV11Test {
    VmV11 constant vm=VmV11(address(uint160(uint256(keccak256("hevm cheat code")))));
    IERC20ViewV11 constant weth=IERC20ViewV11(0x4200000000000000000000000000000000000006);
    IERC20ViewV11 constant usdc=IERC20ViewV11(0x833589fcd6edb6e08f4c7c32d4f71b54bda02913);

    function setUp() public {
        vm.createSelectFork(vm.envString("BASE_RPC_URL"));
        require(block.chainid==8453,"not Base");
    }

    function testEightPoolContractsExist() public view {
        address[8] memory p=BasePoolRegistryV11.pools();
        for(uint256 i;i<p.length;i++) require(p[i].code.length>0,"pool missing");
    }

    function testDeepUniswapPoolIsHugeRelativeToTenDollars() public view {
        address pool=0x6c561b446416e1a00e8e93e221854d6ea4171372;
        uint256 wb=weth.balanceOf(pool);
        uint256 ub=usdc.balanceOf(pool);
        require(wb>1000 ether,"WETH depth");
        require(ub>1_000_000e6,"USDC depth");
        require(10e6*1_000_000 < ub,"$10 not dust");
    }

    function testEveryRegisteredPoolHoldsWethOrUsdc() public view {
        address[8] memory p=BasePoolRegistryV11.pools();
        for(uint256 i;i<p.length;i++) {
            require(weth.balanceOf(p[i])>0 || usdc.balanceOf(p[i])>0,"empty pool");
        }
    }
}
