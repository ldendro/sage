"""Execution policy configuration.

Defines temporal execution rules that govern when signals are computed,
when trades execute, and what price is used for fills.

The ExecutionPolicy is a Pydantic model that can be included in SystemConfig
and serialized with run artifacts for reproducibility.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Literal


class ExecutionPolicy(BaseModel):
    """Temporal execution rules for the backtesting engine.

    The execution policy defines the single canonical lag between
    decision time and execution time. All components in the pipeline
    (strategies, allocators, vol targeting) compute as-of time t using
    data <= t. The engine applies the execution delay to convert
    target weights at t into held weights at t + execution_delay_days.

    Attributes:
        signal_time: When signals are computed (e.g., at market close).
        execution_time: When trades execute (e.g., next market open).
        price_used: Which price is used for fills.
        execution_delay_days: Number of trading days to shift decisions.
            This is the single lag applied by the engine. Default is 1,
            meaning decisions made at t take effect at t+1.

    Example:
        >>> policy = ExecutionPolicy()
        >>> policy.execution_delay_days
        1
        >>> policy = ExecutionPolicy(execution_delay_days=2)
        >>> policy.execution_delay_days
        2
    """

    signal_time: Literal["close"] = Field(
        default="close",
        description="When signals are computed (market close)",
    )
    execution_time: Literal["next_open", "next_close"] = Field(
        default="next_open",
        description="When trades execute after signal computation",
    )
    price_used: Literal["open", "close"] = Field(
        default="open",
        description="Which price is used for trade fills",
    )
    execution_delay_days: int = Field(
        default=1,
        ge=0,
        le=10,
        description=(
            "Number of trading days to shift decisions. "
            "Decisions at t take effect at t + execution_delay_days. "
            "0 = same-bar execution (dangerous, use only for testing)."
        ),
    )

    model_config = ConfigDict(extra="forbid")
