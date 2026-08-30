#!/usr/bin/env python3
"""Reusable Great Expectations Suite/ValidationDefinition/Checkpoint flow."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    import great_expectations as gx
except ImportError as exc:  # friendlier classroom failure
    raise SystemExit("great_expectations is not installed. Run: pip install -r requirements.txt") from exc


def build_checkpoint(context: gx.DataContext):
    """Build the complete in-memory orders validation flow."""

    # Use unique names so re-running inside an ephemeral context is simple.
    data_source = context.data_sources.add_pandas("orders_pandas")
    asset = data_source.add_dataframe_asset(name="orders_dataframe")
    batch_definition = asset.add_batch_definition_whole_dataframe("whole_orders")
    expectations = [
        gx.expectations.ExpectColumnValuesToNotBeNull(
            column="order_id", severity="critical"
        ),
        gx.expectations.ExpectColumnValuesToBeUnique(
            column="order_id", severity="critical"
        ),
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="amount", min_value=0, severity="critical"
        ),
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="currency", value_set=["USD", "VND"], severity="critical"
        ),
    ]
    suite = context.suites.add(gx.ExpectationSuite(name="orders_contract_suite"))
    # Expectations are added after registration so GX persists each mutation.
    for expectation in expectations:
        suite.add_expectation(expectation)

    validation = context.validation_definitions.add(
        gx.ValidationDefinition(
            name="orders_contract_validation",
            data=batch_definition,
            suite=suite,
        )
    )
    checkpoint = context.checkpoints.add(
        gx.Checkpoint(
            name="orders_contract_checkpoint",
            validation_definitions=[validation],
            actions=[],
        )
    )
    return checkpoint


def main() -> None:
    df = pd.read_csv(ROOT / "data" / "incoming" / "orders.csv")
    context = gx.get_context(mode="ephemeral")
    checkpoint = build_checkpoint(context)
    result = checkpoint.run(batch_parameters={"dataframe": df})
    all_ok = bool(result.success)

    # Local action: critical failures quarantine the complete incoming batch.
    # In production this hook would route to object storage/table partition and
    # notify orchestration; writing under reports keeps the lab fully local.
    action = "continue"
    if not all_ok:
        quarantine = ROOT / "reports" / "quarantine_orders.csv"
        df.to_csv(quarantine, index=False)
        action = f"quarantine:{quarantine.relative_to(ROOT)}"

    print("GX checkpoint result:", "PASS" if all_ok else "FAIL")
    print("Action:", action)


if __name__ == "__main__":
    main()
