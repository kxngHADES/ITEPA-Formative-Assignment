"""
Entity linking a learner to a course
"""

from datetime import datetime, timezone, timedelta

south_africa_tz = timezone(timedelta(hours=2))

class Registration:
    # reps one learners enrolment into one course using its own state and linked assessment
    _id_counter = 1
    VALID_STATUSES = {"PENDING", "CONFIRMED", "CANCELLED", "COMPLETED"}

    def __init__(self, learner, course, status="CONFIRMED"):
        if learner is None or course is None:
            raise ValueError("A registration needs a learner and a course")
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status: {repr(status)}")

        self.registration_id = f"R{Registration._id_counter:04d}"
        Registration._id_counter += 1

        self.learner = learner
        self.course = course
        self.status = status
        self.date_registred = datetime.now(south_africa_tz)
        self.assessment = None

    def attach_assessment(self, assessment):
        self.assessment = assessment
        self.status = "COMPLETED"

    def cancel(self):
        self.status = "CANCELLED"

    def __repr__(self):
        return f"<Registration {self.registration_id}: {self.learner.name} -> {self.course.course_code} [{self.status}]>"

    def __str__(self):
        return f"{self.learner.name} registered for {self.course.title}"