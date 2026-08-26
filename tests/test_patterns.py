"""
Unit tests validating the Singleton, Factory, and Strategy design
patterns implemented in app.core (Deliverable 1.2).

Covers:
    - Singleton: ConfigManager
    - Factory: SupportTicketFactory + ticket subclasses
    - Strategy: PercentageStrategy, PassFailStrategy, WeightedStrategy,
      AssessmentCalculator, and their integration into Assessment

Run with:
    python -m unittest tests/test_patterns.py -v
"""

import unittest

from app.core import (
    ConfigManager,
    SupportTicketFactory,
    AcademicTicket,
    TechnicalTicket,
    RegistrationTicket,
    AssessmentStrategy,
    PercentageStrategy,
    PassFailStrategy,
    WeightedStrategy,
    AssessmentCalculator,
)
from app.models import Learner, Course, Registration, Assessment, SupportTicket


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        Learner._id_counter = 1
        Registration._id_counter = 1
        SupportTicket._id_count = 1
        ConfigManager.reset()
        self._original_ticket_types = dict(SupportTicketFactory._ticket_types)

    def tearDown(self):
        ConfigManager.reset()
        SupportTicketFactory._ticket_types = self._original_ticket_types

    def learner(self, name="Ndaedzo Mudau", tag="1"):
        return Learner(name, f"{name.lower().replace(' ', '.')}.{tag}@example.com")

    def course(self, code="ITEPA3-33", capacity=20):
        return Course(code, "Enterprise Python", capacity=capacity)

    def registration(self):
        return self.learner().register_for_course(self.course())


# -------------------------
# Singleton - ConfigManager
# ------------------------

class TestConfigManagerSingleton(BaseTestCase):
    def test_two_instances_are_the_same_object(self):
        config1, config2 = ConfigManager(), ConfigManager()
        self.assertIs(config1, config2)

    def test_settings_are_shared_across_all_references(self):
        config1, config2 = ConfigManager(), ConfigManager()
        config1.set("pass_mark", 60)
        self.assertEqual(config2.get("pass_mark"), 60)

    def test_instance_is_shared_in_different_scopes(self):
        def get_a():
            return ConfigManager()

        def get_b():
            return ConfigManager()

        self.assertIs(get_a(), get_b())

    def test_default_settings_present(self):
        config = ConfigManager()
        self.assertEqual(config.get("pass_mark"), 50)
        self.assertEqual(config.get("distinction_mark"), 75)

    def test_get_missing_key_returns_default(self):
        config = ConfigManager()
        self.assertIsNone(config.get("does_not_exist"))
        self.assertEqual(config.get("does_not_exist", "fallback"), "fallback")

    def test_all_settings_returns_a_copy_not_a_reference(self):
        config = ConfigManager()
        snapshot = config.all_settings()
        snapshot["pass_mark"] = 999
        self.assertEqual(config.get("pass_mark"), 50)

    def test_reset_creates_a_genuinely_new_instance(self):
        config1 = ConfigManager()
        config1.set("pass_mark", 99)
        ConfigManager.reset()
        config2 = ConfigManager()
        self.assertIsNot(config1, config2)
        self.assertEqual(config2.get("pass_mark"), 50)


# ----------------------------
# Factory - SupportTicketFactory
# ------------------------------

class TestSupportTicketFactory(BaseTestCase):
    def test_creates_academic_ticket(self):
        ticket = SupportTicketFactory.create_ticket(
            "academic", self.learner(), "Rubric query", "Need clarity on marking rubric"
        )
        self.assertIsInstance(ticket, AcademicTicket)
        self.assertEqual(ticket.category, "Academic")

    def test_creates_technical_ticket(self):
        ticket = SupportTicketFactory.create_ticket(
            "technical", self.learner(), "Login issue", "Cannot access portal", priority="HIGH"
        )
        self.assertIsInstance(ticket, TechnicalTicket)
        self.assertEqual(ticket.priority, "HIGH")

    def test_creates_registration_ticket(self):
        ticket = SupportTicketFactory.create_ticket(
            "registration", self.learner(), "Enrolment query", "Unsure if registered"
        )
        self.assertIsInstance(ticket, RegistrationTicket)

    def test_factory_call_is_case_and_whitespace_insensitive(self):
        ticket = SupportTicketFactory.create_ticket("  ACADEMIC  ", self.learner(), "Subject", "Description")
        self.assertIsInstance(ticket, AcademicTicket)

    def test_unknown_ticket_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            SupportTicketFactory.create_ticket("billing", self.learner(), "Subject", "Description")

    def test_created_ticket_is_registered_with_the_learner(self):
        learner = self.learner()
        ticket = SupportTicketFactory.create_ticket("technical", learner, "Login issue", "Cannot access portal")
        self.assertIn(ticket, learner.support_tickets)

    def test_ticket_ids_stay_sequential_across_different_types(self):
        learner = self.learner()
        t1 = SupportTicketFactory.create_ticket("academic", learner, "S1", "D1")
        t2 = SupportTicketFactory.create_ticket("technical", learner, "S2", "D2")
        t3 = SupportTicketFactory.create_ticket("registration", learner, "S3", "D3")
        self.assertEqual([t1.ticket_id, t2.ticket_id, t3.ticket_id], ["T0001", "T0002", "T0003"])

    def test_register_new_ticket_type_at_runtime(self):
        class BillingTicket(SupportTicket):
            CATEGORY = "Billing"

            def __init__(self, learner, subject, description, priority="MEDIUM"):
                super().__init__(learner, subject, description, priority)
                self.category = self.CATEGORY

        SupportTicketFactory.register_ticket_type("billing", BillingTicket)
        ticket = SupportTicketFactory.create_ticket("billing", self.learner(), "Invoice query", "Need a copy")

        self.assertIsInstance(ticket, BillingTicket)
        self.assertIn("billing", SupportTicketFactory.available_types())

    def test_register_ticket_type_rejects_non_support_ticket_subclass(self):
        with self.assertRaises(TypeError):
            SupportTicketFactory.register_ticket_type("bogus", int)


# -----------------------------
# Strategy - individual strategies
# --------------------------------

class TestAssessmentStrategyAbstract(BaseTestCase):
    def test_cannot_instantiate_abstract_strategy_directly(self):
        with self.assertRaises(TypeError):
            AssessmentStrategy()


class TestPercentageStrategy(BaseTestCase):
    def test_calculation_matches_the_domain_model_default(self):
        result = PercentageStrategy().calculate(41, 50)
        self.assertEqual(result, {"percentage": 82.0, "classification": "Distinction"})

    def test_classification_boundaries(self):
        cases = [(75, "Distinction"), (74, "pass"), (50, "pass"), (49, "Fail"), (0, "Fail")]
        for raw_score, expected in cases:
            with self.subTest(raw_score=raw_score):
                self.assertEqual(PercentageStrategy().calculate(raw_score, 100)["classification"], expected)


class TestPassFailStrategy(BaseTestCase):
    def test_binary_classification(self):
        cases = [(100, "Pass"), (50, "Pass"), (49, "Fail"), (0, "Fail")]
        for raw_score, expected in cases:
            with self.subTest(raw_score=raw_score):
                self.assertEqual(PassFailStrategy().calculate(raw_score, 100)["classification"], expected)


class TestWeightedStrategy(BaseTestCase):
    def test_weighted_percentage_calculation(self):
        self.assertEqual(WeightedStrategy(weight=0.3).calculate(82, 100)["percentage"], 24.6)

    def test_classification_uses_raw_score_not_weighted(self):
        self.assertEqual(WeightedStrategy(weight=0.3).calculate(82, 100)["classification"], "Distinction")

    def test_weight_of_one_equals_unweighted_percentage(self):
        self.assertEqual(WeightedStrategy(weight=1.0).calculate(82, 100)["percentage"], 82.0)

    def test_invalid_weight_raises_value_error(self):
        for bad_weight in [0, -0.5, 1.1, 2]:
            with self.subTest(weight=bad_weight):
                with self.assertRaises(ValueError):
                    WeightedStrategy(weight=bad_weight)


class TestAssessmentCalculator(BaseTestCase):
    def test_defaults_to_percentage_strategy(self):
        self.assertEqual(AssessmentCalculator().calculate(75, 100)["classification"], "Distinction")

    def test_accepts_explicit_strategy_at_construction(self):
        self.assertEqual(AssessmentCalculator(PassFailStrategy()).calculate(60, 100)["classification"], "Pass")

    def test_set_strategy_swaps_behaviour_at_runtime(self):
        calculator = AssessmentCalculator(PercentageStrategy())
        self.assertEqual(calculator.calculate(60, 100)["classification"], "pass")
        calculator.set_strategy(PassFailStrategy())
        self.assertEqual(calculator.calculate(60, 100)["classification"], "Pass")


# --------------------
# Strategy - integration into the Assessment model
# ------------------------------------------------

class TestAssessmentStrategyIntegration(BaseTestCase):
    def test_default_strategy_matches_the_domain_model_default(self):
        a = Assessment(self.registration(), raw_score=41, max_score=50)
        self.assertEqual(a.get_percentage(), 82.0)
        self.assertEqual(a.get_classification(), "Distinction")

    def test_accepts_strategy_at_construction(self):
        a = Assessment(self.registration(), raw_score=60, strategy=PassFailStrategy())
        self.assertEqual(a.get_classification(), "Pass")

    def test_set_strategy_changes_output_at_runtime(self):
        a = Assessment(self.registration(), raw_score=82)
        self.assertEqual(a.get_classification(), "Distinction")

        a.set_strategy(WeightedStrategy(weight=0.3))
        self.assertEqual(a.get_percentage(), 24.6)
        self.assertEqual(a.get_classification(), "Distinction")

    def test_assessment_still_completes_the_registration(self):
        reg = self.registration()
        Assessment(reg, raw_score=90)
        self.assertEqual(reg.status, "COMPLETED")
        self.assertIsNotNone(reg.assessment)


if __name__ == "__main__":
    unittest.main()