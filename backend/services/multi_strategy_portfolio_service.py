"""
Multi-strategy structural portfolio construction service.

Generates an oversized candidate pool using multiple registered strategies,
combines and structurally deduplicates candidates, then uses PortfolioOptimizer
to select exactly N structurally diversified tickets.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Set, Any, Sequence
import hashlib
import copy
from collections import OrderedDict

from backend.core.algorithms.base import GameConfig, GeneratedTicket, ensure_unique_tickets
from backend.core.algorithms.registry import available_strategies, get_strategy
from backend.services.portfolio_optimizer import PortfolioOptimizer, PortfolioOptimizerResult


@dataclass(frozen=True)
class StrategyAllocation:
    """Allocation details for a single strategy."""
    strategy_id: int
    strategy_name: str
    requested: int
    generated: int
    derived_seed: int


@dataclass(frozen=True)
class ProvenanceRecord:
    """Provenance for a structurally unique ticket."""
    numbers: Tuple[int, ...]
    representative: GeneratedTicket
    strategy_ids: Tuple[int, ...]
    strategy_names: Tuple[str, ...]


@dataclass(frozen=True)
class MultiStrategyPortfolioResult:
    """Immutable result of multi-strategy portfolio construction."""
    game_name: str
    master_seed: int
    requested_candidate_count: int
    generated_candidate_count: int
    unique_structural_candidate_count: int
    duplicate_structural_candidate_count: int
    portfolio_size: int
    allocations: Tuple[StrategyAllocation, ...]
    selected_tickets: Tuple[GeneratedTicket, ...]
    provenance: Tuple[ProvenanceRecord, ...]
    optimizer_result: PortfolioOptimizerResult
    strategy_ids: Tuple[int, ...]
    strategy_names: Tuple[str, ...]


class MultiStrategyPortfolioService:
    """
    Generates a structurally diversified portfolio using multiple strategies.

    The service:
    1. Allocates candidate generation across selected strategies
    2. Generates candidates using each strategy
    3. Validates generated tickets
    4. Deduplicates structurally across strategies
    5. Uses PortfolioOptimizer to select the final portfolio
    """

    def __init__(self):
        """Initialize the multi-strategy portfolio service."""
        self._optimizer_cache = {}

    def _derive_strategy_seed(self, master_seed: int, strategy_id: int) -> int:
        """
        Derive a stable per-strategy seed from master seed and strategy ID.

        Uses SHA256 for cross-process determinism.
        """
        if not isinstance(master_seed, int) or isinstance(master_seed, bool):
            raise ValueError("master_seed must be an integer")
        if master_seed < 0:
            raise ValueError("master_seed must be non-negative")

        # Create deterministic seed
        seed_input = f"{master_seed}:{strategy_id}".encode('utf-8')
        hash_bytes = hashlib.sha256(seed_input).digest()
        # Convert first 8 bytes to integer
        derived = int.from_bytes(hash_bytes[:8], 'big')
        return derived

    def _normalize_strategy_ids(self, strategy_ids: Optional[Sequence[int]] = None) -> Tuple[int, ...]:
        """Normalize strategy IDs to canonical ascending order."""
        if strategy_ids is None:
            # Use all registered strategies
            all_strategies = available_strategies()
            return tuple(sorted(s['id'] for s in all_strategies))

        if not strategy_ids:
            raise ValueError("strategy_ids must not be empty")

        # Remove duplicates while preserving order for validation
        seen = set()
        unique_ids = []
        for sid in strategy_ids:
            if sid in seen:
                raise ValueError(f"duplicate strategy ID: {sid}")
            seen.add(sid)
            unique_ids.append(sid)

        # Validate all IDs are registered
        registered_ids = {s['id'] for s in available_strategies()}
        for sid in unique_ids:
            if sid not in registered_ids:
                raise ValueError(f"unknown strategy ID: {sid}")

        # Return sorted for canonical ordering
        return tuple(sorted(unique_ids))

    def _allocate_candidates(
        self,
        candidate_count: int,
        strategy_ids: Tuple[int, ...]
    ) -> Dict[int, int]:
        """
        Allocate candidates evenly across strategies.

        Remainder allocated in ascending strategy ID order.
        """
        num_strategies = len(strategy_ids)
        base_allocation = candidate_count // num_strategies
        remainder = candidate_count % num_strategies

        allocation = {}
        for idx, sid in enumerate(strategy_ids):
            count = base_allocation + (1 if idx < remainder else 0)
            allocation[sid] = count

        return allocation

    def _build_structural_key(self, ticket: GeneratedTicket) -> Tuple[int, ...]:
        """Build structural key from ticket numbers."""
        return tuple(sorted(ticket.numbers))

    def _deduplicate_structural(
        self,
        tickets: List[GeneratedTicket],
        strategy_id: int,
        strategy_name: str
    ) -> Tuple[List[GeneratedTicket], Dict[Tuple[int, ...], List[int]]]:
        """
        Deduplicate structurally within a single strategy's output.
        Returns unique tickets and provenance mapping.
        """
        seen: Dict[Tuple[int, ...], GeneratedTicket] = {}
        provenance: Dict[Tuple[int, ...], List[int]] = {}

        for ticket in tickets:
            key = self._build_structural_key(ticket)
            if key not in seen:
                seen[key] = ticket
                provenance[key] = [strategy_id]
            else:
                # Duplicate within same strategy - keep first, add to provenance
                if strategy_id not in provenance[key]:
                    provenance[key].append(strategy_id)

        return list(seen.values()), provenance

    def _combine_and_deduplicate(
        self,
        strategy_results: Dict[int, Tuple[List[GeneratedTicket], Dict[Tuple[int, ...], List[int]]]]
    ) -> Tuple[List[GeneratedTicket], Dict[Tuple[int, ...], List[int]]]:
        """
        Combine and deduplicate across all strategies in canonical order.

        Returns unique structural tickets and combined provenance.
        """
        combined: Dict[Tuple[int, ...], GeneratedTicket] = {}
        provenance: Dict[Tuple[int, ...], List[int]] = {}

        # Process strategies in canonical order
        for sid in sorted(strategy_results.keys()):
            tickets, strategy_prov = strategy_results[sid]
            for ticket in tickets:
                key = self._build_structural_key(ticket)
                if key not in combined:
                    combined[key] = ticket
                    provenance[key] = [sid]
                else:
                    # Add strategy to provenance if not already present
                    if sid not in provenance[key]:
                        provenance[key].append(sid)

        return list(combined.values()), provenance

    def build_portfolio(
        self,
        training_draws: Sequence[Any],
        game: GameConfig,
        portfolio_size: int = 33,
        candidate_count: int = 500,
        master_seed: int = 0,
        strategy_ids: Optional[Sequence[int]] = None
    ) -> MultiStrategyPortfolioResult:
        """
        Build a structurally diversified portfolio using multiple strategies.

        Args:
            training_draws: Historical draws for strategy generation
            game: Game configuration
            portfolio_size: Number of tickets to select (default 33)
            candidate_count: Total candidates to generate across strategies (default 500)
            master_seed: Master seed for determinism (default 0)
            strategy_ids: Optional list of strategy IDs to use (default all registered)

        Returns:
            MultiStrategyPortfolioResult with selected portfolio and metadata

        Raises:
            ValueError: For invalid inputs or insufficient candidates
        """
        # Validate inputs
        if portfolio_size < 1:
            raise ValueError(f"portfolio_size must be >= 1, got {portfolio_size}")

        if not isinstance(candidate_count, int) or isinstance(candidate_count, bool):
            raise ValueError("candidate_count must be an integer")

        if candidate_count < portfolio_size:
            raise ValueError(
                f"candidate_count ({candidate_count}) must be >= portfolio_size ({portfolio_size})"
            )

        if not isinstance(master_seed, int) or isinstance(master_seed, bool):
            raise ValueError("master_seed must be an integer")

        if master_seed < 0:
            raise ValueError("master_seed must be non-negative")

        # Normalize strategy IDs
        normalized_ids = self._normalize_strategy_ids(strategy_ids)
        num_strategies = len(normalized_ids)

        if candidate_count < num_strategies:
            raise ValueError(
                f"candidate_count ({candidate_count}) must be >= number of strategies ({num_strategies})"
            )

        # Snapshot training_draws
        training_snapshot = tuple(training_draws)

        # Get strategy info
        strategy_info = {}
        for sid in normalized_ids:
            strategy = get_strategy(sid)
            strategy_info[sid] = {
                'name': strategy.__class__.__name__,
                'instance': strategy
            }

        # Allocate candidates
        allocation = self._allocate_candidates(candidate_count, normalized_ids)

        # Generate candidates per strategy
        strategy_results: Dict[int, Tuple[List[GeneratedTicket], Dict[Tuple[int, ...], List[int]]]] = {}
        allocations_meta: List[StrategyAllocation] = []
        total_generated = 0

        for sid in normalized_ids:
            count = allocation[sid]
            derived_seed = self._derive_strategy_seed(master_seed, sid)
            strategy = strategy_info[sid]['instance']
            name = strategy_info[sid]['name']

            # Generate tickets with the strategy
            try:
                tickets = strategy.generate(
                    training_draws=training_snapshot,
                    ticket_count=count,
                    game=game,
                    seed=derived_seed,
                )
            except Exception as e:
                raise RuntimeError(f"Strategy {sid} ({name}) generation failed: {e}")

            # Enforce the shared strategy-output contract before
            # any structural deduplication. Complete-ticket duplicates
            # within one strategy are generator contract violations.
            try:
                validated_tickets = ensure_unique_tickets(
                    tickets,
                    expected_count=count,
                    game=game,
                )
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Strategy {sid} ({name}) produced invalid "
                    f"ticket output: {exc}"
                ) from exc

            total_generated += len(validated_tickets)

            # Structural identity is main numbers only. For games such
            # as Daily Grand, complete tickets with the same mains but
            # different Grand Numbers may collapse here; the first
            # deterministic representative is retained.
            unique_tickets, strategy_prov = (
                self._deduplicate_structural(
                    validated_tickets,
                    sid,
                    name,
                )
            )

            strategy_results[sid] = (
                unique_tickets,
                strategy_prov,
            )

            allocations_meta.append(
                StrategyAllocation(
                    strategy_id=sid,
                    strategy_name=name,
                    requested=count,
                    generated=len(validated_tickets),
                    derived_seed=derived_seed,
                )
            )

        # Combine and deduplicate across strategies
        combined_tickets, provenance = self._combine_and_deduplicate(strategy_results)

        unique_count = len(combined_tickets)
        duplicate_count = total_generated - unique_count

        if unique_count < portfolio_size:
            raise ValueError(
                f"Insufficient unique structural candidates: {unique_count} available, "
                f"{portfolio_size} required"
            )

        # Convert to list of lists for PortfolioOptimizer
        candidate_numbers = [list(ticket.numbers) for ticket in combined_tickets]

        # Run PortfolioOptimizer
        optimizer = PortfolioOptimizer(
            max_number=game.max_main_number,
            numbers_per_ticket=game.main_numbers_drawn
        )
        optimizer_result = optimizer.optimize(
            candidates=candidate_numbers,
            portfolio_size=portfolio_size,
            seed=master_seed
        )

        # Build selected tickets with provenance
        selected_tickets = []
        selected_provenance = []

        # Map numbers to tickets and provenance
        ticket_map = {
            self._build_structural_key(t): t for t in combined_tickets
        }
        provenance_map = {
            structural_key: tuple(prov)
            for structural_key, prov in provenance.items()
        }

        for numbers_tuple in optimizer_result.selected_tickets:
            numbers_list = list(numbers_tuple)
            # Find matching ticket
            matching_ticket = None
            for ticket in combined_tickets:
                if list(ticket.numbers) == numbers_list:
                    matching_ticket = ticket
                    break

            if matching_ticket is None:
                raise RuntimeError(f"Selected ticket {numbers_list} not found in candidates")

            selected_tickets.append(matching_ticket)

            # Build provenance
            key = self._build_structural_key(matching_ticket)
            prov_ids = provenance_map.get(key, ())
            # Get strategy names
            prov_names = []
            for sid in prov_ids:
                if sid in strategy_info:
                    prov_names.append(strategy_info[sid]['name'])

            selected_provenance.append(ProvenanceRecord(
                numbers=numbers_tuple,
                representative=matching_ticket,
                strategy_ids=tuple(prov_ids),
                strategy_names=tuple(prov_names)
            ))

        # Build result
        strategy_names = tuple(strategy_info[sid]['name'] for sid in normalized_ids)

        return MultiStrategyPortfolioResult(
            game_name=game.__class__.__name__ if hasattr(game, '__class__') else str(game),
            master_seed=master_seed,
            requested_candidate_count=candidate_count,
            generated_candidate_count=total_generated,
            unique_structural_candidate_count=unique_count,
            duplicate_structural_candidate_count=duplicate_count,
            portfolio_size=portfolio_size,
            allocations=tuple(allocations_meta),
            selected_tickets=tuple(selected_tickets),
            provenance=tuple(selected_provenance),
            optimizer_result=optimizer_result,
            strategy_ids=normalized_ids,
            strategy_names=strategy_names
        )
