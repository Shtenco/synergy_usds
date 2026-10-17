// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

library BasePoolRegistryV11 {
    address internal constant WETH=0x4200000000000000000000000000000000000006;
    address internal constant USDC=0x833589fcd6edb6e08f4c7c32d4f71b54bda02913;

    function pools() internal pure returns(address[8] memory p) {
        p[0]=0x72ab388e2e2f6facef59e3c3fa2c4e29011c2d38;
        p[1]=0xb2cc224c1c9fee385f8ad6a55b4d94e92359dc59;
        p[2]=0x3fe04a59ebd38cf06080a6f60a98d124eb59392a;
        p[3]=0x6c561b446416e1a00e8e93e221854d6ea4171372;
        p[4]=0xdbc6998296caa1652a810dc8d3baf4a8294330f1;
        p[5]=0x41595326aabe6132fc6c7ae71af087a3a9dbc9f6;
        p[6]=0x18b497f71122622557e4634c47a05647ff859f47;
        p[7]=0x3548029694fbb241d45fb24ba0cd9c9d4e745f16;
    }
}
