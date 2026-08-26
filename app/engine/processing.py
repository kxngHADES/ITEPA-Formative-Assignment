"""
Registration process engine

Coordinates bulk processing of learber course-registration requests
Enforced business rules through the domain models while making sure a single failed request does not stop processing the rest of the stuff
"""
import time
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime, timezone, timedelta

from app.models.learner import Learner
from app.models.course import Course
from app.models.registration import Registration

south_africa_tz = timezone(timedelta(hours=2))


@dataclass
class RegistrationRequest:
    # one learner into one course
    learner: Learner
    course: Course
    request_id: Optional[str] = None


    def __post_init__(self):
        if self.request_id is None:
            learner_ref = getattr(self.learner, "learner_id", "unknown")
            course_ref = getattr(self.course, "course_code", "unknown")
            self.request_id = f"{learner_ref}->{course_ref}"


@dataclass
class RegistrationResult:
    request: RegistrationRequest
    status: str
    message: str
    registration: Optional[Registration] = None
    processed_at: datetime = field(default_factory=lambda: datetime.now(south_africa_tz))

    @property
    def is_success(self) -> bool:
        return self.status == "SUCCESS"

    def __repr__(self):
        return f"<RegistrationResult {self.request.request_id}: {self.status}>"



class RegistrationProcessingEngine:
    # Process a batch of reg requests, enforcing:
    # basic request validation
    # duplicate regestration prevention
    # couse capacity limits

    def __init__(self, simulated_io_delay: float = 0.0):
        self._results: List[RegistrationResult] = []
        """
        Deliverable 3.3
        simulated_io_delay: Seconds to wait before each registration is processed.
        Use this to simulate a slow external API call (like checking a student information system for duplicates). 
        It defaults to 0.0, so it doesn't affect anything unless you explicitly set it. 
        This is mainly here for the Deliverable 3.3 benchmark to show how concurrent processing handles I/O bottlenecks.
        """
        self._simulated_io_delay = simulated_io_delay

    def _simulate_io_wait(self):
        if self._simulated_io_delay > 0:
            time.sleep(self._simulated_io_delay)

    def _validate_request(self, request: RegistrationRequest) -> Optional[str]:
        if request.learner is None:
            return "Request has no learner"
        if not isinstance(request.learner, Learner):
            return f"Expected a Learner instance, got {type(request.learner).__name__}."
        if request.course is None:
            return "Request has no course."
        if not isinstance(request.course, Course):
            return f"Expected a Course instance, got {type(request.course).__name__}."
        return None

    def process_single(self, request: RegistrationRequest) -> RegistrationResult:
        # processes one reg request making sure of business rules
        validation_error = self._validate_request(request)
        if validation_error:
            result = RegistrationResult(request=request, status="FAILED", message=validation_error)
            self._results.append(result)
            return result

        self._simulate_io_wait()  # simulated external eligibility/verification call

        learner = request.learner
        course = request.course
        try:
            registration = learner.register_for_course(course)
        except ValueError as e:
            result = RegistrationResult(request=request, status="FAILED", message=str(e))
        else:
            result = RegistrationResult(
                request=request,
                status="SUCCESS",
                message=f"{learner.name} registered successfully for {course.course_code}.",
                registration=registration,
            )
        self._results.append(result)
        return result

    def process_batch(self, requests: List[RegistrationRequest]) -> "ProcessingSummary":
        for request in requests:
            self.process_single(request)
        return self.get_summary()
    
    def get_summary(self) -> "ProcessingSummary":
        return ProcessingSummary(list(self._results))

    def clear(self):
        self._results = []

    @property
    def results(self) -> List[RegistrationResult]:
        return list(self._results)


class ProcessingSummary:
    # Aggs a set of Registration resul objects into totals and makes a table

    def __init__(self, results: List[RegistrationResult]):
        self.results = results

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def successful(self) -> List[RegistrationResult]:
        return [r for r in self.results if r.is_success]

    @property
    def failed(self) -> List[RegistrationResult]:
        return [r for r in self.results if not r.is_success]

    @property
    def success_count(self) -> int:
        return len(self.successful)

    @property
    def failure_count(self) -> int:
        return len(self.failed)

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return round((self.success_count / self.total) * 100, 2)

    def print_report(self):
        print("=" * 70)
        print("REGISTRATION PROCESSING ENGINE")
        print("=" * 70)
        for result in self.results:
            tag = "[SUCCESS]" if result.is_success else "[FAILED] "
            print(f"{tag} {result.message}")

        print()
        print("REGISTRATION SUMMARY")
        print("-" * 70)
        print(f"Total Registrations Processed: {self.total}")
        print(f"Successful: {self.success_count}")
        print(f"Failed: {self.failure_count}")
        print(f"Success Rate: {self.success_rate}%")

    def __repr__(self):
        return (
            f"<ProcessingSummary total={self.total} "
            f"success={self.success_count} failed={self.failure_count}>"
        )


# Deliverable 2.3 Concurrent processsing
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

class ConcurrentRegistrationProcessingEngine(RegistrationProcessingEngine):
    """
    I've extended the RegistrationProcessingEngine to handle requests concurrently using a thread pool. 
    To prevent race conditions and over-capacity enrollments, 
    I implemented course-specific locks that ensure "check-then-act" operations are atomic. 
    I also added a separate lock for the internal results list to safely handle concurrent updates from worker threads.
    """

    def __init__(self, max_workers: int = 10, simulated_io_delay: float = 0.0):
        super().__init__(simulated_io_delay=simulated_io_delay)
        self.max_workers = max_workers
        self._course_locks = defaultdict(threading.Lock)
        self._course_locks_guard = threading.Lock()
        self._results_lock = threading.Lock()

    def _get_course_lock(self, course_code: str) -> threading.Lock:
        with self._course_locks_guard:
            return self._course_locks[course_code]

    def process_single(self, request: RegistrationRequest) -> RegistrationResult:
        validation_error = self._validate_request(request)
        if validation_error:
            result = RegistrationResult(request=request, status="FAILED", message=validation_error)
            with self._results_lock:
                self._results.append(result)
            return result

        course_lock = self._get_course_lock(request.course.course_code)

        with course_lock:
            try:
                registration = request.learner.register_for_course(request.course)
            except ValueError as e:
                result = RegistrationResult(request=request, status="FAILED", message=str(e))
            else:
                result = RegistrationResult(
                    request=request,
                    status="SUCCESS",
                    message=(
                        f"{request.learner.name} registered successfully for "
                        f"{request.course.course_code} (concurrent)."
                    ),
                    registration=registration,
                )

        with self._results_lock:
            self._results.append(result)
        return result

    def process_batch_concurrent(self, requests: List[RegistrationRequest]) -> "ProcessingSummary":
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self.process_single, request) for request in requests]
            for future in as_completed(futures):
                future.result()

        return self.get_summary()