from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


SCHEMA = "usds.experiment-result/v1"
ZERO = Decimal("0")
HEX = frozenset("0123456789abcdef")
ALLOWED_MODES = frozenset({"SIMULATION", "FORK", "LIVE_OBSERVED"})


class ExperimentInvariantError(ValueError):
    """Raised when a USDS research result is numerically or semantically unsafe."""


def finite_decimal(value: Decimal | int | str, field_name: str) -> Decimal:
    if isinstance(value, bool):
        raise ExperimentInvariantError(f"{field_name} must be a finite decimal")
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ExperimentInvariantError(f"{field_name} must be a finite decimal") from exc
    if not result.is_finite():
        raise ExperimentInvariantError(f"{field_name} must be finite")
    return result


def canonical_decimal_text(value: Decimal | int | str, field_name: str = "value") -> str:
    number = finite_decimal(value, field_name)
    if number == ZERO:
        return "0"
    text = format(number, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _text(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ExperimentInvariantError(f"{field_name} must be text")
    result = value.strip()
    if not result:
        raise ExperimentInvariantError(f"{field_name} is required")
    return result


def _hex64(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    result = _text(value, field_name).lower()
    if len(result) != 64 or any(char not in HEX for char in result):
        raise ExperimentInvariantError(f"{field_name} must be a 64-character hex digest")
    return result


@dataclass(frozen=True)
class USDExperimentResult:
    """Research handoff; never a self-authorizing Financial OS journal entry."""

    experiment_id: str
    mode: str
    network: str
    reporting_asset: str
    initial_external_capital: Decimal
    minted_usds_notional: Decimal
    sale_proceeds: Decimal
    restoration_external_cost: Decimal
    gas_and_external_costs: Decimal
    external_value_added: Decimal
    closing_usds_liability: Decimal
    price_restored: bool
    supply_closed: bool
    external_value_evidence_digest: str | None = None
    execution_evidence_digest: str | None = None
    fork_block: int | None = None
    classification: str = "RND_ONLY"
    accounting_authority: str = "Shtenco/synergy_financial_os"
    credential_inputs_allowed: bool = False

    def __post_init__(self) -> None:
        experiment_id = _text(self.experiment_id, "experiment_id")
        mode = _text(self.mode, "mode").upper()
        network = _text(self.network, "network")
        reporting_asset = _text(self.reporting_asset, "reporting_asset").upper()
        if mode not in ALLOWED_MODES:
            raise ExperimentInvariantError(f"unsupported experiment mode: {mode}")
        if self.classification != "RND_ONLY":
            raise ExperimentInvariantError("USDS experiment result classification must remain RND_ONLY")
        if self.accounting_authority != "Shtenco/synergy_financial_os":
            raise ExperimentInvariantError("Financial OS is the only accounting authority")
        if self.credential_inputs_allowed is not False:
            raise ExperimentInvariantError("experiment handoff must not accept credentials or private keys")
        if not isinstance(self.price_restored, bool) or not isinstance(self.supply_closed, bool):
            raise ExperimentInvariantError("price_restored and supply_closed must be booleans")
        if self.fork_block is not None:
            if isinstance(self.fork_block, bool) or not isinstance(self.fork_block, int) or self.fork_block < 0:
                raise ExperimentInvariantError("fork_block must be a non-negative integer or null")

        numeric_fields = (
            "initial_external_capital",
            "minted_usds_notional",
            "sale_proceeds",
            "restoration_external_cost",
            "gas_and_external_costs",
            "external_value_added",
            "closing_usds_liability",
        )
        for field_name in numeric_fields:
            value = finite_decimal(getattr(self, field_name), field_name)
            if value < ZERO:
                raise ExperimentInvariantError(f"{field_name} must be non-negative")
            object.__setattr__(self, field_name, value)

        external_digest = _hex64(
            self.external_value_evidence_digest, "external_value_evidence_digest"
        )
        execution_digest = _hex64(
            self.execution_evidence_digest, "execution_evidence_digest"
        )
        if self.external_value_added > ZERO and external_digest is None:
            raise ExperimentInvariantError(
                "positive external_value_added requires independent evidence digest"
            )
        if mode in {"FORK", "LIVE_OBSERVED"} and execution_digest is None:
            raise ExperimentInvariantError(
                f"{mode} result requires execution_evidence_digest"
            )
        if mode == "SIMULATION" and self.fork_block is not None:
            raise ExperimentInvariantError("simulation result cannot claim fork_block")

        object.__setattr__(self, "experiment_id", experiment_id)
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "network", network)
        object.__setattr__(self, "reporting_asset", reporting_asset)
        object.__setattr__(self, "external_value_evidence_digest", external_digest)
        object.__setattr__(self, "execution_evidence_digest", execution_digest)

    @property
    def external_pnl_candidate(self) -> Decimal:
        """Unrecognized research candidate; sale proceeds and mint notional are excluded."""

        return (
            self.external_value_added
            - self.restoration_external_cost
            - self.gas_and_external_costs
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": SCHEMA,
            "experiment_id": self.experiment_id,
            "classification": self.classification,
            "mode": self.mode,
            "network": self.network,
            "fork_block": self.fork_block,
            "reporting_asset": self.reporting_asset,
            "initial_external_capital": canonical_decimal_text(
                self.initial_external_capital, "initial_external_capital"
            ),
            "minted_usds_notional": canonical_decimal_text(
                self.minted_usds_notional, "minted_usds_notional"
            ),
            "sale_proceeds": canonical_decimal_text(self.sale_proceeds, "sale_proceeds"),
            "restoration_external_cost": canonical_decimal_text(
                self.restoration_external_cost, "restoration_external_cost"
            ),
            "gas_and_external_costs": canonical_decimal_text(
                self.gas_and_external_costs, "gas_and_external_costs"
            ),
            "external_value_added": canonical_decimal_text(
                self.external_value_added, "external_value_added"
            ),
            "external_pnl_candidate": canonical_decimal_text(
                self.external_pnl_candidate, "external_pnl_candidate"
            ),
            "closing_usds_liability": canonical_decimal_text(
                self.closing_usds_liability, "closing_usds_liability"
            ),
            "price_restored": self.price_restored,
            "supply_closed": self.supply_closed,
            "external_value_evidence_digest": self.external_value_evidence_digest,
            "execution_evidence_digest": self.execution_evidence_digest,
            "accounting_authority": self.accounting_authority,
            "credential_inputs_allowed": self.credential_inputs_allowed,
        }


@dataclass(frozen=True)
class ExperimentReview:
    status: str
    blockers: tuple[str, ...]
    external_pnl_candidate: Decimal
    financial_os_recognition: str = "NOT_PERFORMED"


def review_for_financial_os_handoff(result: USDExperimentResult) -> ExperimentReview:
    """Review research evidence; never recognize profit or post accounting entries."""

    blockers: set[str] = set()
    if result.external_value_added > ZERO and result.external_value_evidence_digest is None:
        blockers.add("EXTERNAL_VALUE_EVIDENCE_MISSING")
    if result.mode in {"FORK", "LIVE_OBSERVED"} and result.execution_evidence_digest is None:
        blockers.add("EXECUTION_EVIDENCE_MISSING")
    if not result.price_restored:
        blockers.add("PRICE_NOT_RESTORED")
    if result.closing_usds_liability != ZERO or not result.supply_closed:
        blockers.add("LIABILITY_NOT_CLOSED")

    status = "HANDOFF_REVIEWABLE" if not blockers else "RND_BLOCKED"
    return ExperimentReview(
        status=status,
        blockers=tuple(sorted(blockers)),
        external_pnl_candidate=result.external_pnl_candidate,
        financial_os_recognition="NOT_PERFORMED",
    )
