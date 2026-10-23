"""S3–S8 成果读回核验：不打开文件就说"生成了"不算数。

对每个跑完的 run 目录做四件事：

1. 逐阶段列出实际写出的文件（按扩展名归类）；
2. 每个 DXF 用 ezdxf 独立读回，报实体数与图层数——解析不了就是坏图；
3. 每个 OBJ 独立读回，报顶点／面／包围盒与材质组；
4. 读工程量与材料表，报关键数字，并把"待核"项单独列出。

用法：
    python scripts/verify_s3_s8.py out/s38/home/run-xxx [更多 run 目录]

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

KIND = {".dxf": "CAD", ".obj": "模型", ".mtl": "材质", ".svg": "图", ".png": "图",
        ".md": "文档", ".json": "数据", ".pptx": "汇报", ".html": "汇报",
        ".py": "脚本", ".ifc": "BIM", ".blend": "场景"}


def _dxf(path: Path) -> dict:
    try:
        import ezdxf
    except Exception as exc:                      # noqa: BLE001
        return {"ok": False, "error": f"ezdxf 不可用：{exc}"}
    try:
        doc = ezdxf.readfile(str(path))
        msp = doc.modelspace()
        kinds: dict[str, int] = {}
        for e in msp:
            kinds[e.dxftype()] = kinds.get(e.dxftype(), 0) + 1
        return {"ok": True, "entities": sum(kinds.values()),
                "layers": len(doc.layers), "kinds": dict(sorted(kinds.items(),
                                                                key=lambda kv: -kv[1])[:6])}
    except Exception as exc:                      # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def _obj(path: Path) -> dict:
    v = 0
    f = 0
    mats: dict[str, int] = {}
    cur = ""
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("v "):
            p = line.split()
            v += 1
            xs.append(float(p[1]))
            ys.append(float(p[2]))
            zs.append(float(p[3]))
        elif line.startswith("usemtl "):
            cur = line.split(maxsplit=1)[1].strip()
        elif line.startswith("f "):
            f += 1
            mats[cur] = mats.get(cur, 0) + 1
    if not v or not f:
        return {"ok": False, "error": "空模型"}
    return {"ok": True, "vertices": v, "faces": f,
            "bbox_m": [round((max(xs) - min(xs)) / 1000, 1), round((max(ys) - min(ys)) / 1000, 1),
                       round((max(zs) - min(zs)) / 1000, 1)],
            "materials": dict(sorted(mats.items(), key=lambda kv: -kv[1])[:6])}


def _takeoff(path: Path) -> dict:
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:                      # noqa: BLE001
        return {"ok": False, "error": str(exc)}
    # 三种写法都见过：items/rows（清单式）、quantities（汇总式）、cost.lines（造价行）
    items = d.get("items") or d.get("rows") or []
    q = d.get("quantities") or {}
    lines = (d.get("cost") or {}).get("lines") or []
    pending = [i for i in items if str(i.get("status") or "").lower() in ("pending", "待核")]
    cost = d.get("cost") or {}
    total = None
    if cost.get("lines"):
        total = [round(sum(x.get("amount_low") or 0 for x in cost["lines"])),
                 round(sum(x.get("amount_high") or 0 for x in cost["lines"]))]
    return {"ok": True, "items": len(items) or len(lines),
            "pending": len(pending),
            "area_m2": q.get("floor_area_m2") or d.get("total_area_m2") or d.get("area_m2"),
            "quantities": {k: v for k, v in list(q.items())[:8]},
            "cost_cny": total,
            "cost_note": str(cost.get("basis") or "")[:60]}


def _read_run(run: Path) -> dict:
    out: dict = {"run": run.name, "stages": {}, "files": {}, "dxf": [], "obj": [],
                 "takeoff": None}
    for d in sorted(p for p in run.iterdir() if p.is_dir()):
        files = [p for p in d.rglob("*") if p.is_file()]
        kinds: dict[str, int] = {}
        for p in files:
            k = KIND.get(p.suffix.lower(), p.suffix.lower() or "?")
            kinds[k] = kinds.get(k, 0) + 1
        out["stages"][d.name] = {"files": len(files), "kinds": kinds}
        out["files"][d.name] = [str(p.relative_to(run)) for p in files]
    for p in run.rglob("*.dxf"):
        out["dxf"].append({"path": str(p.relative_to(run)), **_dxf(p)})
    for p in run.rglob("*.obj"):
        out["obj"].append({"path": str(p.relative_to(run)),
                           "size_kb": round(p.stat().st_size / 1024), **_obj(p)})
    tk = next(run.rglob("takeoff.json"), None)
    if tk is not None:
        out["takeoff"] = {"path": str(tk.relative_to(run)), **_takeoff(tk)}
    return out


def _print(rep: dict) -> None:
    print(f"\n{'=' * 78}\n{rep['run']}\n{'=' * 78}")
    for name, info in rep["stages"].items():
        kinds = " ".join(f"{k}×{v}" for k, v in sorted(info["kinds"].items(),
                                                       key=lambda kv: -kv[1]))
        print(f"  {name:<16} {info['files']:>3} 个文件　{kinds}")
    if rep["dxf"]:
        print("\n  DXF 读回：")
        for d in rep["dxf"]:
            if d["ok"]:
                print(f"    ok  {d['path']:<34} {d['entities']:>4} 实体 / "
                      f"{d['layers']} 图层 {d['kinds']}")
            else:
                print(f"    坏  {d['path']:<34} {d['error']}")
    if rep["obj"]:
        print("\n  OBJ 读回：")
        for o in rep["obj"]:
            if o["ok"]:
                print(f"    ok  {o['path']:<34} {o['vertices']:>5} 顶点 / {o['faces']:>5} 面　"
                      f"{o['bbox_m']} m　{o['size_kb']} KB")
                print(f"        材质组 {o['materials']}")
            else:
                print(f"    坏  {o['path']:<34} {o['error']}")
    if rep["takeoff"]:
        t = rep["takeoff"]
        print(f"\n  工程量：{t.get('items', '?')} 行清单，其中待核 {t.get('pending', '?')} 项；"
              f"建筑面积 {t.get('area_m2')} m²")
        if t.get("quantities"):
            print(f"        {t['quantities']}")
        if t.get("cost_cny"):
            print(f"        造价区间 {t['cost_cny'][0]:,} – {t['cost_cny'][1]:,} CNY"
                  f"（{t.get('cost_note')}）")


def main(argv: list[str]) -> int:
    runs = [Path(a) for a in argv[1:]]
    if not runs:
        base = ROOT / "out" / "s38"
        runs = sorted({p.parent for p in base.rglob("run-manifest.json")})
    reps = []
    for r in runs:
        rep = _read_run(r)
        reps.append(rep)
        _print(rep)
    (ROOT / "out" / "s38" / "verify.json").write_text(
        json.dumps(reps, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
