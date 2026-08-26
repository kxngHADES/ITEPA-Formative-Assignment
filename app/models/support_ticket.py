"""
support tikets raised by a learner
"""

from datetime import datetime, timezone, timedelta

south_africa_tz = timezone(timedelta(hours=2))

class SupportTicket:
    _id_count = 1
    VALID_PRIORITIES = {"LOW","MEDIUM","HIGH"}
    VALID_STATUSES = {"OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"}

    def __init__(self, learner, subject: str, description: str, priority="MEDIUM"):
        if learner is None:
            raise ValueError("A support ticket needs a learner")
        if not subject:
            raise ValueError("Subject is required")
        if priority not in self.VALID_PRIORITIES:
            raise ValueError(f"Invalid priority: {priority}")

        self.ticket_id = f"T{SupportTicket._id_count:04d}"
        SupportTicket._id_count += 1

        self.learner = learner
        self.subject = subject
        self.description = description
        self.priority = priority
        self.status = "OPEN"
        self.created_at = datetime.now(south_africa_tz)

        learner.raise_support_ticket(self)

    def resolve(self):
        self.status = "RESOLVED"

    def close(self):
        self.status = "CLOSED"

    def __repr__(self):
        return f"<SupportTicker {self.ticket_id}: {self.subject} [{self.status}]>"

    def __str__(self):
        return f"Ticket {self.ticket_id} - {self.subject} ({self.status}) \nDiscription:\n\t{self.description}"