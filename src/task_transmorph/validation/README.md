# Validation

Pure, provider-independent structural validation. This package is the boundary between untrusted provider proposals and the deterministic application/accounting pipeline: it checks structure, identity, coverage, references, effort units, and cross-stage relationships, then returns canonical typed models for downstream consumers.

It does not calculate accounting results, decide whether a transformation is beneficial, allocate effort, score semantic quality, or call a provider. Those responsibilities belong to `domain/accounting.py`, `domain/allocation.py`, `evaluation/`, and `application/` respectively.

Dependency direction: `validation/` → `contracts/` (stage contracts and effort units) and `errors.py`. It is imported by `application/` and re-exported from the top-level `task_transmorph` package. Nothing in `contracts/` or `domain/` imports it.

The public surface is seven functions in `stages.py`. There are no validation classes: inputs are contracts or plain dictionaries, and outputs are the frozen Pydantic models from `task_transmorph.contracts`.

## Directory structure

```text
validation/
├── __init__.py   re-exports the seven validators
└── stages.py     all validators, shared guards, and stage error mapping
```

There are no subpackages and no other modules. All helpers are private to `stages.py`.

## What this package owns

- **Structural integrity** — required fields, duplicate identifiers, contiguous one-based sequence indexes, dependency ordering.
- **Identity** — every downstream stage must match the baseline task ID and name.
- **Coverage** — every subtask, activity, and removed subtask is classified, modeled, or assigned exactly once.
- **References** — every dependency, source subtask, agentic task, and activity reference must resolve.
- **Effort canonicalization** — validate the product rule and normalize compatible units before accounting sees the values.
- **Canonical echo replacement** — downstream stages may echo names and sequence indexes, but the validated baseline always wins.

## What this package does not own

- W0/W1 relationships, ratios, multipliers, or effect classification (`domain/accounting.py`).
- Relative-weight allocation (`domain/allocation.py`).
- Semantic judgment about whether a decomposition is good (`evaluation/`).
- Provider calls, retries, or repair (`application/`).
- Regenerating the baseline. Transformation stages consume the validated decomposition; they never rebuild it.

## Validation order

```text
provider payload
      │
      ▼
validate_operational_decomposition
      │
      ▼
validate_retain_remove_classification
      │
      ▼
validate_agentic_task_synthesis
      │
      ▼
validate_human_agent_activity_model
      │
      ▼
validate_activity_effort_estimation
      │
      ▼
application handoff (support-work resolution → accounting)
```

`validate_stage_chain(operational, classification)` is a convenience for the first two stages only; it does not run the later stages or perform any accounting.

## Function reference

### `validate_operational_decomposition(value)`

Validates the reusable baseline decomposition.

- Subtask IDs must be unique.
- Sequence indexes must be exactly `1..n`.
- A subtask may not depend on itself, may not list duplicate dependencies, may not reference unknown subtasks, and may not depend on a subtask at or after its own position.
- At least one bottom-up baseline estimate is required.
- Relative effort weights must be all present or all absent; partial provider weights are rejected.
- Delegates effort canonicalization to `validate_baseline_effort_estimates`.

Raises `StageValidationError`, `CardinalityError`, `StageDependencyError`, or `UnknownReferenceError`.

### `validate_baseline_effort_estimates(value)`

Validates and canonicalizes bottom-up baseline estimates. Each row describes one subtask relative to one completed parent output, and the canonical product is:

```text
expected_occurrences_per_parent_output × active_effort_per_occurrence
```

- Estimate IDs must be unique and must cover every operational subtask exactly once.
- `active_effort_per_occurrence` must use `TimeBasis.PER_OPERATION`.
- Compatible units are converted to the first estimate's unit before multiplication; incompatible units raise `StageValidationError`.
- A provider-supplied `expected_effort_per_parent_output` is optional, but if present it must equal the computed product.
- The returned model always carries the computed product.

When called directly with an empty estimate collection, this helper returns the input unchanged so intermediate provider/evaluation models can still be inspected. The mandatory-coverage rule is enforced by `validate_operational_decomposition`, which is the canonical entry point.

### `validate_retain_remove_classification(operational, value)`

Validates RETAIN/REMOVE labels against the frozen baseline.

- Every operational subtask appears exactly once; unknown or extra IDs are rejected.
- Task ID and name must match the baseline.
- Sequence indexes may be omitted entirely, but indexed and unindexed rows may not be mixed; when present they must be contiguous and preserve baseline order.
- The baseline is authoritative: `task`, `subtask_name`, and `sequence_index` are rewritten from `operational`, so an echoed provider value cannot redefine identity or ordering.

Raises `IdentityMismatchError`, `CardinalityError`, or `UnknownReferenceError`.

### `validate_agentic_task_synthesis(operational, classification, value)`

Validates agentic-task coverage of REMOVE subtasks.

- Agentic task IDs must be unique.
- Each source list may not contain duplicates and must reference known subtasks.
- A source may not reference a RETAIN subtask.
- Every REMOVE subtask must be assigned exactly once across all agentic tasks.
- Zero REMOVE subtasks require zero agentic tasks.
- The returned model carries the canonical operational task identity.

Raises `CardinalityError`, `StageValidationError`, or `UnknownReferenceError`.

### `validate_human_agent_activity_model(operational, classification, synthesis, value)`

Validates the human-agent activity model and its agentic-task references.

- Activity IDs must be unique.
- Each activity's `agentic_task_ids` may not contain duplicates and must resolve against the completed synthesis.
- Zero agentic tasks require zero human-agent activities.
- The `classification` argument is accepted for stage-signature consistency but is not used; the completed synthesis is authoritative for references.

Raises `CardinalityError` or `UnknownReferenceError`.

### `validate_activity_effort_estimation(operational, activities, value)`

Validates and canonicalizes effort estimates for modeled activities.

- Every modeled activity requires exactly one estimate.
- All estimates must share one unit and time basis.
- The same product rule as baseline effort applies: `expected_occurrences_per_parent_output × active_effort_per_occurrence`.
- A supplied expected product must use the same unit/time basis as effort per occurrence and must equal the computed value.
- The returned model always contains the computed product and the canonical task identity.

Raises `CardinalityError`, `UnknownReferenceError`, or `StageValidationError`.

### `validate_stage_chain(operational, classification)`

Validates the operational decomposition first, then validates the classification against that validated baseline. Returns `(operational, classification)` in canonical form.

This is a two-stage convenience only. It does not validate agentic synthesis, activities, activity effort, or accounting inputs.

## Canonicalization behavior

- **No input mutation.** Validators call `model_copy(update=...)`; the caller's model is left untouched.
- **Dictionaries are parsed.** A `dict` input is passed through `model_validate`; Pydantic `ValidationError` is re-raised as `StageValidationError` naming the contract.
- **Echoed metadata is replaced.** Classification rows are rebuilt from baseline names and indexes; task identity is reset from the operational decomposition at every later stage.
- **Products are materialized.** Both baseline and activity estimates leave validation with a populated `expected_effort_per_parent_output`, even when the provider omitted it.
- **Units are converged, not coerced silently.** Baseline estimates convert to the first estimate's unit; activity estimates must already share one unit and time basis.

Validation never invents semantic content. It only accepts, rejects, or normalizes what a provider supplied.

## Errors

All structural failures derive from `StageValidationError`:

- `StageValidationError` — invalid contract, unit, time basis, or product; also the mapped wrapper for Pydantic failures.
- `StageDependencyError` — self-dependency, duplicate dependencies, or a dependency that does not precede its subtask.
- `IdentityMismatchError` — task identity or classification order does not match the baseline.
- `CardinalityError` — duplicate, missing, or extra IDs; incomplete coverage; inconsistent zero-count cases; malformed sequence indexes.
- `UnknownReferenceError` — a reference to a subtask, agentic task, or activity that does not exist.

Each error message names the offending ID or collection so the application can log or repair precisely.

## Usage

```python
from task_transmorph import (
    StageValidationError,
    validate_operational_decomposition,
    validate_stage_chain,
)

operational = validate_operational_decomposition(provider_payload)

# Validate the classification against the now-canonical baseline.
operational, classification = validate_stage_chain(operational, classification_payload)

try:
    validate_stage_chain(operational, classification_payload)
except StageValidationError as exc:
    # Structural failure: reject or request a provider repair.
    ...
```

Application code normally reaches these validators through `application/_provider_stage.py` (provider-path stages) and `application/staged_pipeline.py` (`validate_stage_chain`). Direct calls are appropriate for tests, replay tools, and custom hosts that already hold typed stage models.

## Notes

- `validate_baseline_effort_estimates` is public through `task_transmorph.validation` and the top-level package, but it is not listed in `stages.__all__`. Import it from either package surface rather than relying on `from ...stages import *`.
- Validation is deterministic and side-effect free: no logging, environment access, filesystem access, or provider SDK imports. It can run with no optional extras installed.
