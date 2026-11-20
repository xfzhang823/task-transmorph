import pytest
from test_task_transformation_boundaries import TASK, operational

from task_transmorph import (
    ClassifiedSubtask,
    RetainRemoveClassification,
    TaskReference,
    TransformationClassification,
)
from task_transmorph.errors import UnknownReferenceError
from task_transmorph.validation import validate_retain_remove_classification


def _classification(task: TaskReference, *subtask_ids: str):
    return RetainRemoveClassification(
        task=task,
        classified_subtasks=tuple(
            ClassifiedSubtask(
                subtask_id=subtask_id,
                classification=TransformationClassification.RETAIN,
            )
            for subtask_id in subtask_ids
        ),
    )


def test_classification_attaches_frozen_operational_task_identity() -> None:
    output = validate_retain_remove_classification(
        operational(),
        _classification(
            TaskReference(task_id="provider-task", task_name="Provider task"),
            "sub-1",
            "sub-2",
            "sub-3",
        ),
    )

    assert output.task == TASK


def test_identity_attachment_does_not_repair_unknown_subtask_references() -> None:
    with pytest.raises(UnknownReferenceError, match="unknown classified subtasks"):
        validate_retain_remove_classification(
            operational(),
            _classification(
                TaskReference(task_id="provider-task", task_name="Provider task"),
                "sub-1",
                "sub-2",
                "sub-3",
                "unknown-subtask",
            ),
        )
