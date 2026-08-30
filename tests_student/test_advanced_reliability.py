from datetime import datetime, timedelta, timezone

import pandas as pd

from student_api import (
    column_downstream,
    detect_distribution,
    detect_metric,
    multiwindow_burn,
    rag_embedding_shift,
    validate_orders,
)
from observability.lineage import extract_dbt_dataset_graph


def _order(**overrides):
    now = datetime.now(timezone.utc)
    row = {
        "order_id": 1,
        "customer_id": "C1",
        "amount": 10.0,
        "currency": "USD",
        "status": "completed",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    row.update(overrides)
    return row


def test_type_and_freshness_drift(tmp_path):
    contract = tmp_path / "contract.yml"
    contract.write_text(
        """freshness:\n  column: updated_at\n  max_delay_minutes: 30\n  severity: warning\ncolumns:\n  order_id: {type: integer, required: true, severity: critical}\n  amount: {type: number, required: true, severity: critical}\n  created_at: {type: datetime, required: true, severity: critical}\n  updated_at: {type: datetime, required: true, severity: critical}\n"""
    )
    stale = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    failures = [
        item
        for item in validate_orders(
            pd.DataFrame([_order(order_id=1.5, amount="bad", updated_at=stale)]),
            contract,
        )
        if not item["passed"]
    ]
    assert {item["check"] for item in failures} >= {"type", "freshness"}
    assert all(item["action"] in {"block", "warn"} for item in failures)


def test_context_robustness_and_distribution_shape():
    result = detect_metric(
        70,
        [1000, 1000, 1000],
        context={"same_segment_history": [68, 70, 72, 69, 71]},
    )
    assert result["is_anomaly"] is False
    current = [-2, -2, 2, 2] * 20
    baseline = [-1, -1, 1, 1] * 20
    assert detect_distribution(current, baseline)["is_anomaly"] is True


def test_transitive_column_lineage_and_burn_policy():
    graph = {
        "raw.amount": ["stg.amount"],
        "stg.amount": ["mart.revenue"],
        "mart.revenue": ["dashboard.revenue"],
    }
    assert column_downstream(graph, "raw.amount") == [
        "stg.amount",
        "mart.revenue",
        "dashboard.revenue",
    ]
    assert multiwindow_burn(20, 2)["page"] is False
    assert multiwindow_burn(20, 15)["page"] is True


def test_embedding_norm_shift():
    result = rag_embedding_shift(
        [9.8, 10.0, 10.2], [0.9, 1.0, 1.1, 1.0, 1.05]
    )
    assert result["is_anomaly"] is True


def test_dbt_manifest_lineage_parser(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        '{"child_map":{"model.lab.stg_orders":["model.lab.revenue"]}}'
    )
    assert extract_dbt_dataset_graph(manifest) == {
        "model.lab.stg_orders": ["model.lab.revenue"]
    }
