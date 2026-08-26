"""
Factory pattern - creates diff SupportTicket types
"""

from app.models.support_ticket import SupportTicket

class AcademicTicket(SupportTicket):

    CATEGORY = "Academic"

    def __init__(self, learner, subject, description, priority="MEDIUM"):
        super().__init__(learner, subject, description, priority)
        self.category = self.CATEGORY

class TechnicalTicket(SupportTicket):
    CATEGORY = "Technical"
    
    def __init__(self, learner, subject, description, priority="MEDIUM"):
        super().__init__(learner, subject, description, priority)
        self.category = self.CATEGORY

class RegistrationTicket(SupportTicket):
    CATEGORY = "Registration"
    
    def __init__(self, learner, subject, description, priority="MEDIUM"):
        super().__init__(learner, subject, description, priority)
        self.category = self.CATEGORY


class SupportTicketFactory:

    _ticket_types = {
        "academic": AcademicTicket,
        "technical": TechnicalTicket,
        "registration": RegistrationTicket
    }

    @classmethod
    def create_ticket(cls, ticket_type, learner, subject, description, priority="MEDIUM"):
        key = ticket_type.strip().lower()
        ticket_class = cls._ticket_types.get(key)

        if ticket_class is None:
            valid = ", ".join(cls._ticket_types.keys())
            raise ValueError(f"Unknown ticket type: {repr(ticket_type)} use these types {valid}")

        return ticket_class(learner, subject, description, priority)

    @classmethod
    def register_ticket_type(cls, type_key, ticket_class):
        # Allows new ticket types to be plugged in at runtime
        if not issubclass(ticket_class, SupportTicket):
            raise TypeError("Ticket class must be a subclass of SupportTicket")

        cls._ticket_types[type_key.strip().lower()] = ticket_class

    @classmethod
    def available_types(cls):
        return list(cls._ticket_types.keys())