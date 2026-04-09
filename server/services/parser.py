"""Document parsing services."""
import re
from typing import List, Dict, Any
from pathlib import Path
import fitz  # PyMuPDF
from models.document import Chunk


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
    """PDF parser using PyMuPDF."""
    
    def parse(self, file_path: str) -> tuple[str, List[Chunk]]:
        """Parse PDF file."""
        doc = fitz.open(file_path)
        chunks = []
        full_text_parts = []
        doc_id = Path(file_path).stem
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            
            if not text.strip():
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
                    "offset": [0, len(text)]
                }
            )
            chunks.extend(page_chunks)
        
        doc.close()
        full_text = "\n\n".join(full_text_parts)
        return full_text, chunks


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
        }
        
        parser_class = parsers.get(kind.lower())
        if not parser_class:
            raise ValueError(f"Unsupported document kind: {kind}")
        
        return parser_class(chunk_size=chunk_size)

