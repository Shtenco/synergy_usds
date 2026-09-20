// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @notice V16 accounting/policy core. It deliberately does not implement a
/// freely transferable token. Protocol-internal buffer units are accounting
/// inventory until an explicitly backed release.
contract PrintMoneyPolicyV16 {
    uint256 public constant WAD = 1e18;

    address public owner;

    uint256 public canonicalAssets;
    uint256 public externalSeniorLiabilities;
    uint256 public escrowedSenior;
    uint256 public qUsds;
    uint256 public qEthsUsd;

    uint256 public targetHfWad = 1.80e18;
    uint256 public hardHfWad   = 1.50e18;
    uint256 public qeCeiling   = 100_000e18;
    uint256 public escrowCeiling = 10_000e18;

    uint256 public realizedCanonicalProfit;
    uint256 public minProfit = 0.001e18;

    error OnlyOwner();
    error Ceiling();
    error HealthFactor();
    error ProfitOrRevert();
    error Amount();

    modifier onlyOwner() {
        if (msg.sender != owner) revert OnlyOwner();
        _;
    }

    constructor(uint256 assets, uint256 liabilities) {
        owner = msg.sender;
        canonicalAssets = assets;
        externalSeniorLiabilities = liabilities;
        if (liabilities != 0 && hfWad() < hardHfWad) revert HealthFactor();
    }

    function hfWad() public view returns (uint256) {
        if (externalSeniorLiabilities == 0) return type(uint256).max;
        return canonicalAssets * WAD / externalSeniorLiabilities;
    }

    function safetySurplus() public view returns (uint256) {
        uint256 req = externalSeniorLiabilities * targetHfWad / WAD;
        return canonicalAssets > req ? canonicalAssets - req : 0;
    }

    // Inverse-Fed style expansion/contraction, but only for junior/virtual QE.
    function expandQeUsds(uint256 amount) external onlyOwner {
        if (qUsds + qEthsUsd + amount > qeCeiling) revert Ceiling();
        qUsds += amount;
    }

    function contractQeUsds(uint256 amount) external onlyOwner {
        if (amount > qUsds) revert Amount();
        qUsds -= amount;
    }

    // Maker/Sky style pre-minted buffer. This is protocol-internal inventory.
    function fill(uint256 amount) external onlyOwner {
        if (escrowedSenior + amount > escrowCeiling) revert Ceiling();
        escrowedSenior += amount;
    }

    function trim(uint256 amount) external onlyOwner {
        if (amount > escrowedSenior) revert Amount();
        escrowedSenior -= amount;
    }

    function maxOneToOneRelease() public view returns (uint256) {
        if (targetHfWad <= WAD) return type(uint256).max;
        return safetySurplus() * WAD / (targetHfWad - WAD);
    }

    /// @notice Releases protocol-internal senior inventory outside the protocol.
    /// Canonical assets received and the new external liability are booked atomically.
    function releaseAgainstCanonical(uint256 amount, uint256 canonicalIn) external onlyOwner {
        if (amount > escrowedSenior) revert Amount();
        uint256 a2 = canonicalAssets + canonicalIn;
        uint256 l2 = externalSeniorLiabilities + amount;
        if (l2 != 0 && a2 * WAD / l2 < targetHfWad) revert HealthFactor();

        escrowedSenior -= amount;
        canonicalAssets = a2;
        externalSeniorLiabilities = l2;
    }

    function redeem(uint256 amount) external onlyOwner {
        if (amount > externalSeniorLiabilities || amount > canonicalAssets) revert Amount();
        canonicalAssets -= amount;
        externalSeniorLiabilities -= amount;
    }

    /// @notice MoneyPrinter-style profit-or-revert gate.
    /// Caller must pass only externally realized revenue/gain and external costs.
    function bookExternalProfit(uint256 grossGain, uint256 externalCost)
        external
        onlyOwner
        returns (uint256 net)
    {
        if (grossGain < externalCost) revert ProfitOrRevert();
        net = grossGain - externalCost;
        if (net < minProfit) revert ProfitOrRevert();
        canonicalAssets += net;
        realizedCanonicalProfit += net;
    }

    function freshSeniorizationCapacity() external view returns (uint256) {
        uint256 c = realizedCanonicalProfit * WAD / targetHfWad;
        return c < escrowedSenior ? c : escrowedSenior;
    }

    function setLimits(
        uint256 targetHf,
        uint256 hardHf,
        uint256 qCap,
        uint256 escrowCap,
        uint256 minProfit_
    ) external onlyOwner {
        if (targetHf < hardHf || hardHf < WAD) revert HealthFactor();
        targetHfWad = targetHf;
        hardHfWad = hardHf;
        qeCeiling = qCap;
        escrowCeiling = escrowCap;
        minProfit = minProfit_;
        if (externalSeniorLiabilities != 0 && hfWad() < hardHfWad) revert HealthFactor();
    }
}
