#!/usr/bin/env bash
set -euo pipefail

: "${BASE_RPC_URL:?set BASE_RPC_URL}"
ROOT=$(cd "$(dirname "$0")/.." && pwd)
KEY_FILE=${KEY_FILE:-"$ROOT/.private/mainnet-deployer.key"}
USDC=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913

command -v forge >/dev/null
command -v cast >/dev/null
[[ $(cast chain-id --rpc-url "$BASE_RPC_URL") == 8453 ]] || { echo "not Base mainnet" >&2; exit 1; }
[[ -f "$KEY_FILE" && $(stat -c %a "$KEY_FILE") == 600 ]] || { echo "private key must be chmod 600" >&2; exit 1; }
PRIVATE_KEY=$(tr -d '\r\n' < "$KEY_FILE")
DEPLOYER=$(cast wallet address --private-key "$PRIVATE_KEY")
[[ $(cast code "$USDC" --rpc-url "$BASE_RPC_URL") != 0x ]] || { echo "USDC missing" >&2; exit 1; }
[[ $(cast call "$USDC" 'decimals()(uint8)' --rpc-url "$BASE_RPC_URL") == 6 ]] || { echo "wrong USDC" >&2; exit 1; }
BALANCE=$(cast call "$USDC" 'balanceOf(address)(uint256)' "$DEPLOYER" --rpc-url "$BASE_RPC_URL")
(( BALANCE >= 2000000 )) || { echo "need at least 2 USDC" >&2; exit 1; }

echo "Deploying from $DEPLOYER on Base mainnet (8453)"
DEPLOY_JSON=$(forge create "$ROOT/src/USDSMintSellPPBaseExperiment.sol:USDSMintSellPPBaseExperiment" \
  --rpc-url "$BASE_RPC_URL" --private-key "$PRIVATE_KEY" --broadcast --json \
  --constructor-args "$USDC")
CONTRACT=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["deployedTo"])' <<<"$DEPLOY_JSON")
cast send "$USDC" 'approve(address,uint256)' "$CONTRACT" 2000000 --rpc-url "$BASE_RPC_URL" --private-key "$PRIVATE_KEY"
cast send "$CONTRACT" 'seed(uint256,uint256,uint256)' 1000000000000000000 1000000 1000000 \
  --rpc-url "$BASE_RPC_URL" --private-key "$PRIVATE_KEY"
printf 'contract=%s\ndeployer=%s\n' "$CONTRACT" "$DEPLOYER" | tee "$ROOT/.private/mainnet-deployment.txt"
unset PRIVATE_KEY
