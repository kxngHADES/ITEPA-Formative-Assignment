"""
Strategy patern - interchangable approaches for calculating assessments percentage and so on
"""

from abc import ABC, abstractmethod

class AssessmentStrategy(ABC):
    @abstractmethod
    def calculate(self, raw_score, max_score):
        # return percetage:float, classification: str
        raise NotImplementedError

class PercentageStrategy(AssessmentStrategy):
    # srandard approach used for full cred courses
    # mark >= 75 Distinction mark >= 50 pass, else fail

    DISTINCTION_THRESHOLD = 75
    PASS_THRESHOLD = 50

    def calculate(self, raw_score, max_score):
        percentage = round((raw_score/max_score)* 100, 2)

        if percentage >= self.DISTINCTION_THRESHOLD:
            classification = "Distinction"
        elif percentage >= self.PASS_THRESHOLD:
            classification = "pass"
        else:
            classification = "Fail"

        return {"percentage": percentage, "classification": classification}

class PassFailStrategy(AssessmentStrategy):
    PASS_THRESHOLD = 50

    def calculate(self, raw_score, max_score):
        percentage = round((raw_score/max_score)* 100, 2)
        classification = "Pass" if percentage >= self.PASS_THRESHOLD else "Fail"
        return {"percentage": percentage, "classification":classification}


class WeightedStrategy(AssessmentStrategy):
    DISTINCTION_THRESHOLD = 75
    PASS_THRESHOLD = 50

    def __init__(self, weight=1.0):
        if not (0 < weight <= 1):
            raise ValueError("weight must be greater than 0 but less than or equal to 1")
        self.weight = weight

    def calculate(self, raw_score, max_score):
        percentage = round((raw_score/max_score)* 100, 2)
        weighted_percentage = round(percentage * self.weight, 2)

        if percentage >= self.DISTINCTION_THRESHOLD:
            classification = "Distinction"
        elif percentage >= self.PASS_THRESHOLD:
            classification = "pass"
        else:
            classification = "Fail"

        return {"percentage": weighted_percentage, "classification": classification}


class AssessmentCalculator:
    def __init__(self, strategy: AssessmentStrategy = None):
        self._strategy = strategy or PercentageStrategy()

    def set_strategy(self, strategy: AssessmentStrategy):
        self._strategy = strategy

    def calculate(self, raw_score, max_score):
        return self._strategy.calculate(raw_score, max_score)