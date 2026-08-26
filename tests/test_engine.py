"""
Tests for the Registration Processing Engine (app.engine.processing).

Covers:
    - Sequential processing (Deliverable 2.1): request validation,
      single/batch registration, business rule enforcement, summary
      reporting
    - Concurrent processing and locking (Deliverable 2.3): capacity
      and duplicate-prevention correctness under real thread
      contention, per-course lock behaviour
    - Performance improvement (Deliverable 3.3): simulated I/O delay
      and the measured speedup from concurrent vs sequential processing

Run with:
    python -m unittest tests/test_engine.py -v
"""

import threading
import unittest

from app.engine import (
    RegistrationRequest,
    RegistrationProcessingEngine,
    ConcurrentRegistrationProcessingEngine,
    ProcessingSummary,
)
from app.models import Learner, Course, Registration

RACE_TEST_ITERATIONS = 20


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        Learner._id_counter = 1
        Registration._id_counter = 1

    def learner(self, name="Ndaedzo Mudau", tag="1"):
        return Learner(name, f"{name.lower().replace(' ', '.')}.{tag}@example.com")

    def course(self, code="ITEPA3-33", capacity=10):
        return Course(code, "Enterprise Python", capacity=capacity)


# ---------------------------------------------------------------------------
# Sequential processing (Deliverable 2.1)
# ---------------------------------------------------------------------------

class TestRegistrationRequest(BaseTestCase):
    def test_request_id_is_generated_from_learner_and_course(self):
        learner, course = self.learner(), self.course()
        request = RegistrationRequest(learner, course)
        self.assertEqual(request.request_id, f"{learner.learner_id}->{course.course_code}")

    def test_explicit_request_id_is_preserved(self):
        request = RegistrationRequest(self.learner(), self.course(), request_id="CUSTOM-01")
        self.assertEqual(request.request_id, "CUSTOM-01")


class TestProcessSingleValidation(BaseTestCase):
    def test_none_learner_fails_validation(self):
        result = RegistrationProcessingEngine().process_single(RegistrationRequest(None, self.course()))
        self.assertFalse(result.is_success)
        self.assertIn("learner", result.message.lower())

    def test_none_course_fails_validation(self):
        result = RegistrationProcessingEngine().process_single(RegistrationRequest(self.learner(), None))
        self.assertFalse(result.is_success)
        self.assertIn("course", result.message.lower())

    def test_wrong_type_fails_validation(self):
        engine = RegistrationProcessingEngine()
        result = engine.process_single(RegistrationRequest("not a learner", self.course()))
        self.assertFalse(result.is_success)
        self.assertIn("Learner instance", result.message)


class TestProcessSingleSuccess(BaseTestCase):
    def test_successful_registration_returns_success_result(self):
        engine = RegistrationProcessingEngine()
        result = engine.process_single(RegistrationRequest(self.learner(), self.course()))

        self.assertTrue(result.is_success)
        self.assertIsInstance(result.registration, Registration)
        self.assertEqual(result.registration.status, "CONFIRMED")

    def test_successful_registration_links_learner_and_course(self):
        engine = RegistrationProcessingEngine()
        learner, course = self.learner(), self.course()
        result = engine.process_single(RegistrationRequest(learner, course))

        self.assertIn(result.registration, learner.registrations)
        self.assertIn(result.registration, course.registrations)


class TestSequentialBusinessRuleEnforcement(BaseTestCase):
    def test_duplicate_registration_is_rejected(self):
        engine = RegistrationProcessingEngine()
        learner, course = self.learner(), self.course()

        first = engine.process_single(RegistrationRequest(learner, course))
        second = engine.process_single(RegistrationRequest(learner, course))

        self.assertTrue(first.is_success)
        self.assertFalse(second.is_success)
        self.assertEqual(len(learner.registrations), 1)

    def test_capacity_limit_is_enforced(self):
        engine = RegistrationProcessingEngine()
        course = self.course(capacity=1)

        result_a = engine.process_single(RegistrationRequest(self.learner("A", "a"), course))
        result_b = engine.process_single(RegistrationRequest(self.learner("B", "b"), course))

        self.assertTrue(result_a.is_success)
        self.assertFalse(result_b.is_success)
        self.assertEqual(course.enrolled_count, 1)

    def test_a_failed_request_does_not_stop_batch_processing(self):
        engine = RegistrationProcessingEngine()
        course = self.course(capacity=1)
        other_course = self.course(code="ITEPA3-34")

        engine.process_single(RegistrationRequest(self.learner("A", "a"), course))
        engine.process_single(RegistrationRequest(self.learner("B", "b"), course))  # fails: full
        result_c = engine.process_single(RegistrationRequest(self.learner("C", "c"), other_course))

        self.assertTrue(result_c.is_success)
        self.assertEqual(len(engine.results), 3)


class TestSequentialBatchProcessing(BaseTestCase):
    def test_batch_of_ten_successful_requests(self):
        engine = RegistrationProcessingEngine()
        course = self.course(capacity=20)
        requests = [RegistrationRequest(self.learner(f"L{i}", i), course) for i in range(10)]

        summary = engine.process_batch(requests)

        self.assertEqual(summary.total, 10)
        self.assertEqual(summary.success_count, 10)
        self.assertEqual(summary.success_rate, 100.0)

    def test_batch_with_mixed_outcomes(self):
        engine = RegistrationProcessingEngine()
        course = self.course(capacity=10)
        requests = [RegistrationRequest(self.learner(f"L{i}", i), course) for i in range(17)]

        summary = engine.process_batch(requests)

        self.assertEqual(summary.total, 17)
        self.assertEqual(summary.success_count, 10)
        self.assertEqual(summary.failure_count, 7)

    def test_process_batch_returns_a_processing_summary(self):
        engine = RegistrationProcessingEngine()
        course = self.course(capacity=20)
        requests = [RegistrationRequest(self.learner(f"L{i}", i), course) for i in range(10)]

        self.assertIsInstance(engine.process_batch(requests), ProcessingSummary)


class TestEngineUtilityMethods(BaseTestCase):
    def test_clear_resets_recorded_results(self):
        engine = RegistrationProcessingEngine()
        engine.process_single(RegistrationRequest(self.learner(), self.course()))
        self.assertEqual(len(engine.results), 1)

        engine.clear()
        self.assertEqual(len(engine.results), 0)

    def test_get_summary_reflects_results_so_far(self):
        engine = RegistrationProcessingEngine()
        course = self.course(capacity=20)
        for i in range(5):
            engine.process_single(RegistrationRequest(self.learner(f"L{i}", i), course))

        summary = engine.get_summary()
        self.assertEqual(summary.total, 5)
        self.assertEqual(summary.success_count, 5)


# ---------------------------------------------------------------------------
# Concurrent processing and locking (Deliverable 2.3)
# ---------------------------------------------------------------------------

class TestConcurrentBatchWithinCapacity(BaseTestCase):
    def test_all_requests_succeed_when_within_capacity(self):
        engine = ConcurrentRegistrationProcessingEngine(max_workers=20)
        course = self.course(capacity=20)
        requests = [RegistrationRequest(self.learner(f"L{i}", i), course) for i in range(10)]

        summary = engine.process_batch_concurrent(requests)

        self.assertEqual(summary.success_count, 10)
        self.assertEqual(course.enrolled_count, 10)


class TestConcurrentCapacityEnforcement(BaseTestCase):
    def test_capacity_is_never_exceeded_under_concurrent_load(self):
        for iteration in range(RACE_TEST_ITERATIONS):
            with self.subTest(iteration=iteration):
                engine = ConcurrentRegistrationProcessingEngine(max_workers=20)
                course = self.course(code=f"ITEPA3-{iteration:02d}", capacity=10)
                requests = [
                    RegistrationRequest(self.learner(f"L{i}", f"{iteration}-{i}"), course)
                    for i in range(17)
                ]

                summary = engine.process_batch_concurrent(requests)

                self.assertEqual(summary.success_count, 10)
                self.assertEqual(summary.failure_count, 7)
                self.assertEqual(course.enrolled_count, 10)
                self.assertEqual(len(course.registrations), 10)


class TestConcurrentDuplicatePrevention(BaseTestCase):
    def test_only_one_of_many_concurrent_duplicate_requests_succeeds(self):
        for iteration in range(RACE_TEST_ITERATIONS):
            with self.subTest(iteration=iteration):
                engine = ConcurrentRegistrationProcessingEngine(max_workers=20)
                course = self.course(code=f"ITEPA4-{iteration:02d}", capacity=50)
                learner = self.learner("Duplicate Attempter", iteration)
                requests = [RegistrationRequest(learner, course) for _ in range(20)]

                summary = engine.process_batch_concurrent(requests)

                self.assertEqual(summary.success_count, 1)
                self.assertEqual(summary.failure_count, 19)
                self.assertEqual(len(learner.registrations), 1)
                self.assertEqual(course.enrolled_count, 1)


class TestConcurrentResultsIntegrity(BaseTestCase):
    def test_no_results_are_lost_or_duplicated_under_concurrency(self):
        engine = ConcurrentRegistrationProcessingEngine(max_workers=20)
        course = self.course(capacity=100)
        requests = [RegistrationRequest(self.learner(f"L{i}", i), course) for i in range(50)]

        engine.process_batch_concurrent(requests)

        self.assertEqual(len(engine.results), 50)

    def test_different_courses_process_independently_and_correctly(self):
        engine = ConcurrentRegistrationProcessingEngine(max_workers=20)
        course_a = self.course(code="ITEPA3-33", capacity=1)
        course_b = self.course(code="ITEPA3-34", capacity=1)

        requests = [
            RegistrationRequest(self.learner("A1", "a1"), course_a),
            RegistrationRequest(self.learner("A2", "a2"), course_a),
            RegistrationRequest(self.learner("B1", "b1"), course_b),
            RegistrationRequest(self.learner("B2", "b2"), course_b),
        ]

        summary = engine.process_batch_concurrent(requests)

        self.assertEqual(summary.success_count, 2)
        self.assertEqual(course_a.enrolled_count, 1)
        self.assertEqual(course_b.enrolled_count, 1)


class TestPerCourseLocking(BaseTestCase):
    def test_same_course_code_returns_the_same_lock_object(self):
        engine = ConcurrentRegistrationProcessingEngine()
        self.assertIs(engine._get_course_lock("ITEPA3-33"), engine._get_course_lock("ITEPA3-33"))

    def test_different_course_codes_return_different_lock_objects(self):
        engine = ConcurrentRegistrationProcessingEngine()
        self.assertIsNot(engine._get_course_lock("ITEPA3-33"), engine._get_course_lock("ITEPA3-34"))

    def test_lock_creation_is_itself_thread_safe(self):
        engine = ConcurrentRegistrationProcessingEngine()
        discovered_locks = []
        discovery_lock = threading.Lock()

        def worker():
            lock = engine._get_course_lock("ITEPA9-99")
            with discovery_lock:
                discovered_locks.append(lock)

        threads = [threading.Thread(target=worker) for _ in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertTrue(all(lock is discovered_locks[0] for lock in discovered_locks))


class TestConcurrentEngineStillSupportsSequentialProcessing(BaseTestCase):
    def test_inherited_process_batch_still_works_correctly(self):
        engine = ConcurrentRegistrationProcessingEngine()
        course = self.course(capacity=5)
        requests = [RegistrationRequest(self.learner(f"L{i}", i), course) for i in range(5)]

        summary = engine.process_batch(requests)
        self.assertEqual(summary.success_count, 5)


# ---------------------------------------------------------------------------
# Performance improvement (Deliverable 3.3)
# ---------------------------------------------------------------------------

class TestSimulatedDelayDefaultsToZero(BaseTestCase):
    def test_sequential_and_concurrent_engines_default_to_no_delay(self):
        self.assertEqual(RegistrationProcessingEngine()._simulated_io_delay, 0.0)
        self.assertEqual(ConcurrentRegistrationProcessingEngine()._simulated_io_delay, 0.0)

    def test_zero_delay_batch_completes_near_instantly(self):
        import time as time_module
        engine = RegistrationProcessingEngine()
        course = self.course(capacity=20)
        requests = [RegistrationRequest(self.learner(f"L{i}", i), course) for i in range(10)]

        start = time_module.perf_counter()
        engine.process_batch(requests)
        elapsed_ms = (time_module.perf_counter() - start) * 1000

        self.assertLess(elapsed_ms, 50)


class TestConcurrencyImprovesPerformance(BaseTestCase):
    def test_concurrent_batch_is_faster_than_sequential_with_simulated_io(self):
        import time as time_module

        DELAY = 0.03
        COUNT = 15

        sequential_engine = RegistrationProcessingEngine(simulated_io_delay=DELAY)
        seq_course = self.course(code="ITEPA-SEQ", capacity=100)
        seq_requests = [RegistrationRequest(self.learner(f"S{i}", f"s{i}"), seq_course) for i in range(COUNT)]

        start = time_module.perf_counter()
        sequential_engine.process_batch(seq_requests)
        sequential_ms = (time_module.perf_counter() - start) * 1000

        concurrent_engine = ConcurrentRegistrationProcessingEngine(max_workers=10, simulated_io_delay=DELAY)
        con_course = self.course(code="ITEPA-CON", capacity=100)
        con_requests = [RegistrationRequest(self.learner(f"C{i}", f"c{i}"), con_course) for i in range(COUNT)]

        start = time_module.perf_counter()
        concurrent_engine.process_batch_concurrent(con_requests)
        concurrent_ms = (time_module.perf_counter() - start) * 1000

        
        self.assertLess(concurrent_ms, sequential_ms / 2)

    def test_correctness_is_unaffected_by_simulated_delay(self):
        engine = ConcurrentRegistrationProcessingEngine(max_workers=10, simulated_io_delay=0.01)
        course = self.course(capacity=5)
        requests = [RegistrationRequest(self.learner(f"L{i}", i), course) for i in range(10)]

        summary = engine.process_batch_concurrent(requests)

        self.assertEqual(summary.success_count, 5)
        self.assertEqual(summary.failure_count, 5)
        self.assertEqual(course.enrolled_count, 5)


if __name__ == "__main__":
    unittest.main()