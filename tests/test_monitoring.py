"""
Functional tests confirming the Bugzot Monitoring Subsystem's logging
precision (app.monitoring).

Covers:
    - BugzotLogger (Deliverable 3.1): direct event logging,
      classification of engine results into the correct category,
      querying/counting, log clearing and reporting
    - PerformanceMonitor (Deliverable 3.2): the measure() context
      manager, manual metric recording, aggregate statistics,
      throughput, report generation

Run with:
    python -m unittest tests/test_monitoring.py -v
"""

import time
import unittest

from app.monitoring import BugzotLogger, EventLevel, EventCategory, PerformanceMonitor, TransactionMetric
from app.engine import RegistrationRequest, RegistrationProcessingEngine
from app.models import Learner, Course, Registration


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        Learner._id_counter = 1
        Registration._id_counter = 1
        self.bugzot = BugzotLogger()
        self.monitor = PerformanceMonitor()

    def learner(self, name="Ndaedzo Mudau", tag="1"):
        return Learner(name, f"{name.lower().replace(' ', '.')}.{tag}@example.com")

    def course(self, code="ITEPA3-33", capacity=10):
        return Course(code, "Enterprise Python", capacity=capacity)


# ---------------------------------------------------------------------------
# BugzotLogger - direct event logging
# ---------------------------------------------------------------------------

class TestDirectEventLogging(BaseTestCase):
    def test_log_success(self):
        event = self.bugzot.log_success("Learner L001 registered successfully.", source="test")
        self.assertEqual(event.level, EventLevel.INFO)
        self.assertEqual(event.category, EventCategory.REGISTRATION_SUCCESS)

    def test_log_validation_failure(self):
        event = self.bugzot.log_validation_failure("Learner L003 has no name.", source="test")
        self.assertEqual(event.level, EventLevel.ERROR)
        self.assertEqual(event.category, EventCategory.VALIDATION_FAILURE)

    def test_log_duplicate_registration(self):
        event = self.bugzot.log_duplicate_registration("Learner L001 is already registered.", source="test")
        self.assertEqual(event.level, EventLevel.WARNING)
        self.assertEqual(event.category, EventCategory.DUPLICATE_REGISTRATION)

    def test_log_capacity_violation(self):
        event = self.bugzot.log_capacity_violation("Course ITEPA3-33 is full.", source="test")
        self.assertEqual(event.level, EventLevel.WARNING)
        self.assertEqual(event.category, EventCategory.CAPACITY_VIOLATION)

    def test_log_application_error(self):
        event = self.bugzot.log_application_error("Unexpected failure.", source="test")
        self.assertEqual(event.level, EventLevel.ERROR)
        self.assertEqual(event.category, EventCategory.APPLICATION_ERROR)

    def test_event_carries_context_for_troubleshooting(self):
        event = self.bugzot.log_capacity_violation(
            "Course ITEPA3-33 is full.", source="test", course_code="ITEPA3-33", learner_id="L005"
        )
        self.assertEqual(event.context["course_code"], "ITEPA3-33")
        self.assertEqual(event.context["learner_id"], "L005")

    def test_format_line_contains_all_key_fields(self):
        line = self.bugzot.log_capacity_violation("Course ITEPA3-33 is full.", source="test").format_line()
        self.assertIn("WARNING", line)
        self.assertIn("Capacity Violation", line)
        self.assertIn("Course ITEPA3-33 is full.", line)


class TestRecordFromRegistrationResult(BaseTestCase):
    def test_successful_result_is_logged_as_success(self):
        engine = RegistrationProcessingEngine()
        result = engine.process_single(RegistrationRequest(self.learner(), self.course()))
        event = self.bugzot.record_from_result(result)
        self.assertEqual(event.category, EventCategory.REGISTRATION_SUCCESS)

    def test_duplicate_result_is_logged_as_duplicate_registration(self):
        engine = RegistrationProcessingEngine()
        learner, course = self.learner(), self.course()

        engine.process_single(RegistrationRequest(learner, course))
        duplicate = engine.process_single(RegistrationRequest(learner, course))
        event = self.bugzot.record_from_result(duplicate)

        self.assertEqual(event.category, EventCategory.DUPLICATE_REGISTRATION)

    def test_capacity_result_is_logged_as_capacity_violation(self):
        engine = RegistrationProcessingEngine()
        course = self.course(capacity=1)

        engine.process_single(RegistrationRequest(self.learner("A", "a"), course))
        capacity_result = engine.process_single(RegistrationRequest(self.learner("B", "b"), course))
        event = self.bugzot.record_from_result(capacity_result)

        self.assertEqual(event.category, EventCategory.CAPACITY_VIOLATION)

    def test_validation_failure_result_is_logged_as_validation_failure(self):
        engine = RegistrationProcessingEngine()
        result = engine.process_single(RegistrationRequest(None, None))
        event = self.bugzot.record_from_result(result)
        self.assertEqual(event.category, EventCategory.VALIDATION_FAILURE)

    def test_processing_a_batch_and_logging_matches_engine_summary(self):
        engine = RegistrationProcessingEngine()
        course = self.course(capacity=10)
        requests = [RegistrationRequest(self.learner(f"L{i}", i), course) for i in range(17)]

        summary = engine.process_batch(requests)
        for result in engine.results:
            self.bugzot.record_from_result(result)

        success_events = self.bugzot.events_by_category(EventCategory.REGISTRATION_SUCCESS)
        capacity_events = self.bugzot.events_by_category(EventCategory.CAPACITY_VIOLATION)

        self.assertEqual(len(success_events), summary.success_count)
        self.assertEqual(len(capacity_events), summary.failure_count)


class TestQueryingAndCounting(BaseTestCase):
    def test_events_by_level_filters_correctly(self):
        self.bugzot.log_success("OK", source="test")
        self.bugzot.log_capacity_violation("Full", source="test")
        self.bugzot.log_validation_failure("Bad input", source="test")

        self.assertEqual(len(self.bugzot.events_by_level(EventLevel.WARNING)), 1)
        self.assertEqual(len(self.bugzot.events_by_level(EventLevel.ERROR)), 1)

    def test_count_by_category(self):
        self.bugzot.log_success("OK 1", source="test")
        self.bugzot.log_success("OK 2", source="test")
        self.bugzot.log_capacity_violation("Full", source="test")

        counts = self.bugzot.count_by_category()
        self.assertEqual(counts[EventCategory.REGISTRATION_SUCCESS.value], 2)
        self.assertEqual(counts[EventCategory.CAPACITY_VIOLATION.value], 1)

    def test_events_property_returns_a_copy_not_internal_reference(self):
        self.bugzot.log_success("OK", source="test")
        snapshot = self.bugzot.events
        snapshot.append("tampered")
        self.assertEqual(len(self.bugzot.events), 1)


class TestClearAndReportingBugzot(BaseTestCase):
    def test_clear_removes_all_recorded_events(self):
        self.bugzot.log_success("OK", source="test")
        self.bugzot.clear()
        self.assertEqual(len(self.bugzot.events), 0)

    def test_repr_shows_event_count(self):
        self.bugzot.log_success("OK", source="test")
        self.assertIn("events=1", repr(self.bugzot))


# ---------------------------------------------------------------------------
# PerformanceMonitor
# ---------------------------------------------------------------------------

class TestMeasureContextManager(BaseTestCase):
    def test_measure_records_a_metric_with_positive_duration(self):
        with self.monitor.measure("TestComponent", "sleep_op"):
            time.sleep(0.01)

        self.assertEqual(self.monitor.transaction_count, 1)
        self.assertGreater(self.monitor.metrics[0].duration_ms, 0)

    def test_measure_marks_success_true_when_no_exception(self):
        with self.monitor.measure("TestComponent", "ok_op"):
            pass
        self.assertTrue(self.monitor.metrics[0].success)

    def test_measure_marks_success_false_and_still_records_on_exception(self):
        with self.assertRaises(ValueError):
            with self.monitor.measure("TestComponent", "failing_op"):
                raise ValueError("boom")

        self.assertEqual(self.monitor.transaction_count, 1)
        self.assertFalse(self.monitor.metrics[0].success)


class TestRecordManual(BaseTestCase):
    def test_record_manual_creates_metric_with_given_values(self):
        metric = self.monitor.record_manual("BatchRunner", "process_batch", duration_ms=42.5, success=True)
        self.assertIsInstance(metric, TransactionMetric)
        self.assertEqual(metric.duration_ms, 42.5)


class TestAggregateStatistics(BaseTestCase):
    def test_average_min_max_duration(self):
        self.monitor.record_manual("Engine", "op", duration_ms=10)
        self.monitor.record_manual("Engine", "op", duration_ms=20)
        self.monitor.record_manual("Engine", "op", duration_ms=30)

        self.assertEqual(self.monitor.average_duration_ms(), 20.0)
        self.assertEqual(self.monitor.min_duration_ms(), 10)
        self.assertEqual(self.monitor.max_duration_ms(), 30)

    def test_success_rate_calculation(self):
        self.monitor.record_manual("Engine", "op", duration_ms=1, success=True)
        self.monitor.record_manual("Engine", "op", duration_ms=1, success=True)
        self.monitor.record_manual("Engine", "op", duration_ms=1, success=False)
        self.monitor.record_manual("Engine", "op", duration_ms=1, success=False)

        self.assertEqual(self.monitor.success_rate(), 50.0)

    def test_filtering_by_component(self):
        self.monitor.record_manual("EngineA", "op", duration_ms=10)
        self.monitor.record_manual("EngineB", "op", duration_ms=100)

        self.assertEqual(self.monitor.average_duration_ms(component="EngineA"), 10)
        self.assertEqual(self.monitor.average_duration_ms(component="EngineB"), 100)


class TestReportGeneration(BaseTestCase):
    def test_report_contains_top_level_totals_and_component_breakdown(self):
        self.monitor.record_manual("EngineA", "op", duration_ms=10, success=True)
        self.monitor.record_manual("EngineB", "op", duration_ms=100, success=False)

        report = self.monitor.generate_report()

        self.assertEqual(report["total_transactions"], 2)
        self.assertIn("EngineA", report["components"])
        self.assertIn("EngineB", report["components"])

    def test_print_report_does_not_raise(self):
        self.monitor.record_manual("Engine", "op", duration_ms=10)
        try:
            self.monitor.print_report()
        except Exception as e:
            self.fail(f"print_report() raised unexpectedly: {e}")


class TestIntegrationWithRegistrationEngine(BaseTestCase):
    def test_measuring_a_batch_of_process_single_calls(self):
        engine = RegistrationProcessingEngine()
        course = self.course(capacity=20)

        for i in range(10):
            request = RegistrationRequest(self.learner(f"L{i}", i), course)
            with self.monitor.measure("RegistrationProcessingEngine", "process_single", detail=request.request_id):
                engine.process_single(request)

        self.assertEqual(self.monitor.transaction_count, 10)
        self.assertEqual(self.monitor.success_rate(component="RegistrationProcessingEngine"), 100.0)


if __name__ == "__main__":
    unittest.main()