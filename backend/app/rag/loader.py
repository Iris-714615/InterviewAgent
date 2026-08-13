"""文件加载与解析 - 支持 PDF / Word / TXT / Markdown"""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

from langchain_core.documents import Document


def _load_pdf(path: Path) -> Iterator[Document]:
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            yield Document(
                page_content=text,
                metadata={"source": path.name, "page": i + 1},
            )


def _load_docx(path: Path) -> Iterator[Document]:
    from docx import Document as DocxDocument
    doc = DocxDocument(str(path))
    for i, para in enumerate(doc.paragraphs):
        if para.text.strip():
            yield Document(
                page_content=para.text,
                metadata={"source": path.name, "line": i + 1},
            )


def _load_text(path: Path) -> Iterator[Document]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    yield Document(page_content=text, metadata={"source": path.name})


def load_file(path: str | Path) -> list[Document]:
    """根据扩展名解析文件,返回 Document 列表。"""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    suffix = path.suffix.lower()
    loaders = {
        ".pdf": _load_pdf,
        ".docx": _load_docx,
        ".doc": _load_docx,
        ".txt": _load_text,
        ".md": _load_text,
    }
    loader = loaders.get(suffix)
    if not loader:
        # 未知类型按文本处理
        loader = _load_text
    return list(loader(path))


def split_documents(
    documents: list[Document],
    chunk_size: int = 500,
    chunk_overlap: int = 80,
) -> list[Document]:
    """将文档切分为适合检索的片段。"""
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "!", "?", ".", " ", ""],
    )
    return splitter.split_documents(documents)
