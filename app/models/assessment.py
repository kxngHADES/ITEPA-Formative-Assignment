"""
assessment results linked to a registration
"""

from app.core.assessment_strategy import AssessmentCalculator, PercentageStrategy


class Assessment:
    def __init__(self, registration, raw_score, max_score=100, strategy=None):
        if registration is None:
            raise ValueError("Assessment needs to link to a registration")
        if max_score <= 0:
            raise ValueError("Max score must be greater than zero")

        if not (0 <= raw_score <= max_score):
            raise ValueError(f"raw score must be between 0 and {max_score}")

        self.registration = registration
        self.raw_score = raw_score
        self.max_score = max_score
        self._calculator = AssessmentCalculator(strategy or PercentageStrategy())
        registration.attach_assessment(self)

    def set_strategy(self, strategy):
        self._calculator.set_strategy(strategy)

    def get_percentage(self):
        return self._calculator.calculate(self.raw_score, self.max_score)["percentage"]

    def get_classification(self):
        return self._calculator.calculate(self.raw_score, self.max_score)["classification"]

    def __repr__(self):
        return f"<Assessment {self.registration.registration_id}x{self.get_percentage()}%>"

    def __str__(self):
        return f"Score: {self.get_percentage()}% ({self.get_classification()})"
