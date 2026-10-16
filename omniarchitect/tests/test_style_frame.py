"""风格系统跑在主框架的八阶段流程之内 —— 用测试证明这一点。

阶段 id、阶段名与门禁名称的权威定义在 `omniarchitect.stages`。风格模块不得另立
一套流程，只能挂上去。这些测试就是那道栏杆：

* 每条挂钩指向的阶段与门禁都真实存在于阶段模型里；
* 挂钩里的门禁措辞与阶段模型**逐字符相同**；
* 没有挂钩虚构出阶段模型里不存在的阶段。

最后一条最要紧。挂钩写「G3 平面确认」而阶段模型写「G3 平面方案确认」，
这种漂移不会抛异常 —— 它一路飘到给业主的汇报里才被看见。

**合并前**这里比对的是一个导出快照文件（两个工程无法互相 import）；
**合并后**两个模块在同一个包里，比对就是直接引用，不再有任何中间副本。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from omniarchitect.stages import STAGES as CORE_STAGES                    # noqa: E402
from omniarchitect.style import hooks as W                                 # noqa: E402
from omniarchitect.style.resources import HOOKED_STAGES                    # noqa: E402

CORE_BY_ID = {s.id: s for s in CORE_STAGES}
CORE_IDS = tuple(s.id for s in CORE_STAGES)


# -- 与阶段模型的关系 -------------------------------------------------------

def test_the_stage_model_still_has_the_eight_stages():
    """如果阶段模型本身变了，风格模块的挂钩必须跟着被审视。"""
    assert CORE_IDS == ("S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8")


def test_hooks_only_touch_stages_the_stage_model_defines():
    for sid in W.STAGE_HOOKS:
        assert sid in CORE_BY_ID, f"挂钩了阶段模型未定义的阶段：{sid}"


def test_hooked_stages_exclude_intake_and_freeze():
    """S1 是需求接单、S6 是设计冻结 —— 这两步没有风格动作可挂。"""
    assert "S1" not in HOOKED_STAGES
    assert "S6" not in HOOKED_STAGES
    assert set(HOOKED_STAGES) <= set(CORE_IDS)
    assert set(W.STAGE_HOOKS) == set(HOOKED_STAGES)


def test_gate_wording_is_identical_to_the_stage_model():
    """这个文件存在的理由：门禁改名后无人察觉的那种漂移。"""
    for sid, h in W.STAGE_HOOKS.items():
        gate = CORE_BY_ID[sid].gate
        want = f"{gate.id} {gate.label}"
        assert h["gate"] == want, (
            f"{sid}: 挂钩写作 {h['gate']!r}，阶段模型是 {want!r}")


def test_stage_names_come_from_the_stage_model():
    for sid in HOOKED_STAGES:
        assert W.stage_name(sid) == CORE_BY_ID[sid].name


def test_gate_lookup_returns_the_stage_model_values():
    for s in CORE_STAGES:
        g = W.gate(s.id)
        assert g["id"] == s.gate.id
        assert g["label"] == s.gate.label
        assert g["approver"] == s.gate.approver


# -- 挂钩的形状 -------------------------------------------------------------

def test_hook_exposes_the_frame_it_was_built_from():
    """调用方必须能看见这套词汇的来源，而不是靠猜。"""
    for sid in HOOKED_STAGES:
        h = W.hook(sid)
        assert h["stage"] == sid
        assert h["stage_name"]
        assert h["gate_id"] and h["gate_label"] and h["gate_approver"]
        src = h["frame_source"]
        assert src["frame"] == "omniarchitect.stages"
        assert src["stage_count"] == len(CORE_STAGES)


def test_unhooked_stage_reports_explicitly_instead_of_guessing():
    h = W.hook("S1")
    assert h["actions"] == []
    assert "无风格系统挂钩" in h["name"]
    assert h["gate_id"] == "G1"          # 仍然是真实门禁，来自阶段模型


def test_unknown_stage_degrades_without_inventing_a_gate():
    h = W.hook("S99")
    assert h["actions"] == []
    assert h["gate_id"] == ""
    assert h["gate"] == ""


def test_all_hooks_is_ordered_and_complete():
    hooks = W.all_hooks()
    assert [h["stage"] for h in hooks] == list(HOOKED_STAGES)


def test_hook_api_names_all_resolve_to_real_callables():
    """挂钩声明了一个没人实现的 API，就是在配置里撒谎。"""
    for h in W.all_hooks():
        for name in h["api"]:
            assert callable(getattr(W, name, None)), \
                f"{h['stage']} 声明了并不存在的 API：{name}"


# -- 合并的证明 -------------------------------------------------------------

def test_the_frame_is_imported_not_copied():
    """合并前这里读的是一个导出快照文件；合并后必须没有任何快照。

    只要还有人把快照读回来，就说明存在第二个真相来源。
    """
    from omniarchitect.style import resources

    assert not hasattr(resources, "FRAME_FILE"), \
        "合并后不应再有框架快照文件（stages.py 已是唯一来源）"
    assert W._CORE_STAGES is CORE_STAGES, \
        "hooks 必须直接引用阶段模型对象，而不是它的副本"


def test_no_snapshot_file_lurks_in_the_schema_directory():
    from omniarchitect.paths import SCHEMAS

    stray = [p.name for p in SCHEMAS.glob("*frame*.json")]
    assert not stray, f"仍存在框架快照残件：{stray}"
