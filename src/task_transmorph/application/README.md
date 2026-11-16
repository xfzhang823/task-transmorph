# Application

The `application/` package orchestrates **task decomposition and AI transformation analysis**. It connects provider-generated judgments to validated, deterministic effort accounting. It does not own vendor SDK calls, persistence, workflow I/O, resource capacity, staffing, or workflow throughput.

A provider can be supplied as an object or selected by a built-in name through the provider factory. Provider responses are treated as untrusted inputs: the application validates them before using them for downstream accounting. Provider construction and tracing may read environment configuration; the canonical arithmetic remains local and deterministic.

## The process at a glance

```text
Human task (e.g., production scheduling)
    |
    v
1. Operational decomposition — decompose_task()
   Provider proposes subtasks, occurrences, and active-effort estimates
   -> validate and evaluate -> derive baseline effort and allocations
    |
    v
Reusable TaskDecomposition (frozen baseline)
    |
    v
2. Transformation decomposition — decompose_transformation()
   Provider classifies retained/removed work and models agentic and
   human-agent activities; application validates the stages
    |
    v
Canonical accounting — domain/accounting
   Baseline versus transformed effort and accounting impact
    |
    v
TransformationDecompositionResult
```

The first stage establishes **what people do today and how much active effort it requires**. The second stage evaluates **how that work changes with AI**. Transformation reuses the accepted baseline rather than asking the provider to invent a new one. The library measures effort per completed parent output, not end-to-end workflow throughput.

## Key concepts

| Term | Meaning |
| --- | --- |
| **Parent output** | One completed unit of the task, such as one approved and released production schedule. All baseline effort is measured relative to this output. |
| **Operational subtask** | A constituent activity required to produce the parent output. |
| **Expected occurrences** | Average number of times a subtask happens per parent output. It may be fractional when a step occurs only some of the time. |
| **Active effort** | Human work time spent on an activity, distinct from elapsed time or waiting. |
| **Baseline / frozen baseline** | The validated pre-transformation subtasks, estimates, and allocations reused unchanged during transformation. |
| **Relative weight** | A subtask's share of total baseline effort. |
| **Allocation** | The normalized, transformation-facing representation of baseline work, optionally carrying compatible absolute effort and provenance. |
| **RETAIN / REMOVE** | Classification of baseline work as retained human work or work removed from the human baseline by transformation. |
| **W0 / W1** | Baseline and post-transformation work measures used by canonical accounting; their precise interpretation depends on the absolute or normalized accounting input. |
| **Support work** | Human work associated with the transformed arrangement, including activities represented through the established support-work categories. |

## Worked example: production scheduling

Suppose the parent output is **one approved and released production schedule**. Two of its operational subtasks have the following provider-estimated inputs:

| Subtask | Expected occurrences per schedule | Active effort per occurrence | Expected effort per schedule |
| --- | ---: | ---: | ---: |
| Assess production resource capacity | 1.00 | 1.00 hour | 1.00 hour |
| Resolve scheduling constraints with production management | 0.35 | 0.75 hour | 0.2625 hour |

The second subtask is expected to arise in 35% of scheduling operations. When it does, it takes 0.75 hours of active effort. Its *average contribution* is therefore `0.35 × 0.75 = 0.2625` hours per completed schedule; this does **not** mean an individual occurrence lasts 0.2625 hours.

In the ten-subtask production-scheduling example, the estimated total is **5.3625 hours of active human effort per schedule**. Assessing capacity contributes `1.00 / 5.3625 ≈ 18.65%`; resolving constraints contributes `0.2625 / 5.3625 ≈ 4.90%`. These shares become normalized baseline allocations for transformation accounting. The values are illustrative provider estimates, not observed measurements or throughput predictions.

## Canonical baseline-effort semantics

For each subtask `i`, the provider supplies expected occurrences, active human effort per occurrence, and supporting rationale and assumptions. The application owns the arithmetic:

```text
expected_effort_i = expected_occurrences_i × active_effort_per_occurrence_i
total_baseline_effort = Σ expected_effort_i
relative_weight_i = expected_effort_i / total_baseline_effort
allocation_weight_i = relative_weight_i / Σ relative_weight
```

Occurrences are dimensionless expected counts per parent output. Active effort, expected subtask effort, and total baseline effort are `EffortQuantity` values with explicit units and time bases; canonical baseline estimates use `per_operation`. Weights and allocation ratios are dimensionless shares, **not** durations or capacity.

`validate_baseline_effort_estimates()` canonicalizes compatible units and materializes expected-effort products. `_prepare_operational()` derives relative weights from those products; provider-supplied relative weights are not authoritative. `_allocate_baseline()` uses `allocate_effort()` to normalize them against a synthetic `W0 = 1.0` parent. A caller-supplied absolute baseline may also produce compatible absolute allocations.

`OperationalSubtask.relative_effort_weight` is the operational-stage projection; `BaselineEffortAllocation.weight_ratio` is the frozen, transformation-facing allocation. They have the same canonical proportions but serve different contracts. Allocations also carry their source and may carry absolute effort.

**Consistency before transformation.** `validate_task_decomposition_consistency()` checks products and totals exactly using `Decimal`, requires both estimate arrays to agree by `subtask_id`, verifies IDs and coverage, and checks relative and allocation ratios with an explicit `1e-9` tolerance for rounded representations. When total effort is zero, normalized shares are undefined, so relative weights and allocations must be absent. This validation runs before provider resolution or transformation stages, including when a host returns a previously serialized decomposition to the Transform API.

These checks establish **mathematical consistency**, not the accuracy of provider/LLM estimates, assumptions, or rationales. Semantic evaluation separately reviews the proposed decomposition's scope and assumptions.

## Public entry points

| Function | Module | Input → output | Calls a provider? |
| --- | --- | --- | --- |
| `decompose_task` | `task_decomposition.py` | Task + provider → `TaskDecomposition` (mandatory bottom-up estimates; optional measured baseline effort) | Yes |
| `decompose_transformation` | `transformation_decomposition.py` | Existing `TaskDecomposition` + explicit accounting input + provider → `TransformationDecompositionResult` | Yes |
| `estimate_transformation` | `normalized_estimation.py` | Existing `TaskDecomposition` + provider → normalized `TransformationDecompositionResult` | Yes |
| `decompose` | `provider_service.py` | Canonical task request + transformation context + provider + explicit accounting → `TransformationDecompositionResult` | Yes |

**Which path to use:** `decompose_task()` followed by `decompose_transformation()` is the intended two-call composition when the host provides explicit `AbsoluteEffortInput` or `NormalizedAccountingInput`. `estimate_transformation()` is an opt-in exploratory/notebook bridge when host-supplied accounting is unavailable: it constructs normalized 100-unit accounting with `W0 = 1.0`, records per-subtask assumptions and rationales, and uses the same accounting handoff. It does not create host-calibrated absolute effort or weaken the explicit-input contract of `decompose_transformation()`.

## Architecture and module responsibilities

Dependency direction: `application/` → `interfaces/` (behavioral protocols) and `contracts/` (data schemas). Concrete providers live in `providers/`; canonical accounting formulas live in `domain/accounting`.

Two kinds of modules belong here:

- **Provider-driven services:** `task_decomposition.py`, `transformation_decomposition.py`, and `provider_service.py` call providers through interfaces, validate their outputs, and orchestrate stages.
- **Provider-independent accounting handoff:** internal `staged_pipeline.py` validates typed stage results and routes them to canonical accounting. It does not implement alternative accounting formulas.

`_provider_stage.py` supplies shared provider-stage helpers: the `provider_id` guard, `call_stage`, and stage-validation wrappers. The canonical transformation provider follows a required sequence: classification, agentic synthesis, human-agent activity modeling, and activity-effort estimation. Built-in OpenAI, Gemini, and DeepSeek providers implement that sequence; external providers must implement the same stage protocol. Incomplete implementations and invalid output fail explicitly. Application APIs accept an optional per-call `model` without mutating provider objects.

### `task_decomposition.py` — build the reusable baseline

`decompose_task()` performs operational decomposition **without transformation context or accounting**:

1. Resolve a provider name or use the supplied provider object; require `TaskDecompositionProvider`.
2. Call `OPERATIONAL_DECOMPOSITION` and structurally validate its output.
3. Run `SemanticEvaluator`; when supported, use bounded targeted repair through `repair_operational_decomposition`, then revalidate and re-evaluate the complete result. Evaluator capability can be provider-default or supplied through `evaluator=`.
4. Require complete bottom-up effort estimates for all accepted subtasks; derive relative weights in `_prepare_operational()`.
5. Normalize the accepted baseline in `_allocate_baseline()`.

Only an accepted decomposition reaches allocation. The result is a reusable `TaskDecomposition`.

### `transformation_decomposition.py` — classify and account the baseline

`decompose_transformation()` consumes an existing `TaskDecomposition` plus explicit `AbsoluteEffortInput` or `NormalizedAccountingInput`. After validating the frozen baseline, it:

1. Requires `TransformationDecompositionProvider` and obtains RETAIN/REMOVE classifications.
2. Validates classification and uses `_apply_baseline_allocation()` to attach existing baseline effort to classified subtasks: `effort` in absolute mode or `baseline_effort_ratio` in normalized mode. The provider does not restate baseline effort.
3. Synthesizes agentic tasks, models human-agent activities, and estimates activity effort.
4. Converts activity estimates to established support-work categories and invokes `_run_staged_pipeline()`.
5. Assembles `TransformationDecompositionResult` from validated stages and canonical accounting impact.

Human-agent activities are **not** independently added to W1; their estimated effort is handled through the existing support-work conversion and accounting boundary.

### `staged_pipeline.py` — validate the accounting handoff

Internal `_run_staged_pipeline()` is a **boundary checker and dispatcher, not a calculator**. W0/W1, gross/net work, and effect calculations come from `domain/accounting`.

1. `validate_stage_chain()` coerces dictionaries to typed models and checks stage consistency, including IDs, classifications, and dependencies.
2. `_validate_effort_handoff()` requires explicit accounting inputs to agree with classified effort (the **must not invent effort** guard).
3. Activity-based support work enters via existing support-work categories.
4. Dispatch to `account_absolute()` or `account_normalized()` with resolved support work.
5. Return canonical accounting impact for assembly into the public result.

**Important invariants:**

- **Explicit effort:** the staged pipeline never infers missing accounting input.
- **Absolute handoff:** classified per-subtask effort is all present or all absent; when present, units agree and RETAIN/REMOVE sums match `retained_human_work` and `gross_removed_work`.
- **Normalized handoff:** baseline ratios (or normalized per-row totals) match `retained_work_ratio` and `gross_removed_work_ratio`.
- **No silent coercion:** inconsistent effort raises `MissingAccountingInputError`; incompatible units or bases raise `IncompatibleEffortUnitError` or `SupportBasisConflictError` as applicable.
- **Host-neutral arithmetic:** given validated inputs, accounting is deterministic; this module validates and routes rather than duplicating formulas.

`_require_matching_units()` ensures classified effort uses a consistent unit and time basis. These handoff checks are separate from the **baseline consistency validator**, which runs before transformation starts.
