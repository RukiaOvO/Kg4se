"""File storage utilities."""
import os
import hashlib
import aiofiles
from pathlib import Path
from typing import Optional
from infra.config import settings


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

