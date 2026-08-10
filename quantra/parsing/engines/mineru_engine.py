"""MinerU 引擎（可选，重型依赖，仓库已集成、本地无需安装）。

原理：DocLayout-YOLO（CNN 版面检测）→ PaddleOCR → 表格/公式识别（Transformer）→ Markdown。
调用方式（版本宽容）：
1. 优先命令行 `magic-pdf -p <pdf> -o <out> -m auto`（跨版本最稳定）；
2. 读取产物 content_list.json + .md，经 mineru_mapper 映射为统一 ParseResult；
3. 未安装时给出明确指引（本地开发不需要装，部署时再装）。
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from quantra.parsing.engines.mineru_mapper import map_mineru_output
from quantra.parsing.interfaces import BaseParser, ParseRequest, ParseResult


INSTALL_HINT = (
    "MinerU 未安装。仓库已完成集成，本地开发无需安装；"
    "部署/质量对比时执行：pip install \"magic-pdf[full]\""
)


class MinerUEngine(BaseParser):
    name = "mineru"

    def parse(self, request: ParseRequest) -> ParseResult:
        cli = shutil.which("magic-pdf")
        if cli is None:
            try:
                import magic_pdf  # noqa: F401
            except ImportError as exc:
                raise RuntimeError(INSTALL_HINT) from exc
            raise RuntimeError(
                "检测到 magic_pdf 已安装但没有 magic-pdf 命令行。"
                "请安装 CLI（pip install \"magic-pdf[full]\"）后重试，"
                "或调整本引擎使用 Python API（版本间 API 差异较大，见 mineru_mapper）。"
            )

        mode = "ocr" if request.mode == "ocr" else "auto"
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "mineru_out"
            cmd = [cli, "-p", str(request.source), "-o", str(out_dir), "-m", mode]
            subprocess.run(cmd, check=True, capture_output=True, text=True)  # noqa: S603
            artifacts = self._find_artifacts(out_dir)
            if not artifacts:
                raise RuntimeError(f"MinerU 运行完成但未找到产物（输出目录: {out_dir}）")
            content_list, markdown, stats = artifacts
            return map_mineru_output(content_list, markdown, str(request.source), stats=stats)

    @staticmethod
    def _find_artifacts(out_dir: Path) -> tuple[list, str, dict] | None:
        """在 MinerU 输出目录里递归定位 content_list.json 与 .md。"""
        content_path = next(out_dir.rglob("content_list.json"), None)
        md_path = next(out_dir.rglob("*.md"), None)
        if content_path is None or md_path is None:
            return None
        content_list = json.loads(content_path.read_text(encoding="utf-8"))
        markdown = md_path.read_text(encoding="utf-8")
        stats = {
            "pages": len(content_list) if isinstance(content_list, list) else 0,
            "blocks": 0,
            "tables": 0,
            "engine_note": "MinerU",
        }
        return content_list, markdown, stats
