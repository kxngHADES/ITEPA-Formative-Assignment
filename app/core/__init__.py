"""
app.core model package
"""

from app.core.config_manager import ConfigManager
from app.core.ticket_factory import SupportTicketFactory, AcademicTicket, TechnicalTicket, RegistrationTicket
from app.core.assessment_strategy import AssessmentStrategy, PercentageStrategy, PassFailStrategy, WeightedStrategy, AssessmentCalculator

__all__ = [
    "ConfigManager",
    "SupportTicketFactory",
    "AcademicTicket",
    "TechnicalTicket",
    "RegistrationTicket",
    "AssessmentStrategy",
    "PercentageStrategy",
    "PassFailStrategy",
    "WeightedStrategy",
    "AssessmentCalculator",
]