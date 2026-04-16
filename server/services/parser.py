"""Document parsing services."""
import re
import os
import json
import csv
import time
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import fitz  # PyMuPDF
from models.document import Chunk
from bs4 import BeautifulSoup
from utils.logger import get_logger

logger = get_logger("services.parser")

try:
    from rapidocr_onnxruntime import RapidOCR
    RAPID_OCR_AVAILABLE = True
except ImportError:
    RAPID_OCR_AVAILABLE = False


class RapidOCRClient:
    def __init__(self):
        self.engine = None
        self._initialize()
    
    def _initialize(self):
        if not RAPID_OCR_AVAILABLE:
            logger.warning("[RapidOCR] Library not installed, OCR functionality disabled")
            return
        
        try:
            self.engine = RapidOCR()
            logger.info("[RapidOCR] Engine initialized successfully")
        except Exception as e:
            logger.error(f"[RapidOCR] Initialization failed: {e}")
    
    def recognize(self, image_bytes: bytes) -> str:
        if not self.engine:
            return ""
        
        try:
            result, _ = self.engine(image_bytes)
            
            if not result:
                logger.debug("[RapidOCR] No text detected")
                return ""
            
            text = "\n".join(item[1] for item in result)
            logger.debug(f"[RapidOCR] Recognition successful, text length: {len(text)}")
            return text
        
        except Exception as e:
            logger.error(f"[RapidOCR] Recognition error: {e}")
            return ""


rapid_ocr_client = RapidOCRClient()


class Parser:
    """Base parser class."""
    
    def __init__(self, chunk_size: int = 2000):
        """
        Initialize parser with chunk size.
        
        Args:
            chunk_size: Maximum characters per chunk (default: 2000)
        """
        self.chunk_size = chunk_size
    
    def parse(self, file_path: str) -> tuple[str, List[Chunk]]:
        """
        Parse document and return (text, chunks).
        
        Returns:
            Tuple of (full_text, list_of_chunks)
        """
        raise NotImplementedError
    
    def _smart_chunk(self, text: str, doc_id: str, base_chunk_id: str, meta: Dict[str, Any]) -> List[Chunk]:
        """
        Intelligently chunk text by size while preserving paragraph boundaries.
        
        Args:
            text: Text to chunk
            doc_id: Document ID
            base_chunk_id: Base chunk ID prefix
            meta: Base metadata for chunks
            
        Returns:
            List of Chunk objects
        """
        if not text.strip():
            return []
        
        chunks = []
        
        if len(text) <= self.chunk_size:
            return [Chunk(
                doc_id=doc_id,
                chunk_id=base_chunk_id,
                text=text.strip(),
                meta=meta.copy()
            )]
        
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip() and len(p.strip()) >= 10]
        
        if not paragraphs:
            sentences = re.split(r'[.!?。！？]\s+', text)
            paragraphs = [s.strip() for s in sentences if s.strip() and len(s.strip()) >= 10]
        
        current_chunk = []
        current_size = 0
        chunk_idx = 0
        
        for para in paragraphs:
            para_size = len(para)
            
            if para_size > self.chunk_size:
                if current_chunk:
                    chunks.append(Chunk(
                        doc_id=doc_id,
                        chunk_id=f"{base_chunk_id}_{chunk_idx}",
                        text="\n\n".join(current_chunk),
                        meta=meta.copy()
                    ))
                    chunk_idx += 1
                    current_chunk = []
                    current_size = 0
                
                sentences = re.split(r'[.!?。！？]\s+', para)
                for sent in sentences:
                    sent = sent.strip()
                    if not sent or len(sent) < 10:
                        continue
                    
                    if len(sent) > self.chunk_size:
                        words = sent.split()
                        current_sent = []
                        current_sent_size = 0
                        
                        for word in words:
                            word_size = len(word) + 1
                            if current_sent_size + word_size > self.chunk_size and current_sent:
                                chunks.append(Chunk(
                                    doc_id=doc_id,
                                    chunk_id=f"{base_chunk_id}_{chunk_idx}",
                                    text=" ".join(current_sent),
                                    meta=meta.copy()
                                ))
                                chunk_idx += 1
                                current_sent = []
                                current_sent_size = 0
                            
                            current_sent.append(word)
                            current_sent_size += word_size
                        
                        if current_sent:
                            current_chunk.append(" ".join(current_sent))
                            current_size += current_sent_size
                    else:
                        if current_size + len(sent) + 2 > self.chunk_size and current_chunk:
                            chunks.append(Chunk(
                                doc_id=doc_id,
                                chunk_id=f"{base_chunk_id}_{chunk_idx}",
                                text="\n\n".join(current_chunk),
                                meta=meta.copy()
                            ))
                            chunk_idx += 1
                            current_chunk = [sent]
                            current_size = len(sent)
                        else:
                            current_chunk.append(sent)
                            current_size += len(sent) + 2
            else:
                if current_size + para_size + 2 > self.chunk_size and current_chunk:
                    chunks.append(Chunk(
                        doc_id=doc_id,
                        chunk_id=f"{base_chunk_id}_{chunk_idx}",
                        text="\n\n".join(current_chunk),
                        meta=meta.copy()
                    ))
                    chunk_idx += 1
                    current_chunk = [para]
                    current_size = para_size
                else:
                    current_chunk.append(para)
                    current_size += para_size + 2
        
        if current_chunk:
            chunks.append(Chunk(
                doc_id=doc_id,
                chunk_id=f"{base_chunk_id}_{chunk_idx}",
                text="\n\n".join(current_chunk),
                meta=meta.copy()
            ))
        
        return chunks

    def _split_by_boundaries(self, text: str) -> List[str]:
        """Split text by meaningful boundaries."""
        patterns = [
            r'\n#{1,6}\s+',
            r'\n\s*[-*]\s+',
            r'\n\s*\d+\.\s+',
            r'\n{2,}',
        ]

        sections = []
        start = 0

        for pattern in patterns:
            matches = list(re.finditer(pattern, text))
            if matches:
                for match in matches:
                    end = match.start()
                    if end > start:
                        section = text[start:end].strip()
                        if section:
                            sections.append(section)
                    start = match.end()

        if start < len(text):
            section = text[start:].strip()
            if section:
                sections.append(section)

        return sections if sections else []

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        sentences = []
        current = ""

        for char in text:
            current += char
            if char in '.!?。！？':
                if len(current) > 1:
                    sentences.append(current.strip())
                    current = ""

        if current.strip():
            sentences.append(current.strip())

        return sentences if sentences else [text]


class PDFParser(Parser):
    """PDF parser using Docling with fallback to PyMuPDF + RapidOCR."""
    
    _docling_converter = None
    _docling_initialized = False
    _docling_lock = False
    
    def __init__(self, chunk_size: int = 2000, timeout: int = 300):
        """
        Initialize PDF parser.
        
        Args:
            chunk_size: Maximum characters per chunk (default: 2000)
            timeout: Maximum parsing time in seconds (default: 300)
        """
        super().__init__(chunk_size=chunk_size)
        self.use_ocr = RAPID_OCR_AVAILABLE and rapid_ocr_client.engine
        self._docling_available = self._check_docling()
        self._timeout = timeout
        self._parse_metrics = {}
        
        if self._docling_available and not PDFParser._docling_initialized:
            self._initialize_docling()
    
    def _check_docling(self) -> bool:
        """检查 Docling 是否可用（包括网络连接）"""
        try:
            from docling.document_converter import DocumentConverter
            # 尝试初始化转换器（会下载模型）
            if not PDFParser._docling_converter:
                PDFParser._docling_converter = DocumentConverter()
                logger.info("[Docling] Library available and initialized")
            return True
        except ImportError:
            logger.warning("[Docling] Library not installed")
            return False
        except Exception as e:
            logger.warning(f"[Docling] Initialization failed (network or model download issue): {e}")
            return False
    
    def _initialize_docling(self):
        """初始化 Docling 转换器（线程安全）"""
        if PDFParser._docling_lock:
            return
        
        PDFParser._docling_lock = True
        try:
            if not PDFParser._docling_converter:
                from docling.document_converter import DocumentConverter
                PDFParser._docling_converter = DocumentConverter()
                logger.info("[Docling] DocumentConverter initialized successfully")
                PDFParser._docling_initialized = True
        except Exception as e:
            logger.error(f"[Docling] Failed to initialize converter: {e}")
        finally:
            PDFParser._docling_lock = False
    
    def _get_docling_converter(self) -> Any:
        """获取 Docling 转换器实例"""
        if not PDFParser._docling_converter:
            self._initialize_docling()
        return PDFParser._docling_converter
    
    def parse(self, file_path: str) -> Tuple[str, List[Chunk]]:
        """Parse PDF file.优先使用 Docling，失败后回退到 PyMuPDF."""
        if self._docling_available:
            try:
                return self._parse_with_docling(file_path)
            except ImportError as e:
                logger.error(f"[Docling] Import failed: {e}")
            except MemoryError as e:
                logger.error(f"[Docling] Memory error processing {file_path}: {e}")
            except TimeoutError as e:
                logger.error(f"[Docling] Timeout processing {file_path}: {e}")
            except ValueError as e:
                logger.error(f"[Docling] Invalid document: {e}")
            except Exception as e:
                logger.error(f"[Docling] Unexpected error processing {file_path}: {e}")
                import traceback
                logger.debug(f"[Docling] Traceback: {traceback.format_exc()}")
        
        logger.info(f"[PDF Parser] Falling back to PyMuPDF for: {file_path}")
        return self._parse_with_pymupdf(file_path)
    
    def _parse_with_docling(self, file_path: str) -> Tuple[str, List[Chunk]]:
        """
        使用 Docling 解析 PDF（支持多模态内容）
        
        Args:
            file_path: PDF 文件路径
        
        Returns:
            (full_text, chunks) 元组
        
        Raises:
            RuntimeError: 如果转换器未初始化
            ValueError: 如果文档转换失败
            TimeoutError: 如果处理超时
        """
        start_time = time.time()
        logger.info(f"{'='*60}")
        logger.info(f"[Docling] Starting multi-modal document parsing: {file_path}")
        
        converter = self._get_docling_converter()
        if not converter:
            raise RuntimeError("[Docling] Converter not initialized")
        
        result = converter.convert(file_path)
        
        if result is None:
            raise ValueError(f"[Docling] Document conversion returned None: {file_path}")
        
        elements = getattr(result, 'elements', None)
        if elements is None:
            logger.warning(f"[Docling] No elements found in document: {file_path}")
            return "", []
            
        if not isinstance(elements, list):
            logger.warning(f"[Docling] Elements is not a list: {type(elements)}")
            return "", []
        
        element_types = {}
        try:
            from docling.datamodel.elements import Table, Figure, TextBlock
            element_types = {
                'TextBlock': TextBlock,
                'Table': Table,
                'Figure': Figure,
            }
            try:
                from docling.datamodel.elements import Equation
                element_types['Equation'] = Equation
            except ImportError:
                pass
            try:
                from docling.datamodel.elements import CodeBlock
                element_types['CodeBlock'] = CodeBlock
            except ImportError:
                pass
        except ImportError as e:
            logger.warning(f"[Docling] Failed to import element types: {e}")
        
        full_text = ""
        chunks = []
        doc_id = Path(file_path).stem
        element_count = {k: 0 for k in element_types.keys()}
        
        for element in elements:
            element_type_name = type(element).__name__
            page_num = getattr(element, 'page_num', 1)
            
            if isinstance(element, element_types.get('TextBlock', object)):
                text = getattr(element, 'content', '').strip()
                if text and len(text) >= 10:
                    full_text += text + "\n\n"
                    chunk = Chunk(
                        doc_id=doc_id,
                        chunk_id=f"text_{len(chunks)}",
                        text=text,
                        meta={
                            "type": "text",
                            "page": page_num,
                            "source": "docling",
                            "element_type": element_type_name
                        }
                    )
                    chunks.append(chunk)
                    element_count['TextBlock'] += 1
                    logger.debug(f"[Docling] Extracted text block: page={page_num}, length={len(text)}")
            
            elif isinstance(element, element_types.get('Table', object)):
                table_md = self._table_to_markdown(element)
                if table_md:
                    full_text += table_md + "\n\n"
                    chunk = Chunk(
                        doc_id=doc_id,
                        chunk_id=f"table_{len(chunks)}",
                        text=table_md,
                        meta={
                            "type": "table",
                            "page": page_num,
                            "source": "docling",
                            "element_type": element_type_name,
                            "rows": len(getattr(element, 'rows', [])),
                            "cols": self._count_table_cols(element)
                        }
                    )
                    chunks.append(chunk)
                    element_count['Table'] += 1
                    logger.debug(f"[Docling] Extracted table: page={page_num}")
            
            elif isinstance(element, element_types.get('Figure', object)):
                caption = getattr(element, 'caption', '') or ''
                description = getattr(element, 'description', '') or ''
                fig_type = getattr(element, 'figure_type', 'unknown')
                
                fig_text = self._build_figure_text(caption, description, fig_type)
                if fig_text:
                    full_text += fig_text + "\n\n"
                    chunk = Chunk(
                        doc_id=doc_id,
                        chunk_id=f"figure_{len(chunks)}",
                        text=fig_text,
                        meta={
                            "type": "figure",
                            "page": page_num,
                            "source": "docling",
                            "element_type": element_type_name,
                            "figure_type": fig_type,
                            "caption": caption,
                            "description": description
                        }
                    )
                    chunks.append(chunk)
                    element_count['Figure'] += 1
                    logger.debug(f"[Docling] Extracted figure: page={page_num}, type={fig_type}")
            
            elif isinstance(element, element_types.get('Equation', object)):
                latex = getattr(element, 'latex', '') or str(element)
                if latex and len(latex) >= 5:
                    full_text += f"$$ {latex} $$\n\n"
                    chunk = Chunk(
                        doc_id=doc_id,
                        chunk_id=f"equation_{len(chunks)}",
                        text=f"$$ {latex} $$",
                        meta={
                            "type": "equation",
                            "page": page_num,
                            "source": "docling",
                            "element_type": element_type_name,
                            "latex": latex
                        }
                    )
                    chunks.append(chunk)
                    element_count['Equation'] += 1
                    logger.debug(f"[Docling] Extracted equation: page={page_num}")
            
            elif isinstance(element, element_types.get('CodeBlock', object)):
                code_text = getattr(element, 'content', '') or ''
                language = getattr(element, 'language', 'unknown')
                if code_text and len(code_text) >= 10:
                    full_text += f"```\n{code_text}\n```\n\n"
                    chunk = Chunk(
                        doc_id=doc_id,
                        chunk_id=f"code_{len(chunks)}",
                        text=f"```\n{code_text}\n```",
                        meta={
                            "type": "code",
                            "page": page_num,
                            "source": "docling",
                            "element_type": element_type_name,
                            "language": language
                        }
                    )
                    chunks.append(chunk)
                    element_count['CodeBlock'] += 1
                    logger.debug(f"[Docling] Extracted code block: page={page_num}, language={language}")
            
            else:
                logger.debug(f"[Docling] Skipping unknown element type: {element_type_name}")
        
        parse_time = time.time() - start_time
        self._parse_metrics = {
            'parse_time': parse_time,
            'total_chunks': len(chunks),
            **element_count
        }
        
        logger.info(f"[Docling] Parsing completed in {parse_time:.2f}s")
        logger.info(f"[Docling] Element breakdown: {element_count}")
        logger.info(f"[Docling] Total chunks: {len(chunks)}")
        logger.info(f"{'='*60}")
        
        return full_text, chunks
    
    def _table_to_markdown(self, table) -> str:
        """将 Docling Table 元素转换为 Markdown 表格"""
        if not table:
            return ""
        
        try:
            rows = getattr(table, 'rows', None)
            if rows is None or not isinstance(rows, list) or len(rows) == 0:
                logger.debug("[Docling] Table has no rows")
                return ""
            
            md_lines = []
            header_processed = False
            
            header = getattr(table, 'header', None)
            if header:
                header_cells = getattr(header, 'cells', None)
                if header_cells and isinstance(header_cells, list):
                    headers = []
                    for cell in header_cells:
                        cell_text = getattr(cell, 'content', '').strip() or '---'
                        headers.append(cell_text)
                    md_lines.append(f"| {' | '.join(headers)} |")
                    md_lines.append(f"| {' | '.join(['---'] * len(headers))} |")
                    header_processed = True
            
            for row_idx, row in enumerate(rows):
                row_cells = getattr(row, 'cells', None)
                if not row_cells or not isinstance(row_cells, list):
                    continue
                
                if not header_processed and row_idx == 0:
                    headers = []
                    for cell in row_cells:
                        cell_text = getattr(cell, 'content', '').strip() or '---'
                        headers.append(cell_text)
                    md_lines.append(f"| {' | '.join(headers)} |")
                    md_lines.append(f"| {' | '.join(['---'] * len(headers))} |")
                    header_processed = True
                    continue
                
                cells = []
                for cell in row_cells:
                    cell_text = getattr(cell, 'content', '').strip() or ''
                    cell_text = cell_text.replace('\n', ' ')
                    cells.append(cell_text)
                
                if cells:
                    md_lines.append(f"| {' | '.join(cells)} |")
            
            return '\n'.join(md_lines)
        
        except Exception as e:
            logger.error(f"[Docling] Table conversion failed: {e}")
            import traceback
            logger.debug(f"[Docling] Table conversion traceback: {traceback.format_exc()}")
            return ""
    
    def _count_table_cols(self, table) -> int:
        """计算表格列数"""
        try:
            if hasattr(table, 'columns') and table.columns:
                return len(table.columns)
            if hasattr(table, 'rows') and table.rows:
                first_row = table.rows[0]
                if hasattr(first_row, 'cells'):
                    return len(first_row.cells)
        except Exception as e:
            logger.debug(f"[Docling] Failed to count table columns: {e}")
        return 0
    
    def _build_figure_text(self, caption: str, description: str, fig_type: str) -> str:
        """构建图表描述文本"""
        parts = []
        
        if fig_type:
            parts.append(f"图表类型: {fig_type}")
        if caption:
            parts.append(f"图表标题: {caption}")
        if description:
            parts.append(f"图表描述: {description}")
        
        return "\n".join(parts) if parts else ""
    
    def _parse_with_pymupdf(self, file_path: str) -> Tuple[str, List[Chunk]]:
        """使用 PyMuPDF 解析 PDF（回退方案）"""
        chunks = []
        full_text_parts = []
        doc_id = Path(file_path).stem
        
        with fitz.open(file_path) as doc:
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()

                if self.use_ocr and (not text.strip() or len(text.strip()) < 50):
                    ocr_text = self._extract_text_with_ocr(page)
                    if ocr_text and len(ocr_text) > len(text):
                        text = ocr_text
                        logger.debug(f"[OCR] Page {page_num + 1} extracted using RapidOCR")
                
                if not text.strip():
                    logger.debug(f"[PDF Parsing] Page {page_num + 1} has no valid text")
                    continue
                
                full_text_parts.append(text)
                
                page_chunks = self._smart_chunk(
                    text=text,
                    doc_id=doc_id,
                    base_chunk_id=f"c_{page_num}",
                    meta={
                        "page": page_num + 1,
                        "section": None,
                        "offset": [0, len(text)],
                        "ocr_used": self.use_ocr and (len(page.get_text()) < 50),
                        "source": "pymupdf"
                    }
                )
                chunks.extend(page_chunks)
        
        full_text = "\n\n".join(full_text_parts)
        return full_text, chunks
    
    def _extract_text_with_ocr(self, page) -> str:
        """Extract text from page images using RapidOCR."""
        if not self.use_ocr:
            return ""
        
        try:
            images = page.get_images(full=True)
            if not images:
                return ""
            
            ocr_text = []
            
            for img_index, img in enumerate(images):
                xref = img[0]
                base_image = page.parent.extract_image(xref)
                if not base_image:
                    continue
                
                img_bytes = base_image["image"]
                text = rapid_ocr_client.recognize(img_bytes)
                if text.strip():
                    ocr_text.append(text.strip())
            
            return "\n\n".join(ocr_text)
        
        except Exception as e:
            logger.error(f"[OCR] Page processing failed: {e}")
            return ""


class MarkdownParser(Parser):
    """Markdown parser."""
    
    def parse(self, file_path: str) -> Tuple[str, List[Chunk]]:
        """Parse Markdown file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        chunks = []
        doc_id = Path(file_path).stem
        
        sections = re.split(r'\n(#{1,6}\s+.+?)\n', content)
        
        current_section = None
        chunk_idx = 0
        
        for i, section in enumerate(sections):
            if i == 0:
                if section.strip():
                    section_chunks = self._smart_chunk(
                        text=section.strip(),
                        doc_id=doc_id,
                        base_chunk_id=f"c_{chunk_idx}",
                        meta={
                            "page": 1,
                            "section": None,
                            "offset": [0, len(section)]
                        }
                    )
                    chunks.extend(section_chunks)
                    chunk_idx += len(section_chunks)
                continue
            
            if section.startswith('#'):
                current_section = section.strip()
            else:
                if section.strip():
                    section_chunks = self._smart_chunk(
                        text=section.strip(),
                        doc_id=doc_id,
                        base_chunk_id=f"c_{chunk_idx}",
                        meta={
                            "page": 1,
                            "section": current_section,
                            "offset": [0, len(section)]
                        }
                    )
                    chunks.extend(section_chunks)
                    chunk_idx += len(section_chunks)
        
        return content, chunks


class TxtParser(Parser):
    """Plain text parser."""
    
    def parse(self, file_path: str) -> Tuple[str, List[Chunk]]:
        """Parse TXT file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        doc_id = Path(file_path).stem
        
        chunks = self._smart_chunk(
            text=content,
            doc_id=doc_id,
            base_chunk_id="c",
            meta={
                "page": 1,
                "section": None,
                "offset": [0, len(content)]
            }
        )
        
        return content, chunks


class WordParser(Parser):
    """Word document parser (DOC/DOCX)."""
    
    def parse(self, file_path: str) -> Tuple[str, List[Chunk]]:
        """Parse Word document."""
        try:
            import docx
        except ImportError:
            raise ImportError("python-docx is required for Word document parsing. Install with: pip install python-docx")
        
        doc = docx.Document(file_path)
        chunks = []
        full_text_parts = []
        doc_id = Path(file_path).stem
        
        all_text = []
        current_section = None
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text or len(text) < 10:
                continue
            
            section = para.style.name if para.style else None
            if section != current_section:
                if all_text:
                    section_text = "\n\n".join(all_text)
                    full_text_parts.append(section_text)
                    section_chunks = self._smart_chunk(
                        text=section_text,
                        doc_id=doc_id,
                        base_chunk_id=f"c_{len(chunks)}",
                        meta={
                            "page": 1,
                            "section": current_section,
                            "offset": [0, len(section_text)]
                        }
                    )
                    chunks.extend(section_chunks)
                    all_text = []
                current_section = section
            
            all_text.append(text)
        
        if all_text:
            section_text = "\n\n".join(all_text)
            full_text_parts.append(section_text)
            section_chunks = self._smart_chunk(
                text=section_text,
                doc_id=doc_id,
                base_chunk_id=f"c_{len(chunks)}",
                meta={
                    "page": 1,
                    "section": current_section,
                    "offset": [0, len(section_text)]
                }
            )
            chunks.extend(section_chunks)
        
        full_text = "\n\n".join(full_text_parts)
        return full_text, chunks


class CSVParser(Parser):
    """CSV file parser."""

    def parse(self, file_path: str) -> Tuple[str, List[Chunk]]:
        """Parse CSV file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)

        doc_id = Path(file_path).stem
        chunks = []

        if not rows:
            return "", chunks

        headers = rows[0]
        content_parts = []

        for idx, row in enumerate(rows[1:], 1):
            if not any(row):
                continue

            row_text = f"行 {idx}: " + " | ".join(
                f"{headers[i]}: {cell}" for i, cell in enumerate(row) if i < len(headers) and cell)
            content_parts.append(row_text)

            if idx % 10 == 0 or idx == len(rows) - 1:
                chunk_text = "\n".join(content_parts[-10:]) if len(content_parts) > 10 else "\n".join(content_parts)
                if chunk_text.strip():
                    chunks.append(Chunk(
                        doc_id=doc_id,
                        chunk_id=f"c_{idx // 10}",
                        text=chunk_text,
                        meta={
                            "page": 1,
                            "section": f"CSV数据块_{idx // 10}",
                            "offset": [0, len(chunk_text)],
                            "file_type": "csv",
                            "headers": headers,
                            "row_count": len(rows) - 1
                        }
                    ))

        full_text = "\n".join([f"表头: {headers}"] + content_parts)
        return full_text, chunks


class JSONParser(Parser):
    """JSON file parser."""

    def parse(self, file_path: str) -> Tuple[str, List[Chunk]]:
        """Parse JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        doc_id = Path(file_path).stem

        def json_to_text(obj, indent=0, path=""):
            text_parts = []
            prefix = "  " * indent

            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    if isinstance(value, (dict, list)):
                        text_parts.append(f"{prefix}{key}:")
                        text_parts.extend(json_to_text(value, indent + 1, current_path))
                    else:
                        text_parts.append(f"{prefix}{key}: {value}")
            elif isinstance(obj, list):
                for idx, item in enumerate(obj):
                    current_path = f"{path}[{idx}]" if path else f"[{idx}]"
                    if isinstance(item, (dict, list)):
                        text_parts.append(f"{prefix}项目 {idx}:")
                        text_parts.extend(json_to_text(item, indent + 1, current_path))
                    else:
                        text_parts.append(f"{prefix}项目 {idx}: {item}")
            else:
                text_parts.append(f"{prefix}{obj}")

            return text_parts

        text_lines = json_to_text(data)
        full_text = "\n".join(text_lines)

        chunks = self._smart_chunk(
            text=full_text,
            doc_id=doc_id,
            base_chunk_id="c",
            meta={
                "page": 1,
                "section": None,
                "offset": [0, len(full_text)],
                "file_type": "json",
                "structure_type": type(data).__name__
            }
        )

        return full_text, chunks


class ExcelParser(Parser):
    """Excel file parser."""

    def parse(self, file_path: str) -> Tuple[str, List[Chunk]]:
        """Parse Excel file."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required for Excel parsing. Install with: pip install pandas")

        try:
            excel_file = pd.ExcelFile(file_path)
            doc_id = Path(file_path).stem
            chunks = []
            full_text_parts = []

            for sheet_name in excel_file.sheet_names:
                df = excel_file.parse(sheet_name)

                sheet_text = f"工作表: {sheet_name}\n"
                sheet_text += f"形状: {df.shape[0]}行 × {df.shape[1]}列\n\n"

                sheet_text += "列名:\n"
                for col in df.columns:
                    sample = str(df[col].iloc[0]) if len(df) > 0 else "空"
                    sheet_text += f"  - {col}: {sample[:100]}...\n"

                sheet_text += "\n数据预览:\n"

                preview_rows = min(20, len(df))
                for i in range(preview_rows):
                    row_text = f"行 {i + 1}: "
                    row_data = []
                    for col in df.columns[:5]:
                        cell_value = str(df[col].iloc[i]) if i < len(df) else ""
                        row_data.append(f"{col}: {cell_value[:50]}")
                    row_text += " | ".join(row_data)
                    sheet_text += row_text + "\n"

                sheet_chunks = self._smart_chunk(
                    text=sheet_text,
                    doc_id=doc_id,
                    base_chunk_id=f"{sheet_name}_c",
                    meta={
                        "page": 1,
                        "section": sheet_name,
                        "offset": [0, len(sheet_text)],
                        "file_type": "excel",
                        "sheet_name": sheet_name,
                        "rows": df.shape[0],
                        "columns": df.shape[1],
                        "columns_list": list(df.columns)
                    }
                )
                chunks.extend(sheet_chunks)
                full_text_parts.append(sheet_text)

            full_text = "\n\n".join(full_text_parts)
            return full_text, chunks

        except Exception as e:
            raise ValueError(f"Failed to parse Excel file: {e}")


class WebParser(Parser):
    """Web page parser using requests and BeautifulSoup."""
    
    def parse(self, url: str) -> Tuple[str, List[Chunk]]:
        """Parse web page content."""
        try:
            import requests
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            main_content = soup.find('main') or soup.find('article') or soup.body
            
            if main_content:
                text = main_content.get_text(separator='\n', strip=True)
            else:
                text = soup.get_text(separator='\n', strip=True)
            
            text = re.sub(r'\n+', '\n\n', text)
            text = text.strip()
            
            doc_id = hash(url)
            chunks = self._smart_chunk(
                text=text,
                doc_id=str(doc_id),
                base_chunk_id="c",
                meta={
                    "page": 1,
                    "section": None,
                    "offset": [0, len(text)],
                    "url": url
                }
            )
            
            return text, chunks
        
        except Exception as e:
            logger.error(f"[Web Scraping] Failed to crawl: {e}")
            return "", []


class ParserFactory:
    """Factory for creating parsers based on file type."""
    
    @staticmethod
    def create_parser(kind: str, chunk_size: int = 2000) -> Parser:
        """
        Create parser based on document kind.
        
        Args:
            kind: Document type (pdf, md, txt, word)
            chunk_size: Maximum characters per chunk (default: 2000)
        """
        parsers = {
            "pdf": PDFParser,
            "md": MarkdownParser,
            "markdown": MarkdownParser,
            "txt": TxtParser,
            "word": WordParser,
            "csv": CSVParser,
            "json": JSONParser,
            "excel": ExcelParser,
            "xlsx": ExcelParser,
            "xls": ExcelParser,
            "web": WebParser,
        }
        
        parser_class = parsers.get(kind.lower())
        if not parser_class:
            raise ValueError(f"Unsupported document kind: {kind}")
        
        return parser_class(chunk_size=chunk_size)