"""S1 intelligent intake: discovery, interview, feasibility and opportunities.

This package is the *inside* of S1 — it does not replace the eight-stage
workflow, it gives S1 a professional front end. Everything here is
deterministic and rule based: the same project data always yields the same
questions, findings and opportunities, so results can be argued with and
tested.

Nothing here invents project facts. Missing information stays missing, and
every claim carries a confidence state.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from .diligence import (
    CONFIDENCE_STATES,
    BLOCKING_SCOPES,
    SourceEntry,
    UncertaintyItem,
    assess_sources,
    blocking_scope,
    precision_level,
    register_source,
    store_precision,
    register_uncertainty,
    uncertainty_register,
)
from .feasibility import CONFLICT_SEVERITIES, Conflict, run_feasibility
from .interview import (
    ANSWER_STATES,
    Answer,
    InterviewState,
    answer_question,
    completeness,
    current_questions,
    detect_start_mode,
    mark_asked,
    load_interview,
    next_questions,
    record_answer,
    save_interview,
    start_interview,
    summary as interview_summary,
)
from .needs import NeedRow, build_need_matrix
from .opportunities import OPPORTUNITY_FIELDS, Opportunity, find_opportunities
from .profiles import PROFILES, QUESTION_INDEX, SLOTS, Question, Profile, profile_for
from .report import S1_BUNDLE_FILES, generate_bundle
from .gate import (
    ApprovalOutcome,
    approval_summary_text,
    baseline_digest,
    check_baseline,
    decide_gate,
)

__all__ = [
    "CONFIDENCE_STATES", "BLOCKING_SCOPES", "SourceEntry", "UncertaintyItem",
    "assess_sources", "blocking_scope", "precision_level", "store_precision",
    "register_source", "register_uncertainty",
    "uncertainty_register",
    "CONFLICT_SEVERITIES", "Conflict", "run_feasibility",
    "ANSWER_STATES", "Answer", "InterviewState", "answer_question", "completeness",
    "detect_start_mode", "mark_asked",
    "current_questions", "load_interview", "next_questions", "record_answer",
    "save_interview", "start_interview", "interview_summary",
    "NeedRow", "build_need_matrix",
    "OPPORTUNITY_FIELDS", "Opportunity", "find_opportunities",
    "PROFILES", "QUESTION_INDEX", "SLOTS", "Question", "Profile", "profile_for",
    "S1_BUNDLE_FILES", "generate_bundle",
    "ApprovalOutcome", "approval_summary_text", "baseline_digest",
    "check_baseline", "decide_gate",
]
