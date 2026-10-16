"""The asset guard has to actually guard — not just report "all clear".

Two failure modes matter here and both are silent in production:

1. a large file slips in because the threshold was never enforced;
2. a render or a site photo gets committed because "it's only 200 KB".

The second one is the real trap. A 200 KB reference photograph is small enough
to pass a size check while still being exactly the kind of file that should not
be in a git history — undiffable, unverifiable by any test, and permanent. So
the guard checks size *and* type, and these tests prove both branches fire.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    "check_assets", ROOT / "scripts" / "check_assets.py")
CA = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CA)                                          # type: ignore[union-attr]

MB = 1024 * 1024


def _write(path: Path, size: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)


# -- thresholds ------------------------------------------------------------

def test_the_limit_is_one_megabyte():
    assert CA.MAX_FILE_BYTES == 1 * 1024 * 1024


def test_media_types_cover_every_group_that_matters_here():
    for kind in ("视频", "图片与位图", "音频", "压缩包", "字体", "Office 二进制"):
        assert kind in CA.MEDIA_TYPES, f"缺少类别：{kind}"
    assert "mp4" in CA.MEDIA_TYPES["视频"]
    assert "png" in CA.MEDIA_TYPES["图片与位图"]
    assert "pptx" in CA.MEDIA_TYPES["Office 二进制"]


# -- size branch -----------------------------------------------------------

def test_a_large_file_is_caught():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write(root / "docs" / "big.bin", int(1.2 * MB))
        rep = CA.scan(root=root)
        assert rep["oversize"], rep
        assert rep["findings"] > 0
        assert rep["conclusion"].startswith("不通过")


def test_exactly_one_megabyte_is_already_over_the_line():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write(root / "exactly.json", MB)
        rep = CA.scan(root=root)
        assert [f["path"] for f in rep["oversize"]] == ["exactly.json"]


def test_a_file_just_under_the_limit_is_allowed():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write(root / "just-under.json", MB - 1)
        rep = CA.scan(root=root)
        assert rep["oversize"] == []
        assert rep["findings"] == 0


# -- media branch ----------------------------------------------------------

def test_a_small_render_png_is_still_refused():
    """The whole point: 200 KB is not too big — but it is still an image."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write(root / "render.png", 200 * 1024)
        rep = CA.scan(root=root)
        assert rep["oversize"] == [], "200 KB 不该触发体积规则"
        assert [m["path"] for m in rep["media"]] == ["render.png"]
        assert rep["media"][0]["kind"] == "图片与位图"
        assert rep["findings"] == 1


def test_video_office_archives_and_fonts_are_refused():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for name in ("walk.mp4", "deck.pptx", "bundle.zip", "fam.ttf",
                     "scan.pdf", "photo.psd"):
            _write(root / name, 1024)
        rep = CA.scan(root=root)
        found = sorted(m["path"] for m in rep["media"])
        assert found == ["bundle.zip", "deck.pptx", "fam.ttf", "photo.psd",
                         "scan.pdf", "walk.mp4"], found


def test_pure_text_and_data_pass():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write(root / "project.json", 300 * 1024)
        (root / "README.md").write_text("# 说明\n", encoding="utf-8")
        _write(root / "model.py", 50 * 1024)
        _write(root / "plan.dxf", 80 * 1024)
        rep = CA.scan(root=root)
        assert rep["media"] == []
        assert rep["oversize"] == []
        assert rep["findings"] == 0


# -- scope -----------------------------------------------------------------

def test_runtime_output_directories_are_out_of_scope():
    """A 5 MB render inside out/ never reaches the remote — not a finding."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write(root / "out" / "render.png", 5 * MB)
        _write(root / "__pycache__" / "x.pyc", 5 * MB)
        _write(root / "projects" / "demo" / "concept-render" / "a.png", 5 * MB)
        (root / "keep.json").write_text("{}\n", encoding="utf-8")
        rep = CA.scan(root=root)
        assert rep["oversize"] == []
        assert rep["media"] == []


# -- the real repository ---------------------------------------------------

def test_this_repository_passes_its_own_guard():
    rep = CA.scan(root=ROOT)
    assert rep["findings"] == 0, rep["oversize"] + rep["media"]
    assert rep["files_scanned"] > 100


def test_every_committed_file_stays_well_under_the_limit():
    rep = CA.scan(root=ROOT)
    worst = rep["biggest"][0] if rep["biggest"] else {"kb": 0, "path": "-"}
    assert worst["kb"] < 200, f"最大文件已接近上限：{worst}"


def test_a_large_file_gets_the_data_conversion_advice():
    """Refusing a file is only useful if the report says what to do instead."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write(root / "notes.json", int(2 * MB))
        rep = CA.scan(root=root)
        assert rep["guidance"], "超限时必须给出替代做法"
        assert any("结构化数据" in g for g in rep["guidance"])
