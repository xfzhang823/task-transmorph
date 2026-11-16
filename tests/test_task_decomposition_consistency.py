from decimal import Decimal

import pytest

from task_transmorph import (
    BaselineEffortAllocation,
    BaselineEffortEstimation,
    BaselineSubtaskEffortEstimate,
    EffortQuantity,
    EffortUnit,
    OperationalDecomposition,
    OperationalSubtask,
    StageValidationError,
    TaskDecomposition,
    TaskReference,
    TimeBasis,
    validate_task_decomposition_consistency,
)
from task_transmorph.application.transformation_decomposition import (
    decompose_transformation,
)
from task_transmorph.contracts.provider import TransformationDecompositionRequest


UNIT = EffortUnit.MINUTES
BASIS = TimeBasis.PER_OPERATION


def make_decomposition(*, zero=False):
    values = (Decimal("0"), Decimal("0")) if zero else (Decimal("0.1"), Decimal("0.2"))
    estimates = tuple(
        BaselineSubtaskEffortEstimate(
            subtask_id=f"sub-{index}",
            expected_occurrences_per_parent_output=(
                Decimal("1.5") if index == 1 and not zero else Decimal("1")
            ),
            active_effort_per_occurrence=EffortQuantity(
                value=value, unit=UNIT, time_basis=BASIS
            ),
            expected_effort_per_parent_output=EffortQuantity(
                value=(
                    value
                    * (Decimal("1.5") if index == 1 and not zero else Decimal("1"))
                ),
                unit=UNIT,
                time_basis=BASIS,
            ),
            rationale="Planning estimate.",
        )
        for index, value in enumerate(values, start=1)
    )
    total_value = sum(
        estimate.expected_effort_per_parent_output.value for estimate in estimates
    )
    total = EffortQuantity(value=total_value, unit=UNIT, time_basis=BASIS)
    subtasks = tuple(
        OperationalSubtask(
            sequence_index=index,
            subtask_id=f"sub-{index}",
            subtask_name=f"Subtask {index}",
            effort_rationale="Planning estimate.",
            relative_effort_weight=(
                None
                if zero
                else estimate.expected_effort_per_parent_output.value / total_value
            ),
        )
        for index, estimate in enumerate(estimates, start=1)
    )
    operational = OperationalDecomposition(
        task=TaskReference(task_name="Example task"),
        operational_subtasks=subtasks,
        baseline_effort_estimates=estimates,
    )
    allocations = (
        ()
        if zero
        else tuple(
            BaselineEffortAllocation(
                subtask_id=estimate.subtask_id,
                weight_ratio=estimate.expected_effort_per_parent_output.value
                / total_value,
                allocation_source="estimated",
            )
            for estimate in estimates
        )
    )
    return TaskDecomposition(
        operational_decomposition=operational,
        baseline_effort_estimation=BaselineEffortEstimation(
            task=operational.task,
            estimates=estimates,
            total_effort_per_parent_output=total,
        ),
        baseline_effort_allocations=allocations,
    )


def test_consistency_accepts_decimal_products_and_rounded_ratios():
    decomposition = make_decomposition()
    rounded = decomposition.operational_decomposition.operational_subtasks[
        0
    ].model_copy(update={"relative_effort_weight": Decimal("0.4285714285")})
    decomposition = decomposition.model_copy(
        update={
            "operational_decomposition": decomposition.operational_decomposition.model_copy(
                update={
                    "operational_subtasks": (
                        rounded,
                        *decomposition.operational_decomposition.operational_subtasks[
                            1:
                        ],
                    )
                }
            ),
            "baseline_effort_allocations": (
                decomposition.baseline_effort_allocations[0].model_copy(
                    update={"weight_ratio": Decimal("0.4285714285")}
                ),
                decomposition.baseline_effort_allocations[1],
            ),
        }
    )

    assert validate_task_decomposition_consistency(decomposition) == decomposition


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("expected_effort_per_parent_output", "does not equal"),
        ("total_effort_per_parent_output", "total effort"),
    ],
)
def test_consistency_rejects_tampered_effort_values(field, message):
    decomposition = make_decomposition()
    if field == "expected_effort_per_parent_output":
        estimate = decomposition.operational_decomposition.baseline_effort_estimates[0]
        bad_estimate = estimate.model_copy(
            update={
                "expected_effort_per_parent_output": estimate.expected_effort_per_parent_output.model_copy(
                    update={"value": Decimal("99")}
                )
            }
        )
        operational = decomposition.operational_decomposition.model_copy(
            update={
                "baseline_effort_estimates": (
                    bad_estimate,
                    *decomposition.operational_decomposition.baseline_effort_estimates[
                        1:
                    ],
                )
            }
        )
        decomposition = decomposition.model_copy(
            update={"operational_decomposition": operational}
        )
    else:
        total = decomposition.baseline_effort_estimation.total_effort_per_parent_output
        decomposition = decomposition.model_copy(
            update={
                "baseline_effort_estimation": decomposition.baseline_effort_estimation.model_copy(
                    update={
                        "total_effort_per_parent_output": total.model_copy(
                            update={"value": Decimal("99")}
                        )
                    }
                )
            }
        )

    with pytest.raises(StageValidationError, match=message):
        validate_task_decomposition_consistency(decomposition)


def test_consistency_rejects_missing_estimate_id_and_tampered_allocation():
    decomposition = make_decomposition()
    with pytest.raises(StageValidationError, match="arrays disagree"):
        validate_task_decomposition_consistency(
            decomposition.model_copy(
                update={
                    "baseline_effort_estimation": decomposition.baseline_effort_estimation.model_copy(
                        update={
                            "estimates": decomposition.baseline_effort_estimation.estimates[
                                :-1
                            ]
                        }
                    )
                }
            )
        )

    allocation = decomposition.baseline_effort_allocations[0].model_copy(
        update={"weight_ratio": Decimal("0.9")}
    )
    with pytest.raises(StageValidationError, match="allocation weight"):
        validate_task_decomposition_consistency(
            decomposition.model_copy(
                update={
                    "baseline_effort_allocations": (
                        allocation,
                        decomposition.baseline_effort_allocations[1],
                    )
                }
            )
        )


def test_zero_total_requires_no_weights_or_allocations():
    decomposition = make_decomposition(zero=True)
    assert validate_task_decomposition_consistency(decomposition) == decomposition

    subtask = decomposition.operational_decomposition.operational_subtasks[
        0
    ].model_copy(update={"relative_effort_weight": Decimal("1")})
    with pytest.raises(StageValidationError, match="zero baseline total"):
        validate_task_decomposition_consistency(
            decomposition.model_copy(
                update={
                    "operational_decomposition": decomposition.operational_decomposition.model_copy(
                        update={
                            "operational_subtasks": (
                                subtask,
                                *decomposition.operational_decomposition.operational_subtasks[
                                    1:
                                ],
                            )
                        }
                    )
                }
            )
        )


def test_transformation_rejects_invalid_baseline_before_provider_resolution():
    decomposition = make_decomposition()
    bad_allocation = decomposition.baseline_effort_allocations[0].model_copy(
        update={"weight_ratio": Decimal("0")}
    )
    invalid = decomposition.model_copy(
        update={
            "baseline_effort_allocations": (
                bad_allocation,
                decomposition.baseline_effort_allocations[1],
            )
        }
    )
    request = TransformationDecompositionRequest(
        task_decomposition=invalid,
        accounting_input={
            "baseline_human_effort": {
                "value": "1",
                "unit": "effort",
                "time_basis": "per_operation",
            },
            "retained_human_work": {
                "value": "1",
                "unit": "effort",
                "time_basis": "per_operation",
            },
            "gross_removed_work": {
                "value": "0",
                "unit": "effort",
                "time_basis": "per_operation",
            },
        },
    )
    with pytest.raises(StageValidationError, match="allocation weight"):
        decompose_transformation(request, object())
