"""
Delierable 5.2

Run with;
    python tests/profile_application.py
"""

import cProfile
import pstats
import io
import sys
import os


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import Learner, Course
from app.engine import RegistrationRequest, RegistrationProcessingEngine, ConcurrentRegistrationProcessingEngine

NUM_LEARNER = 50
NUM_COURSES = 8
SIM_DELAY = 0.02 # 20ms

def build_requests(prefix):
    courses = [Course(f"{prefix}{i}", f"Course {prefix}{i}", capacity=15) for i in range(NUM_COURSES)]
    requests = []
    for i in range(NUM_LEARNER):
        learner = Learner(f"{prefix} Learner {i + 1}", f"{prefix.lower()}.learner{i + 1}@example.com")
        course = courses[i % NUM_COURSES]
        requests.append(RegistrationRequest(learner, course))
    return requests

def run_seq_workload():
    engine = RegistrationProcessingEngine(simulated_io_delay=SIM_DELAY)
    requests = build_requests("SEQ")
    engine.process_batch(requests)

def run_conc_workload():
    engine = ConcurrentRegistrationProcessingEngine(max_workers=10, simulated_io_delay=SIM_DELAY)
    requests = build_requests("CON")
    engine.process_batch_concurrent(requests)

def profile_and_report(func, label, sort_by="cumulative", top_n=15):
    Learner._id_counter = 1

    profiler = cProfile.Profile()
    profiler.enable()
    func()
    profiler.disable()

    print("=" * 80)
    print(f"PROFILE: {label}")
    print("=" * 80)

    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream).sort_stats(sort_by)
    stats.print_stats(top_n)
    print(stream.getvalue())

if __name__ == "__main__":
    profile_and_report(run_seq_workload, f"Sequential - {NUM_LEARNER} requests, {SIM_DELAY*1000:.0f}ms simulated I/O each")
    profile_and_report(run_conc_workload, f"Concurrent - {NUM_LEARNER} requests, {SIM_DELAY*1000:.0f}ms simulated I/O each")