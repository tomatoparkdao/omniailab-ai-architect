"""OmniArchitect — AI Chief Designer for architecture and interior design.

An eight-stage professional workflow, twenty-seven mapped capabilities, real
tool adapters, and one canonical spatial model every deliverable derives from.

Quick start
-----------
    python -m omniailab_ai_architect doctor
    python -m omniailab_ai_architect stages
    python -m omniailab_ai_architect demo
    python -m omniailab_ai_architect status  --project projects/demo-120
    python -m omniailab_ai_architect run     --project projects/demo-120 --from-stage S3
    python -m omniailab_ai_architect change  --project projects/demo-120 "我不喜欢客厅的电视背景墙"
"""
from __future__ import annotations

__version__ = "1.0.0"
SCHEMA_VERSION = "1.0.0"

from .errors import (  # noqa: F401
    AdapterUnavailable,
    GateBlocked,
    ModelError,
    OmniArchitectError,
    ValidationError,
)
from .model import (  # noqa: F401
    Artifact,
    ChangeEntry,
    Element,
    Level,
    Project,
    Space,
    load_project,
    summary,
    validate_all,
    validate_schema,
    validate_semantics,
)
from .paths import ROOT  # noqa: F401
from .planner import PlanGenerator, SchemeOptions, SchemeResult  # noqa: F401
from .registry import (  # noqa: F401
    ARCH_ATTRIBUTION,
    ARCH_FUSION,
    fusion_report,
    load_registry,
    registry_report,
)
from .revisions import (  # noqa: F401
    InvalidationReport,
    apply_geometry_change,
    apply_space_change,
    dependents_of,
    invalidate,
    mark_validated,
    register_artifact,
)
from .routing import RoutePlan, route  # noqa: F401
from .changes import (  # noqa: F401
    ChangeImpactReport,
    analyse as analyse_change,
    diagnose as diagnose_change,
    explain as explain_change,
)
from .stage_state import (  # noqa: F401
    confirm_stage,
    get_state,
    progress,
    reject_stage,
)
from .stages import (  # noqa: F401
    CAPABILITIES,
    CAPABILITY_BY_SLUG,
    DOWNSTREAM,
    GUARDRAILS,
    REQUIRES_CONFIRMED,
    STAGES,
    STAGE_ORDER,
    skills_for_stage,
    stages_for_skill,
    validate_catalog,
)
from .workflow import StageRunner, RunManifest, StageOutcome  # noqa: F401

DEFAULT_STAGES = list(STAGE_ORDER)
WorkflowRunner = StageRunner

__all__ = [
    "__version__", "SCHEMA_VERSION", "ROOT", "DEFAULT_STAGES",
    # model
    "Project", "Space", "Element", "Level", "Artifact", "ChangeEntry",
    "load_project", "validate_all", "summary",
    # planning
    "PlanGenerator", "SchemeOptions", "SchemeResult",
    # workflow
    "StageRunner", "WorkflowRunner", "RunManifest", "StageOutcome",
    # routing & stages
    "route", "RoutePlan", "STAGES", "STAGE_ORDER", "CAPABILITIES",
    "CAPABILITY_BY_SLUG", "REQUIRES_CONFIRMED", "DOWNSTREAM", "GUARDRAILS",
    "skills_for_stage", "stages_for_skill", "validate_catalog",
    # state
    "get_state", "confirm_stage", "reject_stage", "progress",
    # change impact
    "analyse_change", "diagnose_change", "explain_change", "ChangeImpactReport",
    # revisions
    "invalidate", "dependents_of", "apply_geometry_change", "apply_space_change",
    "register_artifact", "mark_validated", "InvalidationReport",
    # registry / provenance
    "registry_report", "load_registry", "fusion_report",
    "ARCH_ATTRIBUTION", "ARCH_FUSION",
    # errors
    "OmniArchitectError", "ModelError", "ValidationError",
    "AdapterUnavailable", "GateBlocked",
]
