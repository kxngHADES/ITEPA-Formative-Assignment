"""
Domain model for learner
"""

import re
from datetime import datetime, timezone, timedelta

south_africa_tz = timezone(timedelta(hours=2))

class Learner:
    # represents a learner enolled

    # maintains the list of course reg and support tickets associayed with the learner.

    _id_counter = 1
    EMAIL_REGEX = re.compile(r'^[\w\-\.]+@([\w\-]+\.)+[\w\-]{2,4}$') # https://regexr.com/3e48o

    def __init__(self, name, email, phone=None):
        if not name or not isinstance(name, str):
            raise ValueError("Learner name is needed and must be a string")
        if not email or not self.EMAIL_REGEX.match(email):
            raise ValueError(f"Invalid email address: {repr(email)}")

        self.learner_id = f"L{Learner._id_counter:03d}" # pad with zeros ad make 3 characters wide
        Learner._id_counter += 1

        self.name = name
        self.email = email
        self.phone = phone
        self.date_joined = datetime.now(south_africa_tz)
        self.registrations = []
        self.support_tickets = []

    def __repr__(self):
        return f"<Learner {self.learner_id}x{self.name}>" # matches teh style of memory addresses 

    def __str__(self):
        return f"Learner ID: {self.learner_id}, Name: {self.name}" # for when we print the class

    def register_for_course(self, course):
        # register learner via a course enrolment function in course class
        if self.has_registration_for(course):
            raise ValueError(f"Learner {self.learner_id} is already registered for {course.course_code}")

        registration = course.enroll(self)
        self.registrations.append(registration)
        return registration

    def has_registration_for(self, course):
        return any(r.course.course_code == course.course_code for r in self.registrations)

    def raise_support_ticket(self, ticket):
        self.support_tickets.append(ticket)

    def get_avrg_score(self):
        scores = [reg.assessment.get_percentage() for reg in self.registrations if reg.assessment is not None]

        if not scores: return None
        return round(sum(scores)/len(scores), 2)
