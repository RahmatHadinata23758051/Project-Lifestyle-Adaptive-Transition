from typing import Dict, List, Optional
from app.budget_selection.constants import (
    BudgetSelectionStatus,
    CandidateBudgetStatus,
    BudgetSelectionPolicy,
)
from app.budget_selection.models import (
    BudgetAwareSelectionInputDTO,
    BudgetAwareSelectionResultDTO,
    BudgetCandidateEvaluationDTO,
    DailyCandidateCombinationDTO,
)
from app.budget_selection.budget_context import derive_daily_budget_envelope
from app.budget_selection.filters import evaluate_candidate_price_and_budget
from app.budget_selection.combinations import generate_bounded_daily_combinations
from app.budget_selection.scoring import rank_combinations
from app.budget_selection.explanations import generate_selection_explanations
from app.price_knowledge.constants import PriceConfidence


def select_budget_aware_candidates(
    input_dto: BudgetAwareSelectionInputDTO,
) -> BudgetAwareSelectionResultDTO:
    """
    Pure zero-I/O budget-aware candidate selector (BUDGET_SELECTION_P1_4).
    Selects nutritionally valid food candidates that fit the user's declared food budget
    without overriding upstream nutrition or safety constraints.
    """
    policy_versions = {
        "engine_version": BudgetSelectionPolicy.VERSION,
        "allocation_policy": BudgetSelectionPolicy.ALLOCATION_POLICY_VERSION,
        "search_policy": BudgetSelectionPolicy.SEARCH_POLICY_VERSION,
        "ranking_policy": BudgetSelectionPolicy.RANKING_POLICY_VERSION,
    }

    # 1. Derive Daily Budget Envelope
    envelope_idr, env_status, env_msg = derive_daily_budget_envelope(input_dto.budget_context)
    if env_status in (
        BudgetSelectionStatus.BUDGET_NOT_CONFIGURED,
        BudgetSelectionStatus.BUDGET_ALREADY_EXCEEDED,
        BudgetSelectionStatus.NEEDS_MORE_BUDGET_DATA,
    ):
        explanations = generate_selection_explanations(env_status, envelope_idr, None)
        return BudgetAwareSelectionResultDTO(
            date=input_dto.date,
            logical_day_id=input_dto.logical_day_id,
            status=env_status,
            budget_envelope_idr=envelope_idr,
            selected_combination=None,
            alternatives=[],
            shortfall_idr=None,
            search_truncated=False,
            explanations=explanations,
            policy_versions=policy_versions,
        )

    # 2. Check Candidate Availability across active slots
    if not input_dto.slot_ids:
        return BudgetAwareSelectionResultDTO(
            date=input_dto.date,
            logical_day_id=input_dto.logical_day_id,
            status=BudgetSelectionStatus.NO_ELIGIBLE_CANDIDATES,
            budget_envelope_idr=envelope_idr,
            selected_combination=None,
            alternatives=[],
            shortfall_idr=None,
            search_truncated=False,
            explanations=["No active meal slots provided."],
            policy_versions=policy_versions,
        )

    evaluated_candidates_by_slot: Dict[str, List[BudgetCandidateEvaluationDTO]] = {}
    missing_candidates_slot = False
    missing_price_slot = False

    for slot_id in input_dto.slot_ids:
        slot_candidates = input_dto.candidates_by_slot.get(slot_id, [])
        if not slot_candidates:
            missing_candidates_slot = True
            break

        evaluated_list: List[BudgetCandidateEvaluationDTO] = []
        has_at_least_one_complete_cost = False

        for cand in slot_candidates:
            cost_est = input_dto.candidate_costs_by_candidate_id.get(cand.candidate_id)
            eval_dto = evaluate_candidate_price_and_budget(
                candidate=cand,
                cost_estimate=cost_est,
                budget_envelope_idr=envelope_idr,
                user_preferences=input_dto.user_preferences_by_food_id,
            )
            evaluated_list.append(eval_dto)
            if eval_dto.estimated_cost_idr is not None and eval_dto.budget_status != CandidateBudgetStatus.UNKNOWN_COST:
                has_at_least_one_complete_cost = True

        evaluated_candidates_by_slot[slot_id] = evaluated_list
        if not has_at_least_one_complete_cost:
            missing_price_slot = True

    if missing_candidates_slot:
        explanations = generate_selection_explanations(BudgetSelectionStatus.NO_ELIGIBLE_CANDIDATES, envelope_idr, None)
        return BudgetAwareSelectionResultDTO(
            date=input_dto.date,
            logical_day_id=input_dto.logical_day_id,
            status=BudgetSelectionStatus.NO_ELIGIBLE_CANDIDATES,
            budget_envelope_idr=envelope_idr,
            selected_combination=None,
            alternatives=[],
            shortfall_idr=None,
            search_truncated=False,
            explanations=explanations,
            policy_versions=policy_versions,
        )

    if missing_price_slot:
        explanations = generate_selection_explanations(BudgetSelectionStatus.NEEDS_MORE_PRICE_DATA, envelope_idr, None)
        return BudgetAwareSelectionResultDTO(
            date=input_dto.date,
            logical_day_id=input_dto.logical_day_id,
            status=BudgetSelectionStatus.NEEDS_MORE_PRICE_DATA,
            budget_envelope_idr=envelope_idr,
            selected_combination=None,
            alternatives=[],
            shortfall_idr=None,
            search_truncated=False,
            explanations=explanations,
            policy_versions=policy_versions,
        )

    # 3. Generate Bounded Daily Combinations
    combinations, search_truncated, eval_count, min_cost_found = generate_bounded_daily_combinations(
        slot_ids=input_dto.slot_ids,
        candidates_by_slot=evaluated_candidates_by_slot,
        budget_envelope_idr=envelope_idr or 0,
    )

    if not combinations:
        explanations = generate_selection_explanations(BudgetSelectionStatus.NEEDS_MORE_PRICE_DATA, envelope_idr, None)
        return BudgetAwareSelectionResultDTO(
            date=input_dto.date,
            logical_day_id=input_dto.logical_day_id,
            status=BudgetSelectionStatus.NEEDS_MORE_PRICE_DATA,
            budget_envelope_idr=envelope_idr,
            selected_combination=None,
            alternatives=[],
            shortfall_idr=None,
            search_truncated=search_truncated,
            explanations=explanations,
            policy_versions=policy_versions,
        )

    # 4. Rank Combinations (BUDGET_SELECTION_RANKING_V01)
    ranked = rank_combinations(combinations)
    feasible_combinations = [c for c in ranked if c.remaining_after_selection_idr >= 0]

    if feasible_combinations:
        best_selection = feasible_combinations[0]
        alternatives = feasible_combinations[1 : BudgetSelectionPolicy.MAX_SELECTION_RESULTS_RETURNED]

        final_status = (
            BudgetSelectionStatus.SELECTION_FOUND_WITH_LOW_CONFIDENCE_PRICE
            if (best_selection.uses_stale_prices or best_selection.price_confidence == PriceConfidence.LOW)
            else BudgetSelectionStatus.SELECTION_FOUND
        )

        explanations = generate_selection_explanations(final_status, envelope_idr, best_selection)

        return BudgetAwareSelectionResultDTO(
            date=input_dto.date,
            logical_day_id=input_dto.logical_day_id,
            status=final_status,
            budget_envelope_idr=envelope_idr,
            selected_combination=best_selection,
            alternatives=alternatives,
            shortfall_idr=None,
            search_truncated=search_truncated,
            explanations=explanations,
            policy_versions=policy_versions,
        )

    # No feasible combination found
    shortfall = None
    if min_cost_found is not None and envelope_idr is not None and min_cost_found > envelope_idr:
        shortfall = min_cost_found - envelope_idr

    explanations = generate_selection_explanations(
        BudgetSelectionStatus.NO_BUDGET_FEASIBLE_SELECTION, envelope_idr, None, shortfall_idr=shortfall
    )

    return BudgetAwareSelectionResultDTO(
        date=input_dto.date,
        logical_day_id=input_dto.logical_day_id,
        status=BudgetSelectionStatus.NO_BUDGET_FEASIBLE_SELECTION,
        budget_envelope_idr=envelope_idr,
        selected_combination=None,
        alternatives=[],
        shortfall_idr=shortfall,
        search_truncated=search_truncated,
        explanations=explanations,
        policy_versions=policy_versions,
    )
