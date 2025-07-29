"""
工具函数模块

提供跨平台的辅助函数，包括路径处理、权限管理、文件操作等。
"""

import os
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .exceptions import DiskSpaceError
from .exceptions import PermissionError as ClaudeWarpPermissionError
from .exceptions import SystemError


class LevelAlignFilter:
    """把 levelname 变成 '[DEBUG]    ' 这种固定总宽的左对齐字符串"""

    WIDTH = 8
    LEVEL_MAP = {
        "DEBUG": "DEBUG",
        "INFO": "INFO",
        "WARNING": "WARN",
        "ERROR": "ERROR",
        "CRITICAL": "CRIT",
        "FATAL": "FATAL",
        "NOTSET": "NOSET",
    }

    def filter(self, record):
        # 原始 level 名
        name = self.LEVEL_MAP.get(record.levelname, record.levelname or "UNKNOWN")
        # 构造固定宽度的前缀
        record.levelname_padded = f"[{name}]{' ' * (self.WIDTH - len(name) - 2)}"
        return True


def get_platform_info() -> Dict[str, str]:
    """获取平台信息

    Returns:
        Dict[str, str]: 包含平台信息的字典
    """
    return {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "architecture": platform.architecture()[0],
        "python_version": platform.python_version(),
    }


def is_windows() -> bool:
    """检查是否为Windows系统"""
    return platform.system().lower() == "windows"


def is_macos() -> bool:
    """检查是否为macOS系统"""
    return platform.system().lower() == "darwin"


def is_linux() -> bool:
    """检查是否为Linux系统"""
    return platform.system().lower() == "linux"


def get_home_directory() -> Path:
    """获取用户主目录

    Returns:
        Path: 用户主目录路径
    """
    return Path.home()


def get_config_directory(app_name: str = "claudewarp") -> Path:
    """获取应用配置目录

    Args:
        app_name: 应用名称

    Returns:
        Path: 配置目录路径
    """
    if is_windows():
        # Windows: %APPDATA%\claudewarp
        app_data = os.environ.get("APPDATA")
        if app_data:
            return Path(app_data) / app_name
        return get_home_directory() / f".{app_name}"

    else:
        # Linux: ~/.config/claudewarp (XDG Base Directory)
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            return Path(xdg_config) / app_name
        return get_home_directory() / ".config" / app_name


def get_cache_directory(app_name: str = "claudewarp") -> Path:
    """获取应用缓存目录

    Args:
        app_name: 应用名称

    Returns:
        Path: 缓存目录路径
    """
    if is_windows():
        # Windows: %LOCALAPPDATA%\claudewarp\cache
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / app_name / "cache"
        return get_home_directory() / f".{app_name}" / "cache"

    elif is_macos():
        # macOS: ~/Library/Caches/claudewarp
        return get_home_directory() / "Library" / "Caches" / app_name

    else:
        # Linux: ~/.cache/claudewarp (XDG Base Directory)
        xdg_cache = os.environ.get("XDG_CACHE_HOME")
        if xdg_cache:
            return Path(xdg_cache) / app_name
        return get_home_directory() / ".cache" / app_name


def ensure_directory(path: Union[str, Path], mode: int = 0o755) -> Path:
    """确保目录存在，如果不存在则创建

    Args:
        path: 目录路径
        mode: 目录权限（Unix系统）

    Returns:
        Path: 目录路径对象

    Raises:
        PermissionError: 无权限创建目录
        SystemError: 其他系统错误
    """
    path = Path(path)

    try:
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)

        # 在Unix系统上设置权限
        if not is_windows():
            os.chmod(path, mode)

        return path

    except OSError as e:
        if e.errno == 13:  # Permission denied
            raise ClaudeWarpPermissionError(str(path), "创建目录") from None
        else:
            raise SystemError(f"无法创建目录 {path}: {e}") from None


def set_file_permissions(file_path: Union[str, Path], mode: int = 0o600) -> bool:
    """设置文件权限

    Args:
        file_path: 文件路径
        mode: 权限模式（Unix系统）

    Returns:
        bool: 是否成功设置权限
    """
    if is_windows():
        # Windows系统使用ACL，这里简单返回True
        return True

    try:
        os.chmod(file_path, mode)
        return True
    except OSError:
        return False


def check_file_permissions(file_path: Union[str, Path]) -> Dict[str, bool]:
    """检查文件权限

    Args:
        file_path: 文件路径

    Returns:
        Dict[str, bool]: 权限信息字典
    """
    path = Path(file_path)

    permissions = {
        "exists": path.exists(),
        "readable": False,
        "writable": False,
        "executable": False,
    }

    if path.exists():
        permissions["readable"] = os.access(path, os.R_OK)
        permissions["writable"] = os.access(path, os.W_OK)
        permissions["executable"] = os.access(path, os.X_OK)

    return permissions


def get_file_size(file_path: Union[str, Path]) -> int:
    """获取文件大小

    Args:
        file_path: 文件路径

    Returns:
        int: 文件大小（字节）
    """
    try:
        return Path(file_path).stat().st_size
    except OSError:
        return 0


def get_disk_usage(path: Union[str, Path]) -> Dict[str, Union[int, float]]:
    """获取磁盘使用情况

    Args:
        path: 路径

    Returns:
        Dict[str, int]: 磁盘使用信息
    """
    try:
        usage = shutil.disk_usage(path)
        return {
            "total": usage.total,
            "used": usage.used,
            "free": usage.free,
            "percent_used": round((usage.used / usage.total) * 100, 2),
        }
    except OSError:
        return {"total": 0, "used": 0, "free": 0, "percent_used": 0}


def check_disk_space(path: Union[str, Path], required_space: int) -> bool:
    """检查磁盘剩余空间是否足够

    Args:
        path: 路径
        required_space: 需要的空间（字节）

    Returns:
        bool: 空间是否足够

    Raises:
        DiskSpaceError: 磁盘空间不足
    """
    usage = get_disk_usage(path)
    if usage["free"] < required_space:
        raise DiskSpaceError(str(path), required_space)
    return True


def safe_copy_file(src: Union[str, Path], dst: Union[str, Path], backup: bool = True) -> bool:
    """安全地复制文件

    Args:
        src: 源文件路径
        dst: 目标文件路径
        backup: 是否备份现有文件

    Returns:
        bool: 是否成功复制
    """
    src_path = Path(src)
    dst_path = Path(dst)

    try:
        # 检查源文件是否存在
        if not src_path.exists():
            return False

        # 如果目标文件存在且需要备份
        if dst_path.exists() and backup:
            backup_path = dst_path.with_suffix(
                f"{dst_path.suffix}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            shutil.copy2(dst_path, backup_path)

        # 确保目标目录存在
        ensure_directory(dst_path.parent)

        # 复制文件
        shutil.copy2(src_path, dst_path)

        return True

    except OSError:
        return False


def create_backup(
    file_path: Union[str, Path], backup_dir: Optional[Union[str, Path]] = None, max_backups: int = 5
) -> Optional[Path]:
    """创建文件备份

    Args:
        file_path: 要备份的文件路径
        backup_dir: 备份目录，如果为None则在原文件同目录
        max_backups: 最大备份数量

    Returns:
        Optional[Path]: 备份文件路径，失败返回None
    """
    src_path = Path(file_path)

    if not src_path.exists():
        return None

    try:
        # 确定备份目录
        if backup_dir:
            backup_path = Path(backup_dir)
        else:
            backup_path = src_path.parent / "backups"

        ensure_directory(backup_path)

        # 生成备份文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_path / f"{src_path.stem}_{timestamp}{src_path.suffix}"

        # 复制文件
        shutil.copy2(src_path, backup_file)

        # 清理旧备份
        cleanup_old_backups(backup_path, src_path.name, max_backups)

        return backup_file

    except OSError:
        return None


def cleanup_old_backups(backup_dir: Path, original_name: str, max_backups: int) -> None:
    """清理旧备份文件

    Args:
        backup_dir: 备份目录
        original_name: 原文件名
        max_backups: 最大保留备份数
    """
    try:
        # 获取备份文件列表
        pattern = f"{Path(original_name).stem}_*{Path(original_name).suffix}"
        backup_files = list(backup_dir.glob(pattern))

        # 按修改时间排序，最新的在前
        backup_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        # 删除超出数量限制的备份
        for old_backup in backup_files[max_backups:]:
            old_backup.unlink()

    except OSError:
        pass  # 忽略清理错误


def atomic_write(
    file_path: Union[str, Path], content: Union[str, bytes], encoding: str = "utf-8"
) -> bool:
    """原子性写入文件

    Args:
        file_path: 文件路径
        content: 文件内容
        encoding: 编码格式（文本模式）

    Returns:
        bool: 是否成功写入
    """
    path = Path(file_path)
    temp_path = None

    try:
        # 确保目录存在
        ensure_directory(path.parent)

        # 创建临时文件
        with tempfile.NamedTemporaryFile(
            mode="wb" if isinstance(content, bytes) else "w",
            dir=path.parent,
            delete=False,
            encoding=encoding if isinstance(content, str) else None,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(content)
            temp_file.flush()
            os.fsync(temp_file.fileno())

        # 原子性移动
        if is_windows():
            # Windows需要先删除目标文件
            if path.exists():
                path.unlink()

        temp_path.replace(path)
        return True

    except OSError:
        # 清理临时文件
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        return False


def run_command(
    command: List[str],
    cwd: Optional[Union[str, Path]] = None,
    timeout: Optional[int] = None,
    capture_output: bool = True,
) -> Dict[str, Any]:
    """运行系统命令

    Args:
        command: 命令列表
        cwd: 工作目录
        timeout: 超时时间（秒）
        capture_output: 是否捕获输出

    Returns:
        Dict[str, Any]: 命令执行结果
    """
    try:
        result = subprocess.run(
            command, cwd=cwd, timeout=timeout, capture_output=capture_output, text=True, check=False
        )

        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout if capture_output else "",
            "stderr": result.stderr if capture_output else "",
            "command": " ".join(command),
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": "Command timed out",
            "command": " ".join(command),
            "timeout": True,
        }
    except Exception as e:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
            "command": " ".join(command),
            "error": str(e),
        }


def format_file_size(size_bytes: Union[int, float]) -> str:
    """格式化文件大小

    Args:
        size_bytes: 字节数

    Returns:
        str: 格式化的大小字符串
    """
    if size_bytes == 0:
        return "0 B"

    sizes = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(sizes) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f} {sizes[i]}"


def validate_url(url: str) -> bool:
    """验证URL格式

    Args:
        url: URL字符串

    Returns:
        bool: URL是否有效
    """
    import re

    # 基本URL格式验证
    url_pattern = re.compile(
        r"^https?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain
        r"localhost|"  # localhost
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # IP
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )

    return bool(url_pattern.match(url))


def sanitize_filename(filename: str) -> str:
    """清理文件名，移除非法字符

    Args:
        filename: 原文件名

    Returns:
        str: 清理后的文件名
    """
    import re

    # 移除非法字符
    if is_windows():
        # Windows非法字符
        illegal_chars = r'[<>:"/\\|?*]'
    else:
        # Unix系统非法字符
        illegal_chars = r"[/\x00]"

    filename = re.sub(illegal_chars, "_", filename)

    # 移除首尾空格和点
    filename = filename.strip(" .")

    # 确保文件名不为空
    if not filename:
        filename = "untitled"

    return filename


def get_environment_info() -> Dict[str, Any]:
    """获取环境信息

    Returns:
        Dict[str, Any]: 环境信息字典
    """
    return {
        "platform": get_platform_info(),
        "python": {
            "version": sys.version,
            "executable": sys.executable,
            "path": sys.path[:3],  # 只取前3个路径
        },
        "environment": {
            "home": str(get_home_directory()),
            "config_dir": str(get_config_directory()),
            "cache_dir": str(get_cache_directory()),
        },
        "permissions": {
            "can_write_config": check_file_permissions(get_config_directory())["writable"],
            "can_write_cache": check_file_permissions(get_cache_directory())["writable"],
        },
    }


# 导出所有公共函数
__all__ = [
    # 平台检测
    "get_platform_info",
    "is_windows",
    "is_macos",
    "is_linux",
    # 路径处理
    "get_home_directory",
    "get_config_directory",
    "get_cache_directory",
    # 目录和权限
    "ensure_directory",
    "set_file_permissions",
    "check_file_permissions",
    # 文件操作
    "get_file_size",
    "safe_copy_file",
    "create_backup",
    "cleanup_old_backups",
    "atomic_write",
    # 磁盘空间
    "get_disk_usage",
    "check_disk_space",
    # 系统命令
    "run_command",
    # 工具函数
    "format_file_size",
    "validate_url",
    "sanitize_filename",
    # 环境信息
    "get_environment_info",
]
