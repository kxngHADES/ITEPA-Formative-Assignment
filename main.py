from app.models import Learner, Course, Registration, Assessment, SupportTicket
from app.core import (
    ConfigManager,
    SupportTicketFactory,
    PercentageStrategy,
    PassFailStrategy,
    WeightedStrategy,
)
from app.engine import (
    RegistrationRequest,
    RegistrationProcessingEngine,
    ConcurrentRegistrationProcessingEngine,
)
from app.monitoring import BugzotLogger, PerformanceMonitor


def deliverable1_1():
    print(f'{"=" * 70}')
    print("ENTERPRISE DOMAIN MODEL DEMONSTRATION")
    print(f'{"=" * 70}')

    print("\n\nDOMAIN MODEL OUTPUT")
    print(f'{"=" * 70}\n')

    learner = Learner("Ndaedzo Mudau", "ndaedzo_mudau@ndaedzo.com")
    course = Course("ITEPA3-33", "Enterprise Python Development", capacity=16)
    print(learner)
    print(course)

    reg = learner.register_for_course(course)
    print(reg)

    print("\n")
    assessment = Assessment(reg, raw_score=82)
    print(assessment)
    print(repr(assessment))
    print(reg.status)

    print("\n")
    ticket = SupportTicket(learner, "Login issue", "Cannot access myLMS")
    print(ticket)
    print(learner.support_tickets)


def deliverable1_2():
    print(f'\n\n{"=" * 70}')
    print("DESIGN PATTERN DEMONSTRATION")
    print(f'{"=" * 70}\n')

    print("SINGLETON PATTERN DEMONSTRATION")
    print(f'{"-" * 60}')
    config1 = ConfigManager()
    config2 = ConfigManager()
    print(f"Config 1 ID: {id(config1)}")
    print(f"Config 2 ID: {id(config2)}")
    print(f"Singleton Successful: {'Same Instance' if config1 is config2 else 'Different Instances'}")
    config1.set("pass_mark", 60)
    print(f"Pass mark seen via config2 after updating config1: {config2.get('pass_mark')}")

    print(f"\n\nFACTORY PATTERN DEMONSTRATION")
    print(f'{"-" * 60}')
    learner = Learner("Naledi Khumalo", "naledi@example.com")

    academic_ticket = SupportTicketFactory.create_ticket(
        "academic", learner, "Assignment clarity", "Need clarity on Assignment 2 rubric"
    )
    print(f"Created: {academic_ticket.__class__.__name__}")

    technical_ticket = SupportTicketFactory.create_ticket(
        "technical", learner, "Cannot login", "Password reset link is not arriving", priority="HIGH"
    )
    print(f"Created: {technical_ticket.__class__.__name__}")

    registration_ticket = SupportTicketFactory.create_ticket(
        "registration", learner, "Enrolment query", "Unsure if my registration was confirmed"
    )
    print(f"Created: {registration_ticket.__class__.__name__}")

    print(f"\n\nSTRATEGY PATTERN DEMONSTRATION")
    print(f'{"-" * 60}')
    course = Course("PY701", "Enterprise Python Development", capacity=16)
    reg = learner.register_for_course(course)

    assessment = Assessment(reg, raw_score=82, strategy=PercentageStrategy())
    print(f"Percentage Result: {assessment.get_percentage()}")
    print(f"Classification Result: {assessment.get_classification()}")

    print(f"\nSwapping to PassFailStrategy at runtime:")
    assessment.set_strategy(PassFailStrategy())
    print(f"Classification Result (Pass/Fail strategy): {assessment.get_classification()}")

    print(f"\nSwapping to WeightedStrategy (30% weighting) at runtime:")
    assessment.set_strategy(WeightedStrategy(weight=0.3))
    print(f"Weighted Percentage Result: {assessment.get_percentage()}")


def deliverable2_1():
    print(f'\n\n{"=" * 70}')
    print("REGISTRATION PROCESSING ENGINE DEMONSTRATION")
    print(f'{"=" * 70}\n')

    course = Course("PY701", "Enterprise Python Development", capacity=10)
    engine = RegistrationProcessingEngine()

    requests = []
    for i in range(17):  # 17 requests against a 10-capacity course
        learner = Learner(f"Learner {i + 1}", f"learner{i + 1}@example.com")
        requests.append(RegistrationRequest(learner=learner, course=course))

    summary = engine.process_batch(requests)
    summary.print_report()


def deliverable2_3():
    print(f'\n\n{"=" * 70}')
    print("CONCURRENT REGISTRATION PROCESSING ENGINE DEMONSTRATION")
    print(f'{"=" * 70}\n')

    course = Course("PY702", "Enterprise Python Development (Concurrent)", capacity=10)
    engine = ConcurrentRegistrationProcessingEngine(max_workers=20)

    requests = [
        RegistrationRequest(
            Learner(f"Concurrent Learner {i + 1}", f"concurrent.learner{i + 1}@example.com"),
            course,
        )
        for i in range(17)  # 17 simultaneous requests against a 10-seat course
    ]

    summary = engine.process_batch_concurrent(requests)
    summary.print_report()

    print(f"\nFinal enrolled_count on Course: {course.enrolled_count} "
          f"(capacity: {course.capacity}) - invariant held under concurrent load.")


def deliverable3_1():
    print(f'\n\n{"=" * 70}')
    print("BUGZOT MONITORING SUBSYSTEM DEMONSTRATION")
    print(f'{"=" * 70}\n')

    bugzot = BugzotLogger()
    engine = RegistrationProcessingEngine()

    course = Course("PY703", "Enterprise Python Development (Bugzot)", capacity=5)

    valid_learner = Learner("Anele Dlamini", "anele@example.com")
    duplicate_learner = Learner("Sipho Mokoena", "sipho@example.com")

    scenarios = [
        RegistrationRequest(valid_learner, course),
        RegistrationRequest(duplicate_learner, course),
        RegistrationRequest(duplicate_learner, course),        # duplicate
        RegistrationRequest(None, course),                     # validation failure
        RegistrationRequest(Learner("Lerato Nkosi", "lerato@example.com"), course),
        RegistrationRequest(Learner("Thando Maseko", "thando@example.com"), course),
        RegistrationRequest(Learner("Naledi Khumalo", "naledi.b@example.com"), course),
        RegistrationRequest(Learner("Over Capacity Learner", "overcap@example.com"), course),  # capacity violation
    ]

    for request in scenarios:
        result = engine.process_single(request)
        bugzot.record_from_result(result)

    bugzot.print_log()

    print("EVENT COUNTS BY CATEGORY")
    print("-" * 60)
    for category, count in bugzot.count_by_category().items():
        print(f"{category}: {count}")


def deliverable3_2():
    print(f'\n\n{"=" * 70}')
    print("BUGZOT APPLICATION PERFORMANCE MONITORING DEMONSTRATION")
    print(f'{"=" * 70}\n')

    monitor = PerformanceMonitor()
    engine = RegistrationProcessingEngine()
    course = Course("PY704", "Enterprise Python Development (Performance)", capacity=12)

    for i in range(15):
        learner = Learner(f"Perf Learner {i + 1}", f"perf.learner{i + 1}@example.com")
        request = RegistrationRequest(learner, course)

        with monitor.measure("RegistrationProcessingEngine", "process_single", detail=request.request_id):
            engine.process_single(request)

    monitor.print_report()


def deliverable3_3():
    print(f'\n\n{"=" * 70}')
    print("PERFORMANCE IMPROVEMENT: SEQUENTIAL vs CONCURRENT PROCESSING")
    print(f'{"=" * 70}\n')

    SIMULATED_DELAY = 0.05   # 50ms - representative of a fast external verification call
    NUM_LEARNERS = 30
    NUM_COURSES = 6           # spread across several courses, as would be typical at peak enrolment

    def build_requests(code_prefix):
        courses = [Course(f"{code_prefix}{i}", f"Course {i}", capacity=20) for i in range(NUM_COURSES)]
        requests = []
        for i in range(NUM_LEARNERS):
            learner = Learner(f"{code_prefix} Learner {i + 1}", f"{code_prefix.lower()}.learner{i + 1}@example.com")
            course = courses[i % NUM_COURSES]
            requests.append(RegistrationRequest(learner, course))
        return requests

    monitor = PerformanceMonitor()

    # --- BEFORE: sequential processing ---
    sequential_engine = RegistrationProcessingEngine(simulated_io_delay=SIMULATED_DELAY)
    sequential_requests = build_requests("SEQ")
    with monitor.measure("RegistrationProcessingEngine", "process_batch (sequential)"):
        sequential_summary = sequential_engine.process_batch(sequential_requests)

    # --- AFTER: concurrent processing ---
    concurrent_engine = ConcurrentRegistrationProcessingEngine(max_workers=10, simulated_io_delay=SIMULATED_DELAY)
    concurrent_requests = build_requests("CON")
    with monitor.measure("ConcurrentRegistrationProcessingEngine", "process_batch_concurrent (after fix)"):
        concurrent_summary = concurrent_engine.process_batch_concurrent(concurrent_requests)

    monitor.print_report()

    sequential_ms = monitor.metrics_for(operation="process_batch (sequential)")[0].duration_ms
    concurrent_ms = monitor.metrics_for(operation="process_batch_concurrent (after fix)")[0].duration_ms
    speedup = round(sequential_ms / concurrent_ms, 2) if concurrent_ms > 0 else float("inf")

    print("SUMMARY")
    print("-" * 70)
    print(f"Requests processed: {NUM_LEARNERS} (across {NUM_COURSES} courses)")
    print(f"Simulated I/O delay per request: {SIMULATED_DELAY * 1000:.0f}ms")
    print(f"BEFORE (sequential): {sequential_ms:.2f}ms total, {sequential_summary.success_count} succeeded")
    print(f"AFTER  (concurrent): {concurrent_ms:.2f}ms total, {concurrent_summary.success_count} succeeded")
    print(f"Speedup: {speedup}x")


deliverable1_1()
deliverable1_2()
deliverable2_1()
deliverable2_3()
deliverable3_1()
deliverable3_2()
deliverable3_3()