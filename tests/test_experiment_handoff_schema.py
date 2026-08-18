import json
from pathlib import Path

from usds_federation import USDExperimentResult


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas/usds_experiment_result_v1.schema.json"


def _payload() -> dict:
    result = USDExperimentResult(
        experiment_id="schema-check",
        mode="FORK",
        network="Base",
        fork_block=100,
        reporting_asset="USDC",
        initial_external_capital="2.00",
        minted_usds_notional="0.01",
        sale_proceeds="0.009872",
        restoration_external_cost="0.019862",
        gas_and_external_costs="0.01",
        external_value_added="0.029615",
        closing_usds_liability="0",
        price_restored=True,
        supply_closed=True,
        external_value_evidence_digest="aa" * 32,
        execution_evidence_digest="bb" * 32,
    )
    return result.to_dict()


def test_runtime_emits_exact_declared_top_level_shape() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    payload = _payload()
    assert set(payload) == set(schema["required"])
    assert set(payload) <= set(schema["properties"])
    assert payload["schema"] == "usds.experiment-result/v1"


def test_runtime_keeps_usds_result_research_only_and_noncredentialed() -> None:
    payload = _payload()
    assert payload["classification"] == "RND_ONLY"
    assert payload["accounting_authority"] == "Shtenco/synergy_financial_os"
    assert payload["credential_inputs_allowed"] is False


def test_runtime_output_is_canonical_decimal_text() -> None:
    payload = _payload()
    assert payload["initial_external_capital"] == "2"
    assert payload["closing_usds_liability"] == "0"
    assert payload["external_pnl_candidate"] == "-0.000247"
