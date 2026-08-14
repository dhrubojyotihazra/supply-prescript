"""
SupplyPrescript - Week 3 Automated Remediation Engine
Circuit Breaker Logic & Stream Routing Engine

Safety Threshold: 2.0% error rate.
When error rate > 2.0%, Flink/Stream process routes incoming payload to
Dead Letter Queue (DLQ) Iceberg table ('warehouses_dlq_stream') instead of main table.
"""

from enum import Enum
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable

class CircuitState(str, Enum):
    CLOSED = "CLOSED"       # Normal operation -> routes to Main Iceberg Table
    OPEN = "OPEN"           # Tripped! -> routes stream to DLQ Iceberg Table
    HALF_OPEN = "HALF_OPEN" # Recovery evaluation mode

class CircuitBreakerManager:
    def __init__(self, threshold_error_rate: float = 2.0):
        self.threshold_error_rate = threshold_error_rate
        self.state = CircuitState.CLOSED
        self.total_events = 1000
        self.error_events = 5
        self.last_evaluated_at = datetime.utcnow()
        self.last_state_change = datetime.utcnow()
        self.main_table = "warehouses_main_stream"
        self.dlq_table = "warehouses_dlq_stream"
        self.listeners: List[Callable[[Dict[str, Any]], None]] = []

    def get_error_rate(self) -> float:
        if self.total_events == 0:
            return 0.0
        return round((self.error_events / self.total_events) * 100.0, 2)

    def register_listener(self, callback: Callable[[Dict[str, Any]], None]):
        """Registers a callback for state change & telemetry updates."""
        if callback not in self.listeners:
            self.listeners.append(callback)

    def notify_listeners(self, event_data: Dict[str, Any]):
        for listener in self.listeners:
            try:
                listener(event_data)
            except Exception:
                pass

    def evaluate_stream_batch(self, batch_total: int, batch_errors: int) -> Dict[str, Any]:
        """
        Evaluates an incoming streaming batch.
        Updates counters and trips circuit breaker if error rate > 2.0%.
        """
        prev_state = self.state
        self.total_events += max(0, batch_total)
        self.error_events += max(0, batch_errors)
        self.last_evaluated_at = datetime.utcnow()

        current_error_rate = self.get_error_rate()

        if current_error_rate > self.threshold_error_rate:
            if self.state != CircuitState.OPEN:
                self.state = CircuitState.OPEN
                self.last_state_change = datetime.utcnow()
        else:
            if self.state == CircuitState.OPEN and batch_errors == 0:
                self.state = CircuitState.HALF_OPEN
            elif self.state == CircuitState.HALF_OPEN and current_error_rate <= self.threshold_error_rate:
                self.state = CircuitState.CLOSED
                self.last_state_change = datetime.utcnow()

        destination = self.dlq_table if self.state == CircuitState.OPEN else self.main_table

        result = {
            "state": self.state.value,
            "error_rate": current_error_rate,
            "threshold": self.threshold_error_rate,
            "total_events": self.total_events,
            "error_events": self.error_events,
            "active_destination": destination,
            "is_tripped": self.state == CircuitState.OPEN,
            "evaluated_at": self.last_evaluated_at.isoformat(),
            "state_changed": prev_state != self.state
        }

        if prev_state != self.state:
            self.notify_listeners(result)

        return result

    def simulate_anomaly_spike(self, error_rate_percent: float = 4.5) -> Dict[str, Any]:
        """Injects an error spike to test the circuit breaker trip logic."""
        added_total = 200
        added_errors = int((error_rate_percent / 100.0) * added_total) + 15
        return self.evaluate_stream_batch(added_total, added_errors)

    def reset_circuit(self) -> Dict[str, Any]:
        """Manually resets the circuit breaker to CLOSED (Normal Operation)."""
        prev_state = self.state
        self.state = CircuitState.CLOSED
        self.total_events = 1000
        self.error_events = 4 # 0.4% baseline
        self.last_state_change = datetime.utcnow()
        self.last_evaluated_at = datetime.utcnow()

        result = {
            "state": self.state.value,
            "error_rate": self.get_error_rate(),
            "threshold": self.threshold_error_rate,
            "total_events": self.total_events,
            "error_events": self.error_events,
            "active_destination": self.main_table,
            "is_tripped": False,
            "evaluated_at": self.last_evaluated_at.isoformat(),
            "state_changed": prev_state != self.state
        }
        self.notify_listeners(result)
        return result

    def get_status(self) -> Dict[str, Any]:
        """Returns the current circuit breaker status snapshot."""
        return {
            "state": self.state.value,
            "error_rate": self.get_error_rate(),
            "threshold": self.threshold_error_rate,
            "total_events": self.total_events,
            "error_events": self.error_events,
            "main_table": self.main_table,
            "dlq_table": self.dlq_table,
            "active_destination": self.dlq_table if self.state == CircuitState.OPEN else self.main_table,
            "is_tripped": self.state == CircuitState.OPEN,
            "last_state_change": self.last_state_change.isoformat(),
            "last_evaluated_at": self.last_evaluated_at.isoformat()
        }

# Global singleton circuit breaker instance
circuit_breaker = CircuitBreakerManager(threshold_error_rate=2.0)
