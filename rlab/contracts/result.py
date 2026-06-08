from pydantic import BaseModel, ConfigDict

from rlab.results.bundle import ResultBundle


class ResultContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    required_metrics: tuple[str, ...] = ()
    required_figures: tuple[str, ...] = ()
    required_tables: tuple[str, ...] = ()
    required_files: tuple[str, ...] = ()


class ContractViolation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    field: str
    missing: tuple[str, ...]


def validate_bundle(  # noqa: E501
    bundle: ResultBundle, contract: ResultContract
) -> tuple[ContractViolation, ...]:
    violations: list[ContractViolation] = []

    present_metrics = {m.name for m in bundle.metrics}
    missing_metrics = tuple(r for r in contract.required_metrics if r not in present_metrics)
    if missing_metrics:
        violations.append(ContractViolation(field="metrics", missing=missing_metrics))

    present_figures = {f.name for f in bundle.figures}
    missing_figures = tuple(r for r in contract.required_figures if r not in present_figures)
    if missing_figures:
        violations.append(ContractViolation(field="figures", missing=missing_figures))

    present_tables = {t.name for t in bundle.tables}
    missing_tables = tuple(r for r in contract.required_tables if r not in present_tables)
    if missing_tables:
        violations.append(ContractViolation(field="tables", missing=missing_tables))

    return tuple(violations)
