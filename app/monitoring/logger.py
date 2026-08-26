"""
Bugzot monitoring subsystem 9event logger)

Records events 9sucess, validation, failures etc) with enough comtext

all timestamps are in SAST = UCT + 2
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import List, Optional, Dict, Any

south_africa_tz = timezone(timedelta(hours=2))

class EventLevel(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

class EventCategory(Enum):
    REGISTRATION_SUCCESS = "Registration Success"
    VALIDATION_FAILURE = "Validation Failure"
    DUPLICATE_REGISTRATION = "Duplicate Registration"
    CAPACITY_VIOLATION = "Capacity Violation"
    APPLICATION_ERROR = "Application Error"


@dataclass
class BugzotEvent:
    # a single recorded event with enough context
    level: EventLevel
    category: EventCategory
    message: str
    source: str = "unknown"
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(south_africa_tz))

    def format_line(self) -> str:
        ts = self.timestamp.strftime("%Y-%m-%d %H:%M:%S") # year-month-day Hour:Minute:Second
        return f"{ts} | {self.level.value} | {self.category.value} | {self.message}"

    def __repr__(self):
        return f"<BugzotEvent {self.category.value}: {self.message}>"

class BugzotLogger:
    def __init__(self):
        self._events: List[BugzotEvent] = []

    # Recording
    def log(self, level: EventLevel, category: EventCategory, message: str, source: str = "unknown", 
            context: Optional[Dict[str, Any]] = None) -> BugzotEvent:

        event = BugzotEvent(level=level, category=category, message=message, source=source, context=context or {})
        self._events.append(event)
        return event

    def log_success(self, message: str, source: str = "unknown", **context) -> BugzotEvent:
        return self.log(EventLevel.INFO, EventCategory.REGISTRATION_SUCCESS, message, source, context)

    def log_validation_failure(self, message: str, source: str = "unknown", **context) -> BugzotEvent:
        return self.log(EventLevel.ERROR, EventCategory.VALIDATION_FAILURE, message, source, context)

    def log_duplicate_registration(self, message: str, source: str = "unknown", **context) -> BugzotEvent:
        return self.log(EventLevel.WARNING, EventCategory.DUPLICATE_REGISTRATION, message, source, context)

    def log_capacity_violation(self, message: str, source: str = "unknown", **context) -> BugzotEvent:
        return self.log(EventLevel.WARNING, EventCategory.CAPACITY_VIOLATION, message, source, context)

    def log_application_error(self, message: str, source: str = "unknown", **context) -> BugzotEvent:
        return self.log(EventLevel.ERROR, EventCategory.APPLICATION_ERROR, message, source, context)


    def record_from_result(self, result, source: str = "RegistrationProcessingEngine") -> BugzotEvent:
        context = {"request_id": getattr(result.request, "request_id", None)}

        if result.registration is not None:
            context["registration_id"] = result.registration.registration_id
        if result.request.learner is not None:
            context["learner_id"] = getattr(result.request.learner, "learner_id", None)
        if result.request.course is not None:
            context["course_code"] = getattr(result.request.course, "course_code", None)

        if result.is_success:
            return self.log_success(result.message, source=source, **context)

        message_lower = result.message.lower()

        if "already" in message_lower and "registered" in message_lower:
            return self.log_duplicate_registration(result.message, source=source, **context)

        if "full" in message_lower:
            return self.log_capacity_violation(result.message, source=source, **context)

        if any(
            keyword in message_lower
            for keyword in ("has no learner", "has no course", "instance, got")
        ):
            return self.log_validation_failure(result.message, source=source, **context)

        return self.log_application_error(result.message, source=source, **context)



    # Querying
    @property
    def events(self) -> List[BugzotEvent]:
        return list(self._events)

    def events_by_category(self, category: EventCategory) -> List[BugzotEvent]:
        return [e for e in self._events if e.category == category]

    def events_by_level(self, level: EventLevel) -> List[BugzotEvent]:
        return [e for e in self._events if e.level == level]

    def count_by_category(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for event in self._events:
            counts[event.category.value] = counts.get(event.category.value, 0) + 1
        return counts

    def clear(self):
        self._events = []


    # Reporting
    def print_log(self, title: str = "BUGZOT EVENT MONITORING LOG"):
        print("=" * 70)
        print(title)
        print("=" * 70)
        for event in self._events:
            print(event.format_line())
        print()

    def __repr__(self):
        return f"<BugzotLogger events={len(self._events)}>"