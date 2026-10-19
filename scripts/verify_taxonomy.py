"""四类项目的分类路由抽查：S1 识别 → S2 方法 → S3 任务。

不是测试（测试在 `omniarchitect/tests/test_taxonomy.py`），而是**验收集**：
跑一遍能直接看到"同一句话进来，四个类型分别得到什么"。

用法：``python scripts/verify_taxonomy.py``

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from omniarchitect import taxonomy as tx  # noqa: E402
from omniarchitect.concept import deliberation as dl  # noqa: E402
from omniarchitect.concept.context import ConceptContext  # noqa: E402
from omniarchitect.intake import interview as iv  # noqa: E402
from omniarchitect.model import Project  # noqa: E402

CASES = (
    ("新建综合医院 300 床，含门诊、医技与住院", "architecture"),
    ("新建中小学 24 班，含食堂与体育馆", "architecture"),
    ("工业厂房及仓储物流，电子制造", "architecture"),
    ("既有酒店室内精装修，含大堂与客房", "interior"),
    ("商业中庭室内景观，需要补光与排水", "landscape"),
)


def main() -> int:
    print("分类路由抽查")
    print("=" * 78)
    for text, lead in CASES:
        p = Project(project_id="demo", name=text)
        p.meta = {}
        iv.ensure_intake(p)
        tax = iv.classification(p)
        codes = tax.get("codes") or []
        print(f"\n【{text}】")
        print(f"  S1 类型：{'、'.join(f'{c} {tx.resolve(c).name}' for c in codes) or '未识别'}")
        print(f"     性质：{'、'.join(tax.get('nature_labels') or []) or '—'}"
              f"　委托：{'、'.join(tax.get('commission_labels') or []) or '—'}")
        cap = tx.capability_of(codes)
        print(f"     能力边界：{cap['label']}")
        qs = [q.id for q in iv.next_questions(p, limit=99) if q.id.startswith("type.")]
        print(f"     行业专项问题：{'、'.join(qs) or '无（按宽口径）'}")

        ctx = ConceptContext(project_id="demo", name=text, taxonomy=tax,
                             taxonomy_codes=tuple(codes))
        # lead_id 由 ctx.lead 推出；抽查时注入，只为看"同一份分类在不同主导专业下
        # 给出什么"，不落盘、不参与任何判定。
        ctx.lead = {"project_lead_discipline": lead, "lead_label": lead}
        strategies = dl.build_strategies(ctx)
        if strategies:
            src = strategies[0].get("source") or "deliberated"
            print(f"  S2 方向（{src}）：")
            for s in strategies[:3]:
                print(f"     · {s['name']}｜{s['deliberation']['parti'][:46]}")
            gap = strategies[0]["deliberation"].get("gap") or ""
            if gap:
                print(f"     缺口：{gap[:60]}…")
        else:
            print("  S2 方向：该类型走原有原型/策略路径（未被模板替换）")

        tasks = tx.s3_tasks(codes, lead)
        print(f"  S3 任务（{lead}，共 {len(tasks)} 项）：")
        for t in tasks[:4]:
            print(f"     - {t}")
        if len(tasks) > 4:
            print(f"     … 另 {len(tasks) - 4} 项")
    print("\n" + "=" * 78)
    print("说明：抽查只验证路由与任务清单；没有几何时不生成平面，这是既有门禁行为。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
