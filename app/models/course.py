"""
Domain model for a course
"""

class Course:
    # enforces enrolment capacity and tracks registrations for a course
    def __init__(self, course_code, title, capacity=50, instructor=None):
        if not course_code:
            raise ValueError("Needs Course code")
        if not title:
            raise ValueError("Needs a title")
        if capacity <= 0:
            raise ValueError("Capacity must be greater than zero")

        self.course_code = course_code
        self.title = title
        self.capacity = capacity
        self.instructor = instructor
        self.registrations = []

    @property
    def enrolled_count(self) -> int:
        return len([r for r in self.registrations if r.status != "CANCELLED"])

    @property
    def is_full(self) -> bool:
        return self.enrolled_count >= self.capacity

    def enroll(self, learner):
        # create a registration and enforce capacity rules
        from app.models.registration import Registration
        if self.is_full:
            raise ValueError(f"Course {self.course_code} is full. annot register {learner.name}")

        registration = Registration(learner, self)
        self.registrations.append(registration)
        return registration

    def cancel_registration(self, registration):
        # cancel a registration
        if registration not in self.registrations:
            raise ValueError("This reg does not beling to this course")
        registration.status = "CANCELLED"

    def __repr__(self):
        return f"<Course {self.course_code}x{self.title}>"

    def __str__(self):
        return f"Course: {self.course_code} - {self.title}"