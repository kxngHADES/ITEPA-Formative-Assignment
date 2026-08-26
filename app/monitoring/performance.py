import time
import statistics
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

south_africa_tz = timezone(timedelta(hours=2))

@dataclass
class TransactionMetric:
    component: str
    operation: str
    duration_ms: float
    success: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(south_africa_tz))
    detail: Optional[str] = None

    def __repr__(self):
        outcome= "OK" if self.success else "FAILED"
        return f"<TransactionMetric {self.component} {self.operation} {self.duration_ms}ms [{outcome}]"

class PerformanceMonitor:
    def __init__(self):
        self._metrics: List[TransactionMetric] = []

    # recording
    @contextmanager
    def measure(self, component: str, operation: str, detail: Optional[str] = None):
        start = time.perf_counter()
        success = True
        try:
            yield
        except Exception:
            success = False
            raise
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            self._metrics.append(
                TransactionMetric(
                    component=component,
                    operation=operation,
                    duration_ms=duration_ms,
                    success=success,
                    detail=detail,
                )
            )

    def record_manual(self, component:str, operation:str, duration_ms:float,
                      success: bool = True, detail: Optional[str] = None) -> TransactionMetric:

        metric = TransactionMetric(
            component=component,
            operation=operation,
            duration_ms=duration_ms,
            success=success,
            detail=detail,
        )
        self._metrics.append(metric)
        return metric



    # querying/stats
    @property
    def metrics(self) -> List[TransactionMetric]:
        return list(self._metrics)

    @property
    def transaction_count(self) -> int:
        return len(self._metrics)

    def metrics_for(self, component: Optional[str] = None, operation: Optional[str] = None) -> List[TransactionMetric]:
        result = self._metrics
        if component is not None:
            result = [m for m in result if m.component == component]
        if operation is not None:
            result = [m for m in result if m.operation == operation]
        return result

    def _durations(self, metrics: List[TransactionMetric]) -> List[float]:
        return [m.duration_ms for m in metrics]

    def average_duration_ms(self, component: Optional[str] = None, operation: Optional[str] = None) -> float:
        durations = self._durations(self.metrics_for(component, operation))
        if not durations:
            return 0.0
        return round(statistics.mean(durations), 3)

    def min_duration_ms(self, component: Optional[str] = None, operation: Optional[str] = None) -> float:
        durations = self._durations(self.metrics_for(component, operation))
        return round(min(durations), 3) if durations else 0.0

    def max_duration_ms(self, component: Optional[str] = None, operation: Optional[str] = None) -> float:
        durations = self._durations(self.metrics_for(component, operation))
        return round(max(durations), 3) if durations else 0.0

    def success_rate(self, component: Optional[str] = None, operation: Optional[str] = None) -> float:
        subset = self.metrics_for(component, operation)
        if not subset:
            return 0.0
        successes = sum(1 for m in subset if m.success)
        return round((successes / len(subset)) * 100, 2)



    def throughput_per_second(self, component: Optional[str] = None, 
                              operation: Optional[str] = None) -> float:


        subset = sorted(self.metrics_for(component, operation), key=lambda m: m.timestamp)
        if len(subset) < 2:
            return 0.0

        elapsed_seconds = (subset[-1].timestamp - subset[0].timestamp).total_seconds()
        if elapsed_seconds <= 0:
            elapsed_seconds = sum(self._durations(subset)) / 1000
            if elapsed_seconds <= 0:
                return 0.0

        return round(len(subset) / elapsed_seconds, 2)

    def components(self) -> List[str]:
        return sorted({m.component for m in self._metrics})

    def clear(self):
        self._metrics = []

        
    # reporting
    def generate_report(self) -> Dict:
        report = {
            "total_transactions": self.transaction_count,
            "overall_success_rate": self.success_rate(),
            "overall_average_duration_ms": self.average_duration_ms(),
            "components": {},
        }

        for component in self.components():
            report["components"][component] = {
                "transaction_count": len(self.metrics_for(component=component)),
                "average_duration_ms": self.average_duration_ms(component=component),
                "min_duration_ms": self.min_duration_ms(component=component),
                "max_duration_ms": self.max_duration_ms(component=component),
                "success_rate": self.success_rate(component=component),
                "throughput_per_second": self.throughput_per_second(component=component),
            }

        return report


    def print_report(self, title: str = "APPLICATION PERFORMANCE REPORT"):
        report = self.generate_report()

        print("=" * 70)
        print(title)
        print("=" * 70)
        print(f"Total Transactions Recorded: {report['total_transactions']}")
        print(f"Overall Success Rate: {report['overall_success_rate']}%")
        print(f"Overall Average Duration: {report['overall_average_duration_ms']}ms")
        print()

        for component, stats in report["components"].items():
            print(f"Component: {component}")
            print("-" * 70)
            print(f"  Transactions: {stats['transaction_count']}")
            print(f"  Average Duration: {stats['average_duration_ms']}ms")
            print(f"  Min Duration: {stats['min_duration_ms']}ms")
            print(f"  Max Duration: {stats['max_duration_ms']}ms")
            print(f"  Success Rate: {stats['success_rate']}%")
            print(f"  Throughput: {stats['throughput_per_second']} transactions/sec")
            print()

    def __repr__(self):
        return f"<PerformanceMonitor transactions={self.transaction_count}>"