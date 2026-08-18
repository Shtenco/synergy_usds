from decimal import Decimal

import pytest

from usds_federation import (
    ExperimentInvariantError,
    USDExperimentResult,
    review_for_financial_os_handoff,
)


def _result(**changes) -> USDExperimentResult:
    kwargs = {
        "experiment_id": "base-fork-001",
        "mode": "FORK",
        "network": "Base",
        "fork_block": 123456,
        "reporting_asset": "USDC",
        "initial_external_capital": "2",
        "minted_usds_notional": "1.681960",
        "sale_proceeds": "1.681960",
        "restoration_external_cost": "3.384097",
        "gas_and_external_costs": "1",
        "external_value_added": "5.045881",
        "closing_usds_liability": "0",
        "price_restored": True,
        "supply_closed": True,
        "external_value_evidence_digest": "aa" * 32,
        "execution_evidence_digest": "bb" * 32,
    }
    kwargs.update(changes)
    return USDExperimentResult(**kwargs)


def test_mint_and_sale_notional_do_not_enter_external_pnl_candidate() -> None:
    result = _result(
        minted_usds_notional="999999",
        sale_proceeds="888888",
        external_value_added="5",
        restoration_external_cost="3",
        gas_and_external_costs="1",
    )
    assert result.external_pnl_candidate == Decimal("1")


def test_no_external_productive_value_means_cost_only_negative_candidate() -> None:
    result = _result(
        external_value_added="0",
        external_value_evidence_digest=None,
        restoration_external_cost="0.4",
        gas_and_external_costs="0.1",
    )
    assert result.external_pnl_candidate == Decimal("-0.5")


def test_positive_external_value_requires_independent_evidence() -> None:
    with pytest.raises(ExperimentInvariantError):
        _result(external_value_added="1", external_value_evidence_digest=None)


def test_fork_result_requires_execution_evidence() -> None:
    with pytest.raises(ExperimentInvariantError):
        _result(execution_evidence_digest=None)


def test_handoff_never_performs_financial_os_profit_recognition() -> None:
    review = review_for_financial_os_handoff(_result())
    assert review.status == "HANDOFF_REVIEWABLE"
    assert review.financial_os_recognition == "NOT_PERFORMED"
    assert review.external_pnl_candidate == Decimal("0.661784")


def test_open_liability_blocks_handoff_even_with_positive_candidate() -> None:
    review = review_for_financial_os_handoff(
        _result(closing_usds_liability="0.1", supply_closed=False)
    )
    assert review.status == "RND_BLOCKED"
    assert "LIABILITY_NOT_CLOSED" in review.blockers


def test_unrestored_price_blocks_handoff() -> None:
    review = review_for_financial_os_handoff(_result(price_restored=False))
    assert review.status == "RND_BLOCKED"
    assert "PRICE_NOT_RESTORED" in review.blockers


@pytest.mark.parametrize("field", [
    "initial_external_capital",
    "minted_usds_notional",
    "sale_proceeds",
    "restoration_external_cost",
    "gas_and_external_costs",
    "external_value_added",
    "closing_usds_liability",
])
@pytest.mark.parametrize("bad", ["NaN", "Infinity", "-Infinity"])
def test_all_financial_inputs_are_finite(field: str, bad: str) -> None:
    with pytest.raises(ExperimentInvariantError):
        _result(**{field: bad})


def test_serialization_uses_unique_decimal_spelling() -> None:
    payload = _result(
        initial_external_capital="2.0000",
        sale_proceeds="1.6800",
        gas_and_external_costs="1.000",
    ).to_dict()
    assert payload["initial_external_capital"] == "2"
    assert payload["sale_proceeds"] == "1.68"
    assert payload["gas_and_external_costs"] == "1"


def test_credentials_or_private_key_authority_cannot_be_enabled() -> None:
    with pytest.raises(ExperimentInvariantError):
        _result(credential_inputs_allowed=True)


def test_usds_repository_cannot_claim_accounting_authority() -> None:
    with pytest.raises(ExperimentInvariantError):
        _result(accounting_authority="Shtenco/usds")
