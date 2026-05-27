"""
PDF 解析层 — MinerU (magic-pdf) 为主，PyMuPDF 为 fallback。

输出统一的 ParseResult 格式，保留页码和坐标信息用于"来源可溯"。
"""
import os
import json
import subprocess
import tempfile
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

import fitz  # PyMuPDF

from backend.config import config


@dataclass
class FigureInfo:
    """图表信息"""
    index: int              # 图表序号
    caption: str            # 图表标题/说明
    page: int               # 所在页码
    bbox: tuple[float, float, float, float]  # 坐标 (x0, y0, x1, y1)
    image_path: str = ""    # 提取后的图片路径


@dataclass
class PageInfo:
    """单页信息"""
    page_num: int
    text: str
    figures: list[FigureInfo] = field(default_factory=list)


@dataclass
class ParseResult:
    """PDF 解析统一结果"""
    file_path: str
    page_count: int
    pages: list[PageInfo] = field(default_factory=list)
    markdown_text: str = ""
    figures: list[FigureInfo] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        """全文纯文本拼接"""
        return "\n\n".join(p.text for p in self.pages)


class PDFParser:
    """PDF 解析器：优先使用 MinerU，降级使用 PyMuPDF"""

    # ── MinerU 方式 ──────────────────────────────────────────

    def parse_with_mineru(self, pdf_path: str, output_dir: str | None = None) -> ParseResult:
        """通过 MinerU CLI 将 PDF 转为 Markdown。

        MinerU 输出目录结构:
          output_dir/<pdf_name>/
            ├── <pdf_name>.md          # 带图文引用的 Markdown
            ├── images/                # 提取的图表图片
            └── content_list.json      # 结构化内容清单
        """
        if output_dir is None:
            output_dir = str(config.CACHE_DIR)

        os.makedirs(output_dir, exist_ok=True)
        pdf_path = os.path.abspath(pdf_path)

        # 调用 magic-pdf 命令行
        cmd = [
            "magic-pdf",
            "-p", pdf_path,
            "-o", output_dir,
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"MinerU 解析失败: {e.stderr}\n"
                f"请确认已安装 MinerU: pip install magic-pdf"
            ) from e
        except FileNotFoundError:
            raise RuntimeError(
                "未找到 magic-pdf 命令。请先安装: pip install magic-pdf\n"
                "或参考: https://github.com/opendatalab/MinerU"
            )

        return self._read_mineru_output(pdf_path, output_dir)

    def _read_mineru_output(self, pdf_path: str, output_dir: str) -> ParseResult:
        """读取 MinerU 输出并转为 ParseResult"""
        pdf_name = Path(pdf_path).stem
        out_root = Path(output_dir) / pdf_name
        md_path = out_root / f"{pdf_name}.md"
        json_path = out_root / "content_list.json"

        result = ParseResult(file_path=pdf_path, page_count=0)

        # 读取 Markdown
        if md_path.exists():
            result.markdown_text = md_path.read_text(encoding="utf-8")

        # 读取结构化内容
        if json_path.exists():
            content = json.loads(json_path.read_text(encoding="utf-8"))
            result.page_count = len(content)
            for i, page_data in enumerate(content):
                page_info = PageInfo(page_num=i + 1)
                if isinstance(page_data, dict):
                    page_info.text = page_data.get("text", "")
                    for j, fig in enumerate(page_data.get("figures", [])):
                        page_info.figures.append(FigureInfo(
                            index=j + 1,
                            caption=fig.get("caption", ""),
                            page=i + 1,
                            bbox=tuple(fig.get("bbox", (0, 0, 0, 0))),
                            image_path=fig.get("path", ""),
                        ))
                result.pages.append(page_info)
                result.figures.extend(page_info.figures)
        else:
            # 没有 JSON 清单时从 markdown 文本估算
            if result.markdown_text:
                result.page_count = 1
                result.pages.append(PageInfo(page_num=1, text=result.markdown_text))

        return result

    # ── PyMuPDF fallback ─────────────────────────────────────

    def parse_with_pymupdf(self, pdf_path: str) -> ParseResult:
        """使用 PyMuPDF 提取文本和图表坐标（MinerU 不可用时的备选方案）"""
        doc = fitz.open(pdf_path)
        result = ParseResult(file_path=pdf_path, page_count=len(doc))

        for i, page in enumerate(doc):
            text = page.get_text("text") or ""
            page_info = PageInfo(page_num=i + 1, text=text)

            # 提取页面中的图片
            images = page.get_images(full=True)
            for j, img in enumerate(images):
                xref = img[0]
                base_image = doc.extract_image(xref)
                pix = fitz.Pixmap(base_image["image"])

                # 获取图片在页面上的位置
                rects = page.get_image_rects(xref)
                bbox = rects[0] if rects else fitz.Rect(0, 0, 0, 0)

                # 保存图片
                img_dir = Path(config.CACHE_DIR) / Path(pdf_path).stem / "images"
                img_dir.mkdir(parents=True, exist_ok=True)
                img_path = str(img_dir / f"figure_{i+1}_{j+1}.png")

                if pix.n < 5:  # RGB 或灰度
                    pix.save(img_path)
                else:          # CMYK
                    fitz.Pixmap(fitz.csRGB, pix).save(img_path)

                page_info.figures.append(FigureInfo(
                    index=j + 1,
                    caption=f"[Page {i+1} Figure {j+1}]",
                    page=i + 1,
                    bbox=(bbox.x0, bbox.y0, bbox.x1, bbox.y1),
                    image_path=img_path,
                ))

            result.pages.append(page_info)
            result.figures.extend(page_info.figures)

        doc.close()

        # 生成简单 Markdown
        md_lines = [f"# {Path(pdf_path).stem}\n"]
        for p in result.pages:
            md_lines.append(p.text)
            for f in p.figures:
                md_lines.append(f"\n![Figure {f.index}]({f.image_path})\n")
        result.markdown_text = "\n\n".join(md_lines)

        return result

    # ── 统一入口 ─────────────────────────────────────────────
    def parse(self, pdf_path: str, prefer_mineru: bool = True) -> ParseResult:
        """解析 PDF，自动选择引擎。

        Args:
            pdf_path: PDF 文件路径
            prefer_mineru: True=优先 MinerU, False=直接使用 PyMuPDF

        Returns:
            ParseResult 统一结果
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")

        if prefer_mineru:
            try:
                return self.parse_with_mineru(pdf_path)
            except (RuntimeError, FileNotFoundError) as e:
                print(f"[WARN] MinerU 不可用，降级使用 PyMuPDF: {e}")

        return self.parse_with_pymupdf(pdf_path)


# 全局单例
pdf_parser = PDFParser()
