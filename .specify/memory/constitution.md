<!--
  Sync Impact Report
  ===================
  Version change: N/A → 1.0.0 (initial ratification)
  Modified principles: N/A (initial creation)
  Added sections:
    - Principle I: Code Quality
    - Principle II: Testing Standards
    - Principle III: UX Consistency
    - Principle IV: Performance Requirements
    - Section: Quality Gates
    - Section: Development Workflow
    - Section: Governance
  Removed sections: N/A
  Templates requiring updates:
    - .specify/templates/plan-template.md ✅ no changes needed
      (Constitution Check section already references constitution file)
    - .specify/templates/spec-template.md ✅ no changes needed
      (Success Criteria section accommodates performance and UX metrics)
    - .specify/templates/tasks-template.md ✅ no changes needed
      (Polish phase already includes performance and testing tasks)
  Follow-up TODOs: none
-->

# Cost Analyzer Constitution

## Core Principles

### I. Code Quality

All production code MUST adhere to the following non-negotiable standards:

- Every module MUST have a single, clearly defined responsibility.
  Functions MUST NOT exceed 40 lines; files MUST NOT exceed 400 lines.
  Violations require documented justification in a code comment.
- All public interfaces MUST include type annotations.
  Dynamic typing at module boundaries is prohibited.
- Dead code, unused imports, and commented-out code MUST NOT exist
  in the main branch. CI linting MUST enforce this automatically.
- Magic numbers and string literals MUST be extracted into named
  constants or configuration. Inline literals are permitted only
  for universally obvious values (0, 1, empty string).
- Every function MUST have a clear contract: defined inputs,
  outputs, and error conditions. Silent failures are prohibited;
  errors MUST be surfaced explicitly.

**Rationale**: Cost analysis logic involves financial calculations
where subtle bugs have outsized impact. Strict code quality
reduces defect density and makes the codebase auditable.

### II. Testing Standards

All features MUST meet the following testing requirements before merge:

- Unit test coverage MUST reach a minimum of 80% line coverage
  for all new or modified modules. Critical calculation paths
  (cost aggregation, billing logic) MUST reach 95% coverage.
- Integration tests MUST exist for every external service
  boundary (cloud provider APIs, database queries, file I/O).
  Mocks are permitted for unit tests but integration tests
  MUST exercise real interfaces in CI.
- Every bug fix MUST include a regression test that reproduces
  the original failure before the fix is applied.
- Test names MUST describe the scenario and expected outcome
  (e.g., `test_monthly_cost_with_zero_usage_returns_zero`).
  Generic names like `test_1` are prohibited.
- Tests MUST be deterministic. Flaky tests MUST be quarantined
  and fixed within 5 business days or removed.

**Rationale**: Cost analyzer output directly influences financial
decisions. Incorrect results erode user trust and can cause
real monetary harm. High test coverage is a safety net, not
a vanity metric.

### III. UX Consistency

All user-facing interfaces MUST maintain coherent behavior:

- Terminology MUST be consistent across the entire application.
  A glossary of domain terms (e.g., "cost", "charge", "usage",
  "estimate") MUST be maintained and all UI text MUST conform.
- Error messages MUST be actionable: state what happened, why,
  and what the user can do about it. Technical stack traces
  MUST NOT be exposed to end users.
- Output formats (tables, charts, reports) MUST use consistent
  number formatting, currency symbols, date formats, and
  decimal precision throughout the application.
- Loading states, empty states, and error states MUST be
  handled explicitly in every user-facing view. No view may
  silently show stale or incomplete data.
- All user-visible text MUST support internationalization (i18n)
  readiness. Hard-coded locale-specific strings are prohibited
  in display logic.

**Rationale**: A cost analysis tool is only useful if users can
trust and interpret its output. Inconsistent presentation
creates confusion and undermines confidence in the data.

### IV. Performance Requirements

All features MUST meet the following performance baselines:

- API responses MUST complete within 500ms at the 95th
  percentile under normal load. Queries exceeding 2 seconds
  MUST be optimized or made asynchronous with progress feedback.
- Dashboard and report views MUST render initial meaningful
  content within 1 second. Full data load MUST complete within
  3 seconds for datasets up to 10,000 cost line items.
- Memory consumption MUST NOT exceed 512MB for standard
  operations. Batch processing of large datasets MUST use
  streaming or pagination to avoid unbounded memory growth.
- Database queries MUST use indexes for all filter and sort
  operations. Full table scans on tables exceeding 10,000 rows
  are prohibited without explicit justification.
- Performance regression tests MUST be included for any change
  to critical data paths (cost aggregation, report generation).
  A >10% degradation in p95 latency MUST block the merge.

**Rationale**: Users run cost analysis on large cloud estates.
Slow performance discourages regular usage, which defeats the
purpose of the tool. Performance is a feature, not an afterthought.

## Quality Gates

All pull requests MUST pass the following gates before merge:

- **Lint gate**: Zero warnings from the configured linter.
  Suppressions require a code comment explaining why.
- **Test gate**: All tests pass. Coverage thresholds met
  (80% general, 95% critical paths).
- **Performance gate**: No p95 latency regression >10% on
  benchmarked endpoints.
- **Review gate**: At least one approval from a team member
  who did not author the change.
- **UX gate**: Any user-facing change MUST include before/after
  screenshots or output samples in the PR description.

## Development Workflow

The following workflow MUST be followed for all feature work:

1. **Specification**: Define user stories and acceptance criteria
   before writing code. Use `/speckit.specify` for structured specs.
2. **Planning**: Create an implementation plan that references
   this constitution's principles. Use `/speckit.plan`.
3. **Implementation**: Follow the plan. Commit frequently with
   descriptive messages. Each commit MUST leave the codebase
   in a buildable, testable state.
4. **Review**: Submit PR against the main branch. Address all
   review comments before merge. Do not self-merge.
5. **Validation**: After merge, verify the feature works in the
   integrated environment. Monitor for performance regressions.

## Governance

This constitution is the authoritative source of development
standards for the Cost Analyzer project. In case of conflict
between this document and any other project documentation,
this constitution takes precedence.

- **Amendments**: Any change to this constitution MUST be
  proposed as a PR with a clear rationale. Changes to Core
  Principles require approval from at least two team members.
- **Versioning**: This constitution follows semantic versioning.
  MAJOR for principle removals or incompatible redefinitions,
  MINOR for new principles or material expansions,
  PATCH for clarifications and wording fixes.
- **Compliance**: All code reviews MUST verify adherence to
  these principles. Repeated violations MUST be raised in
  team retrospectives.

**Version**: 1.0.0 | **Ratified**: 2026-03-17 | **Last Amended**: 2026-03-17
