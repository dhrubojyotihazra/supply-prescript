"""
solver.py
=========

SupplyPrescript - Week 2 Prescriptive Analytics Engine
Thin wrapper around the PuLP/CBC MILP solver backend.

Isolating solver configuration (backend choice, time limits, MIP gap,
verbosity) in its own module keeps ``optimizer.py`` focused on model
formulation and makes it straightforward to swap solvers (e.g. to a
commercial solver such as Gurobi/CPLEX in a later iteration) without
touching the model-building code.

Author: SupplyPrescript ML Engineering Team
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import pulp

logger = logging.getLogger("solver")

DEFAULT_TIME_LIMIT_SECONDS = 30
DEFAULT_MIP_GAP = 0.01  # Accept solutions within 1% of provable optimality.


@dataclass
class SolveOutcome:
    """Result of invoking the solver on a PuLP problem."""

    status: str
    elapsed_seconds: float
    objective_value: float


class MilpSolver:
    """Configures and invokes the CBC MILP solver for a PuLP problem."""

    def __init__(self, time_limit_seconds: int = DEFAULT_TIME_LIMIT_SECONDS,
                 mip_gap: float = DEFAULT_MIP_GAP, verbose: bool = False):
        self.time_limit_seconds = time_limit_seconds
        self.mip_gap = mip_gap
        self.verbose = verbose

    def solve(self, prob: pulp.LpProblem) -> SolveOutcome:
        """Solve the given PuLP problem and return a structured outcome."""
        solver = pulp.PULP_CBC_CMD(
            msg=1 if self.verbose else 0,
            timeLimit=self.time_limit_seconds,
            gapRel=self.mip_gap,
        )

        start = time.time()
        try:
            status_code = prob.solve(solver)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Solver raised an exception: %s", exc)
            raise
        elapsed = time.time() - start

        status_str = pulp.LpStatus[status_code]
        objective = float(pulp.value(prob.objective)) if prob.objective is not None else 0.0

        logger.info(
            "Solve complete: status=%s, objective=%.2f, elapsed=%.3fs",
            status_str, objective, elapsed,
        )
        return SolveOutcome(status=status_str, elapsed_seconds=round(elapsed, 4), objective_value=round(objective, 2))
