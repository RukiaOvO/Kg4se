"""File storage utilities."""
import os
import hashlib
import aiofiles
from pathlib import Path
from typing import Optional
from config import settings


class Storage:
    """Handles file storage and checksum calculation."""
    
    # Characters not allowed in Windows filenames
    _INVALID_FILENAME_CHARS = r'[\\/:*?"<>|]'
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or settings.upload_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Remove or replace invalid characters from filename for cross-platform compatibility.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename safe for all operating systems
        """
        import re
        # Replace invalid characters with underscore
        sanitized = re.sub(self._INVALID_FILENAME_CHARS, '_', filename)
        # Remove multiple consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        # Ensure filename is not empty
        if not sanitized:
            sanitized = 'unnamed'
        return sanitized
    
    async def save_file(self, file_content: bytes, filename: str) -> tuple[str, str]:
        """
        Save file and return (file_path, checksum).
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            
        Returns:
            Tuple of (relative_path, sha256_checksum)
        """
        # Calculate checksum
        checksum = hashlib.sha256(file_content).hexdigest()
        
        # Create filename with checksum prefix to avoid collisions
        file_ext = Path(filename).suffix
        sanitized_stem = self._sanitize_filename(Path(filename).stem)
        safe_filename = f"{checksum[:16]}_{sanitized_stem}{file_ext}"
        file_path = self.base_dir / safe_filename
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_content)
        
        return str(file_path.resolve().relative_to(Path.cwd())), checksum
    
    async def save_file_streaming(self, file, filename: str) -> tuple[str, str, int]:
        """
        Save file from UploadFile stream and return (file_path, checksum).
        
        This method is memory-efficient for large files as it reads and writes in chunks.
        
        Args:
            file: UploadFile object from FastAPI
            filename: Original filename
            
        Returns:
            Tuple of (relative_path, sha256_checksum)
        """
        # Create filename with checksum prefix
        file_ext = Path(filename).suffix
        sanitized_stem = self._sanitize_filename(Path(filename).stem)
        
        # Generate a temporary filename first
        import uuid
        temp_filename = f"temp_{uuid.uuid4().hex[:16]}{file_ext}"
        temp_path = self.base_dir / temp_filename
        
        # Hash object for checksum calculation
        sha256_hash = hashlib.sha256()
        file_size = 0
        
        # Stream file to disk in chunks
        async with aiofiles.open(temp_path, 'wb') as f:
            while True:
                chunk = await file.read(8192)  # Read in 8KB chunks
                if not chunk:
                    break
                sha256_hash.update(chunk)
                file_size += len(chunk)
                await f.write(chunk)
        
        # Calculate final checksum
        checksum = sha256_hash.hexdigest()
        
        # Rename temp file to final name with checksum prefix
        safe_filename = f"{checksum[:16]}_{sanitized_stem}{file_ext}"
        final_path = self.base_dir / safe_filename
        
        # Remove existing file if exists
        if final_path.exists():
            final_path.unlink()
        
        # Rename temp file to final name
        temp_path.rename(final_path)
        
        return str(final_path.resolve().relative_to(Path.cwd())), checksum, file_size
    
    def calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of a file."""
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    def get_file_path(self, filename: str) -> Path:
        """Get full path for a filename."""
        return self.base_dir / filename
    
    def file_exists(self, checksum: str) -> Optional[str]:
        """Check if a file with given checksum exists, return path if found."""
        for file_path in self.base_dir.glob(f"{checksum[:16]}*"):
            return str(file_path)
        return None

    def delete_file(self, checksum: str) -> bool:
        """
        根据校验和删除文件。

        Args:
            checksum: 文件校验和

        Returns:
            是否成功删除
        """
        try:
            file_path = self.file_exists(checksum)
            if file_path and Path(file_path).exists():
                Path(file_path).unlink()
                print(f"✅ 已删除文件: {file_path}")
                return True
            return False
        except Exception as e:
            print(f"❌ 删除文件失败 (checksum: {checksum}): {e}")
            return False