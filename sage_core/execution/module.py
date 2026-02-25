"""Execution module — single enforcement point for execution timing.

Design contract:
    - Strategy: intent/signals at t using data <= t (no shift)
    - Meta allocator: combines strategy outputs using data <= t (no shift)
    - Asset allocator: target weights at t using raw asset returns <= t (no shift)
    - Risk caps / Vol targeting: transforms target weights at t using data <= t (no shift)
    - Engine / ExecutionModule: target weights at t -> held weights at t+1 (single shift)

Terminology:
    - Intent: model or rule output (scores or discrete signals)
    - Target weights: desired portfolio weights after exposure mapping
    - Held weights: actual portfolio weights after execution delay
"""

import logging
from typing import Callable, Optional

import numpy as np
import pandas as pd

from sage_core.execution.policy import ExecutionPolicy

logger = logging.getLogger(__name__)


class ExecutionModule:
    """Single enforcement point for execution timing in the Sage pipeline.

    All temporal lag logic is consolidated here. No strategy, allocator,
    or portfolio component should apply shift(1) or any other timing
    adjustment — the ExecutionModule is the only component that converts
    'decided at t' objects into 'effective at t+1' objects.

    Methods:
        apply_delay: Shift any time-indexed object by execution_delay_days.
        compute_meta_raw_returns: Compute strategy realized returns with proper lag.
        validate_alignment: Assert time-indexed objects share the same index.
        validate_intent: Structural validation of strategy output.

    Example:
        >>> from sage_core.execution import ExecutionPolicy, ExecutionModule
        >>> policy = ExecutionPolicy(execution_delay_days=1)
        >>> module = ExecutionModule(policy)
        >>> delayed_weights = module.apply_delay(target_weights)
    """

    def __init__(self, policy: ExecutionPolicy) -> None:
        """Initialize with an ExecutionPolicy.

        Args:
            policy: Temporal execution rules defining the lag.
        """
        self.policy = policy

    # ------------------------------------------------------------------
    # apply_delay
    # ------------------------------------------------------------------

    def apply_delay(
        self, obj: pd.Series | pd.DataFrame
    ) -> pd.Series | pd.DataFrame:
        """Shift a time-indexed object by execution_delay_days.

        This is the one canonical place where the execution delay is
        applied. Use it for:
        - intent -> delayed intent (signal-to-execution separation)
        - target weights -> held weights (the primary use case)
        - any other 'decided at t, effective at t+1' object

        Args:
            obj: Series or DataFrame indexed by date.

        Returns:
            Same type, shifted forward by execution_delay_days.
            The first execution_delay_days rows become NaN.

        Raises:
            TypeError: If obj is not a Series or DataFrame.
            ValueError: If obj has no DatetimeIndex.

        Example:
            >>> weights_at_t = pd.DataFrame({'SPY': [0.5, 0.6]},
            ...     index=pd.date_range('2020-01-01', periods=2))
            >>> held = module.apply_delay(weights_at_t)
            >>> held.iloc[0].isna().all()  # First row is NaN
            True
        """
        if not isinstance(obj, (pd.Series, pd.DataFrame)):
            raise TypeError(
                f"apply_delay expects Series or DataFrame, got {type(obj).__name__}"
            )
        if not isinstance(obj.index, pd.DatetimeIndex):
            raise ValueError(
                "apply_delay expects a DatetimeIndex, "
                f"got {type(obj.index).__name__}"
            )

        delay = self.policy.execution_delay_days
        if delay == 0:
            logger.warning(
                "execution_delay_days=0: same-bar execution. "
                "Use only for testing — this allows lookahead."
            )
            return obj

        return obj.shift(delay)

    # ------------------------------------------------------------------
    # compute_meta_raw_returns
    # ------------------------------------------------------------------

    def compute_meta_raw_returns(
        self,
        intent_by_asset: dict[str, pd.Series],
        raw_returns_by_asset: dict[str, pd.Series],
        *,
        exposure_mapper: Optional[Callable[[pd.Series], pd.Series]] = None,
    ) -> dict[str, pd.Series]:
        """Compute strategy-level realized returns with proper execution lag.

        Replaces every ``signals.shift(1) * raw_ret`` that previously lived
        inside strategy files. Internally delays intent via apply_delay(),
        optionally maps exposure, then multiplies by raw returns.

        Args:
            intent_by_asset: Per-asset intent series (discrete or continuous)
                at decision time t. Keys are asset symbols.
            raw_returns_by_asset: Per-asset raw return series. Keys are asset
                symbols and must match intent_by_asset.
            exposure_mapper: Optional callable that maps raw intent to exposure.
                For discrete {-1, 0, 1} intent, this can be None (identity).
                For continuous scores, use e.g. rank_then_normalize,
                zscore_then_clip, etc.

        Returns:
            Dict mapping symbol -> Series of strategy-level realized returns
            (meta_raw_ret). NaN during warmup + execution delay period.

        Raises:
            ValueError: If intent and return keys don't match.

        Example:
            >>> intent = {'SPY': pd.Series([1, -1, 1], index=dates)}
            >>> raw_ret = {'SPY': pd.Series([0.01, -0.02, 0.015], index=dates)}
            >>> meta = module.compute_meta_raw_returns(intent, raw_ret)
            >>> # meta['SPY'][0] is NaN (delay), meta['SPY'][1] = 1 * (-0.02)
        """
        intent_keys = set(intent_by_asset.keys())
        return_keys = set(raw_returns_by_asset.keys())
        if intent_keys != return_keys:
            raise ValueError(
                f"Intent keys {sorted(intent_keys)} do not match "
                f"return keys {sorted(return_keys)}"
            )

        result = {}
        for symbol in intent_by_asset:
            intent = intent_by_asset[symbol]
            raw_ret = raw_returns_by_asset[symbol]

            # Optionally map raw intent to exposure
            if exposure_mapper is not None:
                intent = exposure_mapper(intent)

            # Apply execution delay (the single canonical shift)
            delayed_intent = self.apply_delay(intent)

            # Realized return = delayed intent * raw return
            meta_raw_ret = delayed_intent * raw_ret
            result[symbol] = meta_raw_ret

        return result

    # ------------------------------------------------------------------
    # validate_alignment
    # ------------------------------------------------------------------

    def validate_alignment(
        self, index: pd.DatetimeIndex, *objs: pd.Series | pd.DataFrame
    ) -> None:
        """Assert all objects share the given DatetimeIndex.

        Prevents silent pandas alignment bugs — one of the sneakiest
        sources of leakage and incorrectness. Call this at key pipeline
        boundaries (e.g., before combining signals with returns).

        Checks:
        - Same index as the reference
        - Index is sorted
        - Index values are unique (no duplicate timestamps)
        - No timezone mismatches

        Args:
            index: Reference DatetimeIndex that all objects must match.
            *objs: Series or DataFrames to validate against the reference.

        Raises:
            TypeError: If index is not a DatetimeIndex.
            AlignmentError (ValueError): If any check fails.

        Example:
            >>> module.validate_alignment(prices.index, signals, weights)
        """
        if not isinstance(index, pd.DatetimeIndex):
            raise TypeError(
                f"Reference index must be DatetimeIndex, "
                f"got {type(index).__name__}"
            )

        # Check reference index properties
        if not index.is_monotonic_increasing:
            raise ValueError(
                "Reference index is not sorted (monotonic increasing)"
            )
        if not index.is_unique:
            raise ValueError(
                f"Reference index has {len(index) - index.nunique()} "
                f"duplicate timestamps"
            )

        ref_tz = index.tz

        for i, obj in enumerate(objs):
            label = f"object[{i}]"
            if isinstance(obj, (pd.Series, pd.DataFrame)):
                obj_index = obj.index
            else:
                raise TypeError(
                    f"{label} must be Series or DataFrame, "
                    f"got {type(obj).__name__}"
                )

            if not isinstance(obj_index, pd.DatetimeIndex):
                raise ValueError(
                    f"{label} does not have a DatetimeIndex "
                    f"(got {type(obj_index).__name__})"
                )

            # Check sorted
            if not obj_index.is_monotonic_increasing:
                raise ValueError(f"{label} index is not sorted")

            # Check unique
            if not obj_index.is_unique:
                raise ValueError(
                    f"{label} index has "
                    f"{len(obj_index) - obj_index.nunique()} duplicates"
                )

            # Check timezone consistency
            obj_tz = obj_index.tz
            if (ref_tz is None) != (obj_tz is None):
                raise ValueError(
                    f"{label} timezone mismatch: reference tz={ref_tz}, "
                    f"object tz={obj_tz}"
                )
            if ref_tz is not None and obj_tz is not None and ref_tz != obj_tz:
                raise ValueError(
                    f"{label} timezone mismatch: reference tz={ref_tz}, "
                    f"object tz={obj_tz}"
                )

            # Check same index
            if not obj_index.equals(index):
                # Provide useful diagnostics
                missing_from_obj = index.difference(obj_index)
                extra_in_obj = obj_index.difference(index)
                msg_parts = [f"{label} index does not match reference."]
                if len(missing_from_obj) > 0:
                    msg_parts.append(
                        f"  Missing {len(missing_from_obj)} timestamps "
                        f"(first: {missing_from_obj[0]})"
                    )
                if len(extra_in_obj) > 0:
                    msg_parts.append(
                        f"  Extra {len(extra_in_obj)} timestamps "
                        f"(first: {extra_in_obj[0]})"
                    )
                raise ValueError("\n".join(msg_parts))

    # ------------------------------------------------------------------
    # validate_intent
    # ------------------------------------------------------------------

    def validate_intent(
        self,
        intent_by_asset: dict[str, pd.Series],
        *,
        intent_type: str = "discrete",
    ) -> None:
        """Structural validation of strategy output.

        Validates that intent values are well-formed before they enter the
        execution pipeline. This catches bugs at strategy authoring time,
        not at portfolio construction time.

        Args:
            intent_by_asset: Dict mapping symbol -> intent Series.
            intent_type: Type of intent to validate.
                - ``"discrete"``: values must be in {-1, 0, 1}
                - ``"continuous"``: values must be finite numeric

        Raises:
            TypeError: If values are not pd.Series.
            ValueError: If values violate constraints for the intent type.

        Example:
            >>> module.validate_intent(
            ...     {'SPY': pd.Series([1, 0, -1])},
            ...     intent_type='discrete',
            ... )
        """
        valid_types = {"discrete", "continuous"}
        if intent_type not in valid_types:
            raise ValueError(
                f"intent_type must be one of {valid_types}, got '{intent_type}'"
            )

        for symbol, intent in intent_by_asset.items():
            # Type check
            if not isinstance(intent, pd.Series):
                raise TypeError(
                    f"Intent for '{symbol}' must be pd.Series, "
                    f"got {type(intent).__name__}"
                )

            # Index check
            if not isinstance(intent.index, pd.DatetimeIndex):
                raise ValueError(
                    f"Intent for '{symbol}' must have DatetimeIndex, "
                    f"got {type(intent.index).__name__}"
                )

            # Drop NaN (warmup period) before checking values
            non_null = intent.dropna()

            if len(non_null) == 0:
                continue  # All NaN — valid during warmup

            if intent_type == "discrete":
                valid_values = {-1, 0, 1}
                invalid = non_null[~non_null.isin(valid_values)]
                if len(invalid) > 0:
                    raise ValueError(
                        f"Discrete intent for '{symbol}' has invalid values. "
                        f"Expected {{-1, 0, 1}}, got {sorted(invalid.unique().tolist())} "
                        f"at {len(invalid)} positions"
                    )

            elif intent_type == "continuous":
                if not np.issubdtype(non_null.dtype, np.number):
                    raise ValueError(
                        f"Continuous intent for '{symbol}' must be numeric, "
                        f"got dtype={non_null.dtype}"
                    )
                non_finite = non_null[~np.isfinite(non_null)]
                if len(non_finite) > 0:
                    raise ValueError(
                        f"Continuous intent for '{symbol}' has "
                        f"{len(non_finite)} non-finite values "
                        f"(inf or -inf)"
                    )
