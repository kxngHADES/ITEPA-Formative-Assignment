"""
Unit tests for the core domain model (app.models).

Covers:
    - Learner, Course, Registration, Assessment, SupportTicket
    - Relationships between classes (Learner <-> Course <-> Registration,
      Registration <-> Assessment, Learner <-> SupportTicket)
    - Validation rules and core functionality on each class

Run with:
    python -m unittest tests/test_models.py -v
"""

import re
import unittest

from app.models import Learner, Course, Registration, Assessment, SupportTicket


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        Learner._id_counter = 1
        Registration._id_counter = 1
        SupportTicket._id_count = 1

    def learner(self, name="Ndaedzo Mudau", tag="1"):
        return Learner(name, f"{name.lower().replace(' ', '.')}.{tag}@example.com")

    def course(self, code="ITEPA3-33", capacity=2):
        return Course(code, "Enterprise Python", capacity=capacity)


# --------------
# Learner
# --------------

class TestLearnerCreation(BaseTestCase):
    def test_created_with_correct_attributes(self):
        l = Learner("Ndaedzo Mudau", "ndaedzo@example.com", phone="0821234567")
        self.assertEqual(l.name, "Ndaedzo Mudau")
        self.assertEqual(l.email, "ndaedzo@example.com")
        self.assertEqual(l.phone, "0821234567")
        self.assertEqual(l.registrations, [])
        self.assertEqual(l.support_tickets, [])

    def test_id_format_and_increment(self):
        l1 = self.learner("Learner A", "a")
        l2 = self.learner("Learner B", "b")
        self.assertTrue(re.match(r"^L\d{3}$", l1.learner_id))
        self.assertEqual(l1.learner_id, "L001")
        self.assertEqual(l2.learner_id, "L002")

    def test_repr_and_str(self):
        l = self.learner()
        self.assertEqual(str(l), f"Learner ID: {l.learner_id}, Name: {l.name}")
        self.assertIn(l.learner_id, repr(l))


class TestLearnerValidation(BaseTestCase):
    def test_empty_or_none_name_raises(self):
        with self.assertRaises(ValueError):
            Learner("", "ndaedzo@example.com")
        with self.assertRaises(ValueError):
            Learner(None, "ndaedzo@example.com")

    def test_invalid_email_formats_raise(self):
        for bad_email in ["not-an-email", "missing@tld", "@example.com", "ndaedzo@", "ndaedzo @example.com"]:
            with self.subTest(bad_email=bad_email):
                with self.assertRaises(ValueError):
                    Learner("Ndaedzo Mudau", bad_email)

    def test_valid_email_formats_accepted(self):
        for good_email in ["ndaedzo@example.com", "ndaedzo.mudau@example.co.za"]:
            with self.subTest(good_email=good_email):
                l = Learner("Ndaedzo Mudau", good_email)
                self.assertEqual(l.email, good_email)


class TestLearnerFunctionality(BaseTestCase):
    def test_register_for_course_creates_registration(self):
        learner, course = self.learner(), self.course()
        reg = learner.register_for_course(course)

        self.assertIsInstance(reg, Registration)
        self.assertIn(reg, learner.registrations)
        self.assertIs(reg.learner, learner)
        self.assertIs(reg.course, course)

    def test_duplicate_registration_raises(self):
        learner, course = self.learner(), self.course()
        learner.register_for_course(course)
        with self.assertRaises(ValueError):
            learner.register_for_course(course)

    def test_has_registration_for(self):
        learner, course = self.learner(), self.course()
        other = self.course(code="PY702")

        self.assertFalse(learner.has_registration_for(course))
        learner.register_for_course(course)
        self.assertTrue(learner.has_registration_for(course))
        self.assertFalse(learner.has_registration_for(other))

    def test_average_score_none_when_no_assessments(self):
        learner = self.learner()
        learner.register_for_course(self.course())
        self.assertIsNone(learner.get_avrg_score())

    def test_average_score_computed_correctly(self):
        learner = self.learner()
        course_a, course_b = self.course("PY701"), self.course("PY702")

        Assessment(learner.register_for_course(course_a), raw_score=80)
        Assessment(learner.register_for_course(course_b), raw_score=60)

        self.assertEqual(learner.get_avrg_score(), 70.0)


# --------------
# Course
# --------------

class TestCourseCreation(BaseTestCase):
    def test_created_with_correct_attributes(self):
        c = Course("ITEPA3-33", "Enterprise Python", capacity=20, instructor="Ms. Naidoo")
        self.assertEqual(c.course_code, "ITEPA3-33")
        self.assertEqual(c.capacity, 20)
        self.assertEqual(c.instructor, "Ms. Naidoo")
        self.assertEqual(c.registrations, [])


class TestCourseValidation(BaseTestCase):
    def test_empty_course_code_or_title_raises(self):
        with self.assertRaises(ValueError):
            Course("", "Enterprise Python")
        with self.assertRaises(ValueError):
            Course("ITEPA3-33", "")

    def test_non_positive_capacity_raises(self):
        for bad_capacity in [0, -1, -50]:
            with self.subTest(capacity=bad_capacity):
                with self.assertRaises(ValueError):
                    Course("ITEPA3-33", "Enterprise Python", capacity=bad_capacity)


class TestCourseFunctionality(BaseTestCase):
    def test_enrolled_count_and_is_full(self):
        course = self.course(capacity=1)
        self.assertEqual(course.enrolled_count, 0)
        self.assertFalse(course.is_full)

        self.learner("Learner A", "a").register_for_course(course)

        self.assertEqual(course.enrolled_count, 1)
        self.assertTrue(course.is_full)

    def test_enroll_raises_when_full(self):
        course = self.course(capacity=1)
        self.learner("Learner A", "a").register_for_course(course)

        with self.assertRaises(ValueError):
            self.learner("Learner B", "b").register_for_course(course)

        self.assertEqual(len(course.registrations), 1)

    def test_cancel_registration_frees_capacity(self):
        course = self.course(capacity=1)
        learner_a = self.learner("Learner A", "a")
        learner_b = self.learner("Learner B", "b")

        reg_a = learner_a.register_for_course(course)
        course.cancel_registration(reg_a)
        reg_b = learner_b.register_for_course(course)

        self.assertEqual(reg_a.status, "CANCELLED")
        self.assertIn(reg_b, course.registrations)
        self.assertEqual(course.enrolled_count, 1)

    def test_cancel_registration_not_belonging_to_course_raises(self):
        course, other_course = self.course(), self.course(code="PY999")
        foreign_reg = self.learner().register_for_course(other_course)

        with self.assertRaises(ValueError):
            course.cancel_registration(foreign_reg)


# --------------
# Registration
# --------------

class TestRegistrationCreation(BaseTestCase):
    def test_created_with_correct_attributes(self):
        learner, course = self.learner(), self.course()
        reg = Registration(learner, course)

        self.assertIs(reg.learner, learner)
        self.assertIs(reg.course, course)
        self.assertEqual(reg.status, "CONFIRMED")
        self.assertIsNone(reg.assessment)

    def test_id_format_and_increment(self):
        learner, course = self.learner(), self.course()
        reg1 = Registration(learner, course)
        reg2 = Registration(self.learner("Other", "o"), self.course(code="PY702"))
        self.assertTrue(re.match(r"^R\d{4}$", reg1.registration_id))
        self.assertEqual(reg1.registration_id, "R0001")
        self.assertEqual(reg2.registration_id, "R0002")


class TestRegistrationValidation(BaseTestCase):
    def test_none_learner_or_course_raises(self):
        with self.assertRaises(ValueError):
            Registration(None, self.course())
        with self.assertRaises(ValueError):
            Registration(self.learner(), None)

    def test_invalid_status_raises(self):
        with self.assertRaises(ValueError):
            Registration(self.learner(), self.course(), status="BOGUS")

    def test_valid_statuses_accepted(self):
        for status in ["PENDING", "CONFIRMED", "CANCELLED", "COMPLETED"]:
            with self.subTest(status=status):
                reg = Registration(self.learner(tag=status), self.course(code=f"PY{status}"), status=status)
                self.assertEqual(reg.status, status)


class TestRegistrationFunctionality(BaseTestCase):
    def test_attach_assessment_sets_status_completed(self):
        reg = self.learner().register_for_course(self.course())
        assessment = Assessment(reg, raw_score=75)

        self.assertIs(reg.assessment, assessment)
        self.assertEqual(reg.status, "COMPLETED")

    def test_cancel_sets_status_cancelled(self):
        reg = self.learner().register_for_course(self.course())
        reg.cancel()
        self.assertEqual(reg.status, "CANCELLED")


# --------------
# Assessment
# --------------

class TestAssessmentCreation(BaseTestCase):
    def test_created_with_correct_attributes(self):
        reg = self.learner().register_for_course(self.course())
        a = Assessment(reg, raw_score=82, max_score=100)

        self.assertIs(a.registration, reg)
        self.assertEqual(a.raw_score, 82)
        self.assertEqual(a.max_score, 100)

    def test_max_score_defaults_to_hundred(self):
        reg = self.learner().register_for_course(self.course())
        self.assertEqual(Assessment(reg, raw_score=82).max_score, 100)


class TestAssessmentValidation(BaseTestCase):
    def test_none_registration_raises(self):
        with self.assertRaises(ValueError):
            Assessment(None, raw_score=82)

    def test_non_positive_max_score_raises(self):
        reg = self.learner().register_for_course(self.course())
        with self.assertRaises(ValueError):
            Assessment(reg, raw_score=10, max_score=0)

    def test_score_out_of_range_raises(self):
        reg = self.learner().register_for_course(self.course())
        with self.assertRaises(ValueError):
            Assessment(reg, raw_score=-5)
        with self.assertRaises(ValueError):
            Assessment(reg, raw_score=150, max_score=100)

    def test_boundary_scores_are_valid(self):
        reg = self.learner().register_for_course(self.course())
        self.assertEqual(Assessment(reg, raw_score=0).raw_score, 0)


class TestAssessmentFunctionality(BaseTestCase):
    def test_get_percentage_calculation(self):
        reg = self.learner().register_for_course(self.course())
        a = Assessment(reg, raw_score=41, max_score=50)
        self.assertEqual(a.get_percentage(), 82.0)

    def test_classification_boundaries(self):
        cases = [(75, "Distinction"), (74, "pass"), (50, "pass"), (49, "Fail"), (0, "Fail")]
        for raw_score, expected in cases:
            with self.subTest(raw_score=raw_score):
                reg = self.learner(tag=f"c{raw_score}").register_for_course(self.course(code=f"PYC{raw_score}"))
                a = Assessment(reg, raw_score=raw_score, max_score=100)
                self.assertEqual(a.get_classification(), expected)


# --------------
# SupportTicket
# --------------

class TestSupportTicketCreation(BaseTestCase):
    def test_created_with_correct_attributes(self):
        learner = self.learner()
        t = SupportTicket(learner, "Login issue", "Cannot access portal", priority="HIGH")

        self.assertIs(t.learner, learner)
        self.assertEqual(t.subject, "Login issue")
        self.assertEqual(t.priority, "HIGH")
        self.assertEqual(t.status, "OPEN")

    def test_priority_defaults_to_medium(self):
        t = SupportTicket(self.learner(), "Login issue", "Cannot access portal")
        self.assertEqual(t.priority, "MEDIUM")

    def test_id_format_and_increment(self):
        learner = self.learner()
        t1 = SupportTicket(learner, "Issue 1", "Description 1")
        t2 = SupportTicket(learner, "Issue 2", "Description 2")
        self.assertEqual(t1.ticket_id, "T0001")
        self.assertEqual(t2.ticket_id, "T0002")

    def test_creating_ticket_registers_it_with_learner(self):
        learner = self.learner()
        t = SupportTicket(learner, "Login issue", "Cannot access portal")
        self.assertIn(t, learner.support_tickets)


class TestSupportTicketValidation(BaseTestCase):
    def test_none_learner_raises(self):
        with self.assertRaises(ValueError):
            SupportTicket(None, "Login issue", "Cannot access portal")

    def test_empty_subject_raises(self):
        with self.assertRaises(ValueError):
            SupportTicket(self.learner(), "", "Cannot access portal")

    def test_invalid_priority_raises(self):
        with self.assertRaises(ValueError):
            SupportTicket(self.learner(), "Login issue", "Cannot access portal", priority="URGENT")


class TestSupportTicketFunctionality(BaseTestCase):
    def test_resolve_and_close(self):
        t = SupportTicket(self.learner(), "Login issue", "Cannot access portal")
        t.resolve()
        self.assertEqual(t.status, "RESOLVED")
        t.close()
        self.assertEqual(t.status, "CLOSED")


# ------------------------------------
# Integration across all five classes
# ------------------------------------

class TestDomainModelIntegration(BaseTestCase):
    def test_full_learner_to_course_to_assessment_to_ticket_workflow(self):
        learner = self.learner()
        course = self.course(capacity=16)

        reg = learner.register_for_course(course)
        self.assertIn(reg, course.registrations)

        assessment = Assessment(reg, raw_score=82)
        self.assertEqual(reg.status, "COMPLETED")
        self.assertEqual(assessment.get_classification(), "Distinction")

        ticket = SupportTicket(learner, "Login issue", "Cannot access myLMS")
        self.assertIn(ticket, learner.support_tickets)

        self.assertEqual(learner.get_avrg_score(), 82.0)


if __name__ == "__main__":
    unittest.main()