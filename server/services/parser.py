"""Document parsing services."""
import re
import os
from typing import List, Dict, Any
from pathlib import Path
import fitz  # PyMuPDF
from models.document import Chunk
from bs4 import BeautifulSoup

# 百度 OCR
try:
    from aip import AipOcr
    BAIDU_OCR_AVAILABLE = True
except ImportError:
    BAIDU_OCR_AVAILABLE = False


class BaiduOCRClient:
    """百度 OCR API 客户端"""
    
    def __init__(self):
        self.client = None
        self._initialize()
    
    def _initialize(self):
        """初始化百度 OCR 客户端"""
        if not BAIDU_OCR_AVAILABLE:
            print("[百度OCR] 库未安装，OCR 功能将被禁用")
            return
        
        app_id = os.environ.get('BAIDU_OCR_APP_ID', '')
        api_key = os.environ.get('BAIDU_OCR_API_KEY', '')
        secret_key = os.environ.get('BAIDU_OCR_SECRET_KEY', '')

        # 检查配置完整性（不打印密钥内容）
        has_app_id = bool(app_id)
        has_api_key = bool(api_key)
        has_secret_key = bool(secret_key)
        
        if not has_app_id or not has_api_key or not has_secret_key:
            print("[百度OCR] 未配置 API 密钥，OCR 功能将被禁用")
            print(f"[百度OCR] 配置检查: APP_ID: {'✅' if has_app_id else '❌'}, API_KEY: {'✅' if has_api_key else '❌'}, SECRET_KEY: {'✅' if has_secret_key else '❌'}")
            return
        
        try:
            self.client = AipOcr(app_id, api_key, secret_key)
            print("[百度OCR] 客户端初始化成功")
        except Exception as e:
            # 隐藏异常详情中的敏感信息
            error_msg = str(e)
            # 替换可能泄露的密钥信息
            if api_key and api_key in error_msg:
                error_msg = error_msg.replace(api_key, "***")
            if secret_key and secret_key in error_msg:
                error_msg = error_msg.replace(secret_key, "***")
            print(f"[百度OCR] 初始化失败: {error_msg}")
    
    def recognize(self, image_bytes: bytes) -> str:
        """
        使用百度 OCR 识别图片文字
        
        Args:
            image_bytes: 图片字节数据
        
        Returns:
            识别出的文本
        """
        if not self.client:
            return ""
        
        try:
            # 调用通用文字识别（高精度版）
            result = self.client.basicAccurate(image_bytes)
            
            if 'words_result' not in result:
                print(f"[百度OCR] 识别失败: {result.get('error_msg', 'Unknown error')}")
                return ""
            
            # 提取识别结果
            text = "\n".join(item['words'] for item in result['words_result'])
            print(f"[百度OCR] 识别成功，文本长度: {len(text)}")
            return text
        
        except Exception as e:
            print(f"[百度OCR] 识别异常: {e}")
            return ""

# 全局 OCR 客户端实例
baidu_ocr_client = BaiduOCRClient()

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
        
        # If text is smaller than chunk_size, return as single chunk
        if len(text) <= self.chunk_size:
            return [Chunk(
                doc_id=doc_id,
                chunk_id=base_chunk_id,
                text=text.strip(),
                meta=meta.copy()
            )]
        
        # Split by paragraphs first
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip() and len(p.strip()) >= 10]
        
        if not paragraphs:
            # Fallback: split by sentences if no paragraphs
            import re
            sentences = re.split(r'[.!?。！？]\s+', text)
            paragraphs = [s.strip() for s in sentences if s.strip() and len(s.strip()) >= 10]
        
        current_chunk = []
        current_size = 0
        chunk_idx = 0
        
        for para in paragraphs:
            para_size = len(para)
            
            # If single paragraph exceeds chunk_size, split it
            if para_size > self.chunk_size:
                # Save current chunk if exists
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
                
                # Split large paragraph by sentences
                import re
                sentences = re.split(r'[.!?。！？]\s+', para)
                for sent in sentences:
                    sent = sent.strip()
                    if not sent or len(sent) < 10:
                        continue
                    
                    if len(sent) > self.chunk_size:
                        # Even sentence is too long, split by words
                        words = sent.split()
                        current_sent = []
                        current_sent_size = 0
                        
                        for word in words:
                            word_size = len(word) + 1  # +1 for space
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
                        # Sentence fits, add to current chunk
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
                            current_size += len(sent) + 2  # +2 for \n\n
            else:
                # Check if adding this paragraph would exceed chunk_size
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
                    current_size += para_size + 2  # +2 for \n\n
        
        # Add remaining chunk
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
        # 按照章节标记、标题等进行分割
        patterns = [
            r'\n#{1,6}\s+',  # Markdown 标题
            r'\n\s*[-*]\s+',  # 列表项
            r'\n\s*\d+\.\s+',  # 编号列表
            r'\n{2,}',  # 多个换行符
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

        # 添加剩余的文本
        if start < len(text):
            section = text[start:].strip()
            if section:
                sections.append(section)

        return sections if sections else []

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # 双语句子分割
        sentences = []
        current = ""

        for char in text:
            current += char
            if char in '.!?。！？':
                # 检查是否真的是句子结尾
                if len(current) > 1:
                    sentences.append(current.strip())
                    current = ""

        # 如果有剩余文本，作为最后一个句子
        if current.strip():
            sentences.append(current.strip())

        return sentences if sentences else [text]


class PDFParser(Parser):
    """PDF parser using Docling with fallback to PyMuPDF + Baidu OCR."""
    
    def __init__(self, chunk_size: int = 2000):
        """
        Initialize PDF parser.
        
        Args:
            chunk_size: Maximum characters per chunk (default: 2000)
        """
        super().__init__(chunk_size=chunk_size)
        # 检查百度 OCR 是否可用
        self.use_ocr = BAIDU_OCR_AVAILABLE and baidu_ocr_client.client
        # 检查 Docling 是否可用
        self._docling_available = self._check_docling()

    def _check_docling(self) -> bool:
        """检查 Docling 是否可用"""
        try:
            from docling.document_converter import DocumentConverter
            return True
        except ImportError:
            return False

    def parse(self, file_path: str) -> tuple[str, List[Chunk]]:
        """Parse PDF file.优先使用 Docling，失败后回退到 PyMuPDF."""
        # 首先尝试使用 Docling
        if self._docling_available:
            try:
                return self._parse_with_docling(file_path)
            except Exception as e:
                print(f"[Docling] 解析失败，回退到 PyMuPDF: {e}")
        
        # 使用 PyMuPDF 作为回退
        return self._parse_with_pymupdf(file_path)

    def _parse_with_docling(self, file_path: str) -> tuple[str, List[Chunk]]:
        """
        使用 Docling 解析 PDF（支持多模态内容）
        
        Args:
            file_path: PDF 文件路径
        
        Returns:
            (full_text, chunks) 元组
        """
        from docling.document_converter import DocumentConverter
        from docling.datamodel.document import Document
        from docling.datamodel.elements import Table, Figure, TextBlock, Equation, CodeBlock
        
        print(f"\n{'='*80}")
        print(f"🔍 [Docling] 开始解析多模态文档: {file_path}")
        
        converter = DocumentConverter()
        result: Document = converter.convert(file_path)
        
        full_text = ""
        chunks = []
        doc_id = Path(file_path).stem
        
        for element in result.elements:
            element_type = type(element).__name__
            page_num = getattr(element, 'page_num', 1)
            
            if isinstance(element, TextBlock):
                # 文本块处理
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
                            "element_type": element_type
                        }
                    )
                    chunks.append(chunk)
                    print(f"📝 [Docling] 提取文本块: page={page_num}, length={len(text)}")
            
            elif isinstance(element, Table):
                # 表格处理 → 转换为 Markdown 格式
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
                            "element_type": element_type,
                            "rows": len(element.rows) if hasattr(element, 'rows') else 0,
                            "cols": self._count_table_cols(element)
                        }
                    )
                    chunks.append(chunk)
                    print(f"📊 [Docling] 提取表格: page={page_num}, rows={chunk.meta['rows']}, cols={chunk.meta['cols']}")
            
            elif isinstance(element, Figure):
                # 图表处理 → 提取标题和描述
                caption = getattr(element, 'caption', '') or ''
                description = getattr(element, 'description', '') or ''
                fig_type = getattr(element, 'figure_type', 'unknown')
                
                # 构建图表描述文本
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
                            "element_type": element_type,
                            "figure_type": fig_type,
                            "caption": caption,
                            "description": description
                        }
                    )
                    chunks.append(chunk)
                    print(f"🖼️ [Docling] 提取图表: page={page_num}, type={fig_type}")
            
            elif isinstance(element, Equation):
                # 公式处理 → LaTeX 格式
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
                            "element_type": element_type,
                            "latex": latex
                        }
                    )
                    chunks.append(chunk)
                    print(f"∑ [Docling] 提取公式: page={page_num}, length={len(latex)}")
            
            elif isinstance(element, CodeBlock):
                # 代码块处理
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
                            "element_type": element_type,
                            "language": language
                        }
                    )
                    chunks.append(chunk)
                    print(f"💻 [Docling] 提取代码块: page={page_num}, language={language}")
        
        print(f"✅ [Docling] 解析完成: 共 {len(chunks)} 个多模态块")
        print(f"{'='*80}\n")
        
        return full_text, chunks
    
    def _table_to_markdown(self, table) -> str:
        """
        将 Docling Table 元素转换为 Markdown 表格
        
        Args:
            table: Docling Table 元素
        
        Returns:
            Markdown 格式的表格字符串
        """
        if not table:
            return ""
        
        try:
            rows = getattr(table, 'rows', [])
            if not rows:
                return ""
            
            md_lines = []
            
            # 处理表头
            header = getattr(table, 'header', None)
            if header and hasattr(header, 'cells'):
                headers = []
                for cell in header.cells:
                    cell_text = getattr(cell, 'content', '').strip() or '---'
                    headers.append(cell_text)
                md_lines.append(f"| {' | '.join(headers)} |")
                md_lines.append(f"| {' | '.join(['---'] * len(headers))} |")
            
            # 处理表格行
            for row in rows:
                if hasattr(row, 'cells'):
                    cells = []
                    for cell in row.cells:
                        cell_text = getattr(cell, 'content', '').strip() or ''
                        # 处理换行符
                        cell_text = cell_text.replace('\n', ' ')
                        cells.append(cell_text)
                    md_lines.append(f"| {' | '.join(cells)} |")
            
            return '\n'.join(md_lines)
        
        except Exception as e:
            print(f"⚠️ [Docling] 表格转换失败: {e}")
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
        except Exception:
            pass
        return 0
    
    def _build_figure_text(self, caption: str, description: str, fig_type: str) -> str:
        """
        构建图表描述文本
        
        Args:
            caption: 图表标题
            description: 图表描述
            fig_type: 图表类型
        
        Returns:
            结构化的图表描述文本
        """
        parts = []
        
        if fig_type:
            parts.append(f"图表类型: {fig_type}")
        if caption:
            parts.append(f"图表标题: {caption}")
        if description:
            parts.append(f"图表描述: {description}")
        
        if parts:
            return "\n".join(parts)
        return ""

    def _parse_with_pymupdf(self, file_path: str) -> tuple[str, List[Chunk]]:
        """使用 PyMuPDF 解析 PDF（回退方案）"""
        chunks = []
        full_text_parts = []
        doc_id = Path(file_path).stem
        
        # 使用 with 语句确保文档正确关闭
        with fitz.open(file_path) as doc:
            for page_num in range(len(doc)):
                page = doc[page_num]

                # 1. 首先尝试提取嵌入文本
                text = page.get_text()

                # 2. 如果文本很少或为空，尝试 OCR
                if self.use_ocr and (not text.strip() or len(text.strip()) < 50):
                    ocr_text = self._extract_text_with_ocr(page)
                    if ocr_text and len(ocr_text) > len(text):
                        text = ocr_text
                        print(f"[OCR] 页面 {page_num + 1} 使用百度 OCR 提取")
                
                # 3. 如果仍然没有文本，跳过该页面
                if not text.strip():
                    print(f"[PDF解析] 页面 {page_num + 1} 无有效文本")
                    continue
                
                full_text_parts.append(text)
                
                # Use smart chunking with page-aware metadata
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
        """Extract text from page images using Baidu OCR."""
        if not self.use_ocr:
            return ""
        
        try:
            # 获取页面中的所有图片
            images = page.get_images(full=True)
            if not images:
                return ""
            
            ocr_text = []
            
            for img_index, img in enumerate(images):
                # 获取图片信息
                xref = img[0]
                base_image = page.parent.extract_image(xref)
                if not base_image:
                    continue
                
                # 获取图片字节数据
                img_bytes = base_image["image"]
                
                # 使用百度 OCR 识别
                text = baidu_ocr_client.recognize(img_bytes)
                if text.strip():
                    ocr_text.append(text.strip())
            
            return "\n\n".join(ocr_text)
        
        except Exception as e:
            print(f"[OCR] 页面处理失败: {e}")
            return ""


class MarkdownParser(Parser):
    """Markdown parser."""
    
    def parse(self, file_path: str) -> tuple[str, List[Chunk]]:
        """Parse Markdown file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        chunks = []
        doc_id = Path(file_path).stem
        
        # Split by headers and paragraphs
        sections = re.split(r'\n(#{1,6}\s+.+?)\n', content)
        
        current_section = None
        chunk_idx = 0
        
        for i, section in enumerate(sections):
            if i == 0:
                # First section might be content without header
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
                # This is a header
                current_section = section.strip()
            else:
                # This is content
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

    def _extract_text_with_ocr(self, page) -> str:
        """Extract text from page images using OCR."""
        if not OCR_AVAILABLE:
            return ""
        
        try:
            # 获取页面中的所有图片
            images = page.get_images(full=True)
            if not images:
                return ""
            
            ocr_text = []
            
            for img_index, img in enumerate(images):
                # 获取图片信息
                xref = img[0]
                base_image = page.parent.extract_image(xref)
                if not base_image:
                    continue
                
                # 获取图片字节数据
                img_bytes = base_image["image"]
                width = base_image["width"]
                height = base_image["height"]
                
                try:
                    # 使用 PIL 打开图片
                    image = Image.frombytes(
                        "RGB", 
                        (width, height), 
                        img_bytes,
                        "raw",
                        "BGR"
                    )
                    
                    # 使用 Tesseract OCR 提取文本
                    # 添加中文和英文语言支持
                    text = pytesseract.image_to_string(image, lang="chi_sim+eng")
                    if text.strip():
                        ocr_text.append(text.strip())
                
                except Exception as e:
                    print(f"[OCR] 处理图片 {img_index} 失败: {e}")
                    continue
            
            return "\n\n".join(ocr_text)
        
        except Exception as e:
            print(f"[OCR] 页面处理失败: {e}")
            return ""


class TxtParser(Parser):
    """Plain text parser."""
    
    def parse(self, file_path: str) -> tuple[str, List[Chunk]]:
        """Parse TXT file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        doc_id = Path(file_path).stem
        
        # Use smart chunking
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
    
    def parse(self, file_path: str) -> tuple[str, List[Chunk]]:
        """Parse Word document."""
        try:
            import docx
        except ImportError:
            raise ImportError("python-docx is required for Word document parsing. Install with: pip install python-docx")
        
        doc = docx.Document(file_path)
        chunks = []
        full_text_parts = []
        doc_id = Path(file_path).stem
        
        # Collect all paragraphs first
        all_text = []
        current_section = None
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text or len(text) < 10:
                continue
            
            section = para.style.name if para.style else None
            if section != current_section:
                # Section changed, process accumulated text
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
        
        # Process remaining text
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

# 新增Csv文件解析器
class CSVParser(Parser):
    """CSV file parser."""

    def parse(self, file_path: str) -> tuple[str, List[Chunk]]:
        """Parse CSV file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)

        doc_id = Path(file_path).stem
        chunks = []

        if not rows:
            return "", chunks

        # 创建文本表示并带有表头
        headers = rows[0]
        content_parts = []

        for idx, row in enumerate(rows[1:], 1):
            if not any(row):  # 跳过空行
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


# 新增的JSON解析器
class JSONParser(Parser):
    """JSON file parser."""

    def parse(self, file_path: str) -> tuple[str, List[Chunk]]:
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

        # 创建 chunks
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


# 新增的Excel解析器
class ExcelParser(Parser):
    """Excel file parser."""

    def parse(self, file_path: str) -> tuple[str, List[Chunk]]:
        """Parse Excel file."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required for Excel parsing. Install with: pip install pandas")

        # 尝试读取Excel文件
        try:
            excel_file = pd.ExcelFile(file_path)
            doc_id = Path(file_path).stem
            chunks = []
            full_text_parts = []

            for sheet_name in excel_file.sheet_names:
                df = excel_file.parse(sheet_name)

                # 转为文本
                sheet_text = f"工作表: {sheet_name}\n"
                sheet_text += f"形状: {df.shape[0]}行 × {df.shape[1]}列\n\n"

                # 添加列描述
                sheet_text += "列名:\n"
                for col in df.columns:
                    sample = str(df[col].iloc[0]) if len(df) > 0 else "空"
                    sheet_text += f"  - {col}: {sample[:100]}...\n"

                sheet_text += "\n数据预览:\n"

                #转换前几行数据为文本
                preview_rows = min(20, len(df))
                for i in range(preview_rows):
                    row_text = f"行 {i + 1}: "
                    row_data = []
                    for col in df.columns[:5]:
                        cell_value = str(df[col].iloc[i]) if i < len(df) else ""
                        row_data.append(f"{col}: {cell_value[:50]}")
                    row_text += " | ".join(row_data)
                    sheet_text += row_text + "\n"

                #为每个工作表创建chunk
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
    
    def parse(self, url: str) -> tuple[str, List[Chunk]]:
        """Parse web page content."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取主要内容
            main_content = soup.find('main') or soup.find('article') or soup.body
            
            if main_content:
                text = main_content.get_text(separator='\n', strip=True)
            else:
                text = soup.get_text(separator='\n', strip=True)
            
            # 清理文本
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
            print(f"[网页解析] 爬取失败: {e}")
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

