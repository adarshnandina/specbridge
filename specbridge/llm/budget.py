"""Daily LLM budget guard."""

from __future__ import annotations

from collections.abc import Callable

from specbridge.errors import BudgetExceededError
from specbridge.logging_setup import get_logger

log = get_logger("specbridge.llm.budget")


class BudgetGuard:
    def __init__(self, daily_budget_usd: float, spent_today: Callable[[], float]) -> None:
        self.daily_budget = daily_budget_usd
        self.spent_today = spent_today

    def remaining(self) -> float:
        return self.daily_budget - self.spent_today()

    def check(self, estimated_cost: float = 0.0) -> None:
        spent = self.spent_today()
        if spent + estimated_cost > self.daily_budget:
            log.warning(
                "budget.exceeded", spent=spent, estimated=estimated_cost, budget=self.daily_budget
            )
            raise BudgetExceededError(
                f"Daily LLM budget of ${self.daily_budget:.2f} would be exceeded "
                f"(spent ${spent:.4f}, this call ~${estimated_cost:.4f})."
            )
