# ITEPA3-33 — Enterprise Python Practical Assignment

**Module:** ITEPA3-33 (Enterprise Python Development)
**Campus:** Pretoria — Faculty of Information Technology
**Lecturer:** Tariro Bonyongwa
**Student:** Ndaedzo Mudau (MD.2022.G4C7J5)
**Submission date:** 26/08/2026

This repository contains the full practical assignment: an enterprise-style learner
management system ("myLMS") built incrementally across five deliverables — a domain
model, design patterns, a registration processing engine, an application monitoring
subsystem (Bugzot), UI mockups, automated testing/profiling, and a microservices
readiness assessment.

## Project layout

```
app/
├── models/        # Domain model: Learner, Course, Registration, Assessment, SupportTicket
├── core/          # Design patterns: ConfigManager (Singleton), SupportTicketFactory (Factory),
│                  # AssessmentStrategy (Strategy)
├── engine/        # RegistrationProcessingEngine (sequential + concurrent/threaded)
└── monitoring/     # Bugzot event logger + PerformanceMonitor (APM)

tests/             # Unit tests + cProfile-based profiling script
main.py            # Runs the deliverable demonstrations end-to-end
docs/              # Assignment PDF + microservices architecture diagram
```

## Deliverable 1 — Domain Model & Design Patterns

**1.1 Domain model** (`app/models/*`): `Learner`, `Course`, `Registration`, `Assessment`
and `SupportTicket`, wired together so a `Learner` registers for a `Course`, producing a
`Registration` that can carry an `Assessment` or raise a `SupportTicket`. Validated with
18 unit tests.

**1.2 Design patterns** (`app/core/*`), 31 unit tests:
- **Singleton — `ConfigManager`**: one shared source of truth (e.g. `pass_mark`,
  `default_course_capacity`) for every subsystem, avoiding config drift between modules.
- **Factory — `SupportTicketFactory`**: creates the correct ticket subclass from a string
  key (e.g. `"technical"`), so calling code never touches ticket subclasses directly and
  new categories can be registered at runtime via `register_ticket_type()`.
- **Strategy — `AssessmentCalculator`**: swaps grading rules (`PercentageStrategy`,
  `WeightedStrategy`, pass/fail) at runtime via `set_strategy()` without rebuilding the
  `Assessment` object.

## Deliverable 2 — Registration Processing Engine

- **2.1 Registration engine**: processes batches of registration requests, enforcing
  course capacity and rejecting duplicates, with a full success/failure summary report.
- **2.2 Scalable data modelling**: registrations are stored as plain Python lists of
  `@dataclass` request/result objects rather than indexed dictionaries. This keeps
  insertion order (needed for the audit trail) and is justified as sufficient at the
  current (hundreds–thousands of rows) scale; lookup logic is isolated behind methods
  like `has_registration_for()` and `is_full` so the underlying structure can be swapped
  later without touching the engine.
- **2.3 Concurrent request processing**: a threaded version of the engine using
  per-course locks, so concurrent registrations can't oversell a course's capacity.

## Deliverable 3 — Bugzot Monitoring & Performance

- **3.1 Bugzot monitoring subsystem**: structured event logging (INFO/WARNING/ERROR)
  for registration successes, duplicates, validation failures and capacity violations.
- **3.2 Application Performance Monitoring**: a `PerformanceMonitor` records per-component
  transaction counts, average/min/max duration, success rate and throughput.
- **3.3 Performance improvement**: demonstrates that `process_batch()` is I/O-bound (each
  registration simulates an external call). Because Python's GIL releases during I/O
  waits, the multithreaded engine achieves a **~244x speedup** over the sequential engine
  for the same 30 requests with 50ms simulated latency, with no change to correctness.

## Deliverable 4 — UI Design & Evaluation

Mockups and design rationale for four screens (Learner Registration, Course Management,
Support Ticket Creation, Report Viewing), each mapped directly to validation rules and
data already present in the domain model (e.g. `EMAIL_REGEX`, `is_full`, `VALID_PRIORITIES`),
plus an evaluation of strengths, gaps (e.g. no duplicate course-code check, no async
inline validation) and proposed fixes.

## Deliverable 5 — Testing, Profiling & Microservices Readiness

- **5.1 Automated testing**: full unit test suite across models, patterns, the
  processing engine and the monitoring subsystem.
- **5.2 Application profiling** (`tests/profile_application.py`): `cProfile` confirms the
  sequential engine spends ~99% of runtime in simulated I/O wait (confirming it's
  I/O-bound, not CPU-bound). It also shows a limitation of `cProfile` under threads — it
  only captures the main thread, so `time.perf_counter` (used in 3.3) is the accurate
  measure of concurrent wall-clock time.
- **5.3 Microservices readiness assessment**: see below.

## Microservices Readiness Assessment (Deliverable 5.3)

The monolith is assessed for its readiness to be decomposed into independently
deployable services.

### Candidate services & responsibilities

| Service | Responsibility |
|---|---|
| **Learner** | Owns learner identity/profile exclusively; other services hold only a reference. |
| **Course** | Sole owner of course data and the "is this course full?" rule (the same per-course lock from 2.3, now enforced at the service boundary instead of the thread boundary). |
| **Registration** | Orchestrator only — owns no data itself; calls Learner and Course to validate a request and records the outcome. Maps directly onto the sequential vs. concurrent engine split already built. |
| **Assessment** | Stateless scoring service (registration ID + raw score + strategy in, percentage/classification out) — trivially horizontally scalable behind a load balancer. |
| **Support Ticket** | Builds the correct ticket type from a category string using the existing Factory logic and manages ticket status transitions. |
| **Configuration** | Replaces the in-process `ConfigManager` singleton (which has no meaning across process boundaries) with a shared config service or environment-based store, keeping one source of truth without relying on object identity. |
| **Monitoring (Bugzot)** | Observability layer that every other service reports to, but nothing depends on — the system keeps working if it goes down. |

### Service communication

- **Synchronous (HTTP)**: used where an immediate answer blocks the caller — e.g.
  Registration → Course to check capacity before enrolling (the networked equivalent of
  the direct method call used in the monolith).
- **Asynchronous (message broker, e.g. Kafka)**: used where the caller must never be
  slowed down or failed by the receiver — e.g. Registration emitting events to Monitoring,
  mirroring how the engine today has no awareness that Bugzot exists.

### Testing & tracing requirements

- Unit tests stay the same (validation, strategies, ticket creation), now easier to run
  in isolation without importing the whole application.
- **Contract testing** becomes necessary, since a renamed field or changed status code
  between services can no longer be caught by Python crashing at import time.
- **End-to-end integration tests** cover the full Registration → Learner → Course path in
  a test environment.
- **Distributed tracing**: `RegistrationRequest.request_id` is reused as a correlation ID,
  passed as an HTTP header / event attribute on every downstream call, enabling tools like
  Jaeger or Zipkin to reconstruct a request's path across services and feed that data into
  Bugzot.

### Independence

Learner, Course, Support Ticket, Monitoring and Configuration can all operate
independently. Assessment can run its (stateless) scoring logic independently, but
linking a score to a registration depends on the Registration service having already run.

### Architecture diagram

![Microservices architecture diagram](docs/ITEPA3-33%20Formative%20Assignment%20Diagram%205.3.png)

*Client → API Gateway → Core Business Services (Learner, Course, Registration, Assessment,
Support Ticket), with Config and Bugzot Monitoring as shared services, each business
service backed by its own database/store.*

## Running the project

```bash
python main.py                        # runs the deliverable demonstrations
python -m unittest discover tests -v  # runs the full test suite
python tests/profile_application.py   # runs the cProfile sequential/concurrent profiling
```

## AI Disclosure

NotebookLM (Gemini) was used to help derive a folder structure matching the project
overview and to locate learning material (YouTube videos) on the required design
patterns and domain modelling concepts. Output was verified by cross-checking the
suggested folder structure against each deliverable's actual requirements and by
watching and validating the referenced videos. Full disclosure and bibliography are in
the assignment PDF (`docs/ITEPA3-33 Practical Assignment Pretoria MD.2022.G4C7J5.pdf`).
