"""
工具函数测试
测试跨平台辅助函数，包括路径处理、权限管理、文件操作等
"""

import platform
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from claudewarp.core.exceptions import DiskSpaceError, SystemError
from claudewarp.core.exceptions import PermissionError as ClaudeWarpPermissionError
from claudewarp.core.utils import (
    # 平台检测
    get_platform_info,
    is_windows,
    is_macos,
    is_linux,
    # 路径处理
    get_home_directory,
    get_config_directory,
    get_cache_directory,
    # 目录和权限
    ensure_directory,
    set_file_permissions,
    check_file_permissions,
    # 文件操作
    get_file_size,
    safe_copy_file,
    create_backup,
    cleanup_old_backups,
    atomic_write,
    # 磁盘空间
    get_disk_usage,
    check_disk_space,
    # 系统命令
    run_command,
    # 工具函数
    format_file_size,
    validate_url,
    sanitize_filename,
    get_environment_info,
    # 日志相关
    LevelAlignFilter,
)


class TestPlatformDetection:
    """平台检测功能测试"""

    def test_get_platform_info(self):
        """测试获取平台信息"""
        info = get_platform_info()
        
        required_keys = [
            "system", "release", "version", "machine", 
            "processor", "architecture", "python_version"
        ]
        
        for key in required_keys:
            assert key in info
            assert isinstance(info[key], str)

    @patch('platform.system')
    def test_is_windows(self, mock_system):
        """测试Windows平台检测"""
        mock_system.return_value = "Windows"
        assert is_windows() is True
        
        mock_system.return_value = "Linux"
        assert is_windows() is False

    @patch('platform.system')
    def test_is_macos(self, mock_system):
        """测试macOS平台检测"""
        mock_system.return_value = "Darwin"
        assert is_macos() is True
        
        mock_system.return_value = "Linux"
        assert is_macos() is False

    @patch('platform.system')
    def test_is_linux(self, mock_system):
        """测试Linux平台检测"""
        mock_system.return_value = "Linux"
        assert is_linux() is True
        
        mock_system.return_value = "Windows"
        assert is_linux() is False


class TestPathHandling:
    """路径处理功能测试"""

    @patch('pathlib.Path.home')
    def test_get_home_directory(self, mock_home):
        """测试获取用户主目录"""
        # Mock 主目录路径以避免访问真实系统目录
        mock_home_path = Path("/mock/home/user")
        mock_home.return_value = mock_home_path
        
        home_dir = get_home_directory()
        
        assert isinstance(home_dir, Path)
        assert home_dir == mock_home_path

    @patch('claudewarp.core.utils.is_windows')
    @patch('os.environ.get')
    def test_get_config_directory_windows(self, mock_env_get, mock_is_windows):
        """测试Windows配置目录获取"""
        mock_is_windows.return_value = True
        mock_env_get.return_value = r"C:\Users\test\AppData\Roaming"
        
        config_dir = get_config_directory("testapp")
        # 在测试环境中，Path会使用当前系统的路径分隔符，所以使用字符串比较
        assert str(config_dir).endswith("testapp")
        assert "AppData" in str(config_dir)
        assert "Roaming" in str(config_dir)

    @patch('claudewarp.core.utils.is_windows')
    @patch('os.environ.get')
    def test_get_config_directory_windows_no_appdata(self, mock_env_get, mock_is_windows):
        """测试Windows无APPDATA环境变量时的配置目录"""
        mock_is_windows.return_value = True
        mock_env_get.return_value = None
        
        with patch('claudewarp.core.utils.get_home_directory') as mock_home:
            mock_home.return_value = Path("/home/test")
            config_dir = get_config_directory("testapp")
            expected = Path("/home/test/.testapp")
            assert config_dir == expected

    @patch('claudewarp.core.utils.is_windows')
    @patch('os.environ.get')
    def test_get_config_directory_linux_xdg(self, mock_env_get, mock_is_windows):
        """测试Linux XDG配置目录"""
        mock_is_windows.return_value = False
        mock_env_get.return_value = "/home/test/.config"
        
        config_dir = get_config_directory("testapp")
        expected = Path("/home/test/.config/testapp")
        assert config_dir == expected

    @patch('claudewarp.core.utils.is_windows')
    @patch('os.environ.get')
    def test_get_config_directory_linux_no_xdg(self, mock_env_get, mock_is_windows):
        """测试Linux无XDG环境变量时的配置目录"""
        mock_is_windows.return_value = False
        mock_env_get.return_value = None
        
        with patch('claudewarp.core.utils.get_home_directory') as mock_home:
            mock_home.return_value = Path("/home/test")
            config_dir = get_config_directory("testapp")
            expected = Path("/home/test/.config/testapp")
            assert config_dir == expected

    @patch('claudewarp.core.utils.is_windows')
    @patch('claudewarp.core.utils.is_macos')
    @patch('os.environ.get')
    def test_get_cache_directory_macos(self, mock_env_get, mock_is_macos, mock_is_windows):
        """测试macOS缓存目录"""
        mock_is_windows.return_value = False
        mock_is_macos.return_value = True
        
        with patch('claudewarp.core.utils.get_home_directory') as mock_home:
            mock_home.return_value = Path("/Users/test")
            cache_dir = get_cache_directory("testapp")
            expected = Path("/Users/test/Library/Caches/testapp")
            assert cache_dir == expected


class TestDirectoryAndPermissions:
    """目录和权限管理测试"""

    def test_ensure_directory_new_directory(self, temp_dir):
        """测试创建新目录"""
        new_dir = temp_dir / "new_directory"
        result = ensure_directory(new_dir)
        
        assert result == new_dir
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_ensure_directory_existing_directory(self, temp_dir):
        """测试确保已存在的目录"""
        result = ensure_directory(temp_dir)
        assert result == temp_dir

    def test_ensure_directory_nested_path(self, temp_dir):
        """测试创建嵌套目录"""
        nested_dir = temp_dir / "level1" / "level2" / "level3"
        result = ensure_directory(nested_dir)
        
        assert result == nested_dir
        assert nested_dir.exists()
        assert nested_dir.is_dir()

    def test_ensure_directory_string_path(self, temp_dir):
        """测试使用字符串路径创建目录"""
        new_dir_str = str(temp_dir / "string_dir")
        result = ensure_directory(new_dir_str)
        
        assert isinstance(result, Path)
        assert result.exists()

    @patch('pathlib.Path.mkdir')
    def test_ensure_directory_permission_error(self, mock_mkdir, temp_dir):
        """测试创建目录时的权限错误"""
        mock_mkdir.side_effect = OSError()
        mock_mkdir.side_effect.errno = 13  # Permission denied
        
        new_dir = temp_dir / "forbidden"
        with pytest.raises(ClaudeWarpPermissionError):
            ensure_directory(new_dir)

    @patch('pathlib.Path.mkdir')
    def test_ensure_directory_system_error(self, mock_mkdir, temp_dir):
        """测试创建目录时的系统错误"""
        mock_mkdir.side_effect = OSError("Disk full")
        mock_mkdir.side_effect.errno = 28  # No space left on device
        
        new_dir = temp_dir / "failed"
        with pytest.raises(SystemError):
            ensure_directory(new_dir)

    def test_check_file_permissions_existing_file(self, temp_dir):
        """测试检查现有文件权限"""
        test_file = temp_dir / "test_file.txt"
        test_file.write_text("test content")
        
        permissions = check_file_permissions(test_file)
        
        assert permissions["exists"] is True
        assert permissions["readable"] is True
        assert permissions["writable"] is True
        # executable取决于文件权限，不做断言

    def test_check_file_permissions_nonexistent_file(self, temp_dir):
        """测试检查不存在文件的权限"""
        nonexistent_file = temp_dir / "nonexistent.txt"
        
        permissions = check_file_permissions(nonexistent_file)
        
        assert permissions["exists"] is False
        assert permissions["readable"] is False
        assert permissions["writable"] is False
        assert permissions["executable"] is False

    @patch('claudewarp.core.utils.is_windows')
    def test_set_file_permissions_windows(self, mock_is_windows, temp_dir):
        """测试在Windows上设置文件权限"""
        mock_is_windows.return_value = True
        
        test_file = temp_dir / "test_file.txt"
        test_file.write_text("test")
        
        result = set_file_permissions(test_file, 0o600)
        assert result is True  # Windows上总是返回True

    @patch('claudewarp.core.utils.is_windows')
    @patch('os.chmod')
    def test_set_file_permissions_unix_success(self, mock_chmod, mock_is_windows, temp_dir):
        """测试在Unix系统上成功设置文件权限"""
        mock_is_windows.return_value = False
        mock_chmod.return_value = None
        
        test_file = temp_dir / "test_file.txt"
        test_file.write_text("test")
        
        result = set_file_permissions(test_file, 0o600)
        assert result is True
        mock_chmod.assert_called_once_with(test_file, 0o600)

    @patch('claudewarp.core.utils.is_windows')
    @patch('os.chmod')
    def test_set_file_permissions_unix_error(self, mock_chmod, mock_is_windows, temp_dir):
        """测试在Unix系统上设置权限失败"""
        mock_is_windows.return_value = False
        mock_chmod.side_effect = OSError("Permission denied")
        
        test_file = temp_dir / "test_file.txt"
        test_file.write_text("test")
        
        result = set_file_permissions(test_file, 0o600)
        assert result is False


class TestFileOperations:
    """文件操作测试"""

    def test_get_file_size_existing_file(self, temp_dir):
        """测试获取现有文件大小"""
        test_file = temp_dir / "test_file.txt"
        content = "This is test content"
        test_file.write_text(content, encoding="utf-8")
        
        size = get_file_size(test_file)
        assert size == len(content.encode("utf-8"))

    def test_get_file_size_nonexistent_file(self, temp_dir):
        """测试获取不存在文件的大小"""
        nonexistent_file = temp_dir / "nonexistent.txt"
        size = get_file_size(nonexistent_file)
        assert size == 0

    def test_safe_copy_file_success(self, temp_dir):
        """测试成功复制文件"""
        src_file = temp_dir / "source.txt"
        dst_file = temp_dir / "destination.txt"
        content = "Test content for copying"
        
        src_file.write_text(content)
        
        result = safe_copy_file(src_file, dst_file)
        
        assert result is True
        assert dst_file.exists()
        assert dst_file.read_text() == content

    def test_safe_copy_file_with_backup(self, temp_dir):
        """测试复制文件时备份现有文件"""
        src_file = temp_dir / "source.txt"
        dst_file = temp_dir / "destination.txt"
        
        # 创建源文件和目标文件
        src_file.write_text("New content")
        dst_file.write_text("Old content")
        
        result = safe_copy_file(src_file, dst_file, backup=True)
        
        assert result is True
        assert dst_file.read_text() == "New content"
        
        # 检查备份文件是否存在
        backup_files = list(temp_dir.glob("destination.txt.backup.*"))
        assert len(backup_files) > 0

    def test_safe_copy_file_no_backup(self, temp_dir):
        """测试复制文件时不备份"""
        src_file = temp_dir / "source.txt"
        dst_file = temp_dir / "destination.txt"
        
        src_file.write_text("New content")
        dst_file.write_text("Old content")
        
        result = safe_copy_file(src_file, dst_file, backup=False)
        
        assert result is True
        assert dst_file.read_text() == "New content"
        
        # 不应该有备份文件
        backup_files = list(temp_dir.glob("destination.txt.backup.*"))
        assert len(backup_files) == 0

    def test_safe_copy_file_source_not_exists(self, temp_dir):
        """测试复制不存在的源文件"""
        src_file = temp_dir / "nonexistent.txt"
        dst_file = temp_dir / "destination.txt"
        
        result = safe_copy_file(src_file, dst_file)
        assert result is False

    def test_create_backup_success(self, temp_dir):
        """测试成功创建备份"""
        original_file = temp_dir / "original.txt"
        original_file.write_text("Original content")
        
        backup_path = create_backup(original_file, max_backups=3)
        
        assert backup_path is not None
        assert backup_path.exists()
        assert backup_path.read_text() == "Original content"
        assert "original_" in backup_path.name
        assert backup_path.suffix == ".txt"

    def test_create_backup_custom_directory(self, temp_dir):
        """测试在自定义目录创建备份"""
        original_file = temp_dir / "original.txt"
        backup_dir = temp_dir / "custom_backups"
        
        original_file.write_text("Content")
        
        backup_path = create_backup(original_file, backup_dir=backup_dir)
        
        assert backup_path is not None
        assert backup_path.parent == backup_dir
        assert backup_dir.exists()

    def test_create_backup_nonexistent_file(self, temp_dir):
        """测试备份不存在的文件"""
        nonexistent_file = temp_dir / "nonexistent.txt"
        result = create_backup(nonexistent_file)
        assert result is None

    def test_cleanup_old_backups(self, temp_dir):
        """测试清理旧备份"""
        backup_dir = temp_dir / "backups"
        backup_dir.mkdir()
        
        # 创建5个备份文件
        for i in range(5):
            backup_file = backup_dir / f"config_{i:02d}.toml"
            backup_file.write_text(f"Backup {i}")
        
        # 清理，只保留最新的2个
        cleanup_old_backups(backup_dir, "config.toml", max_backups=2)
        
        remaining_backups = list(backup_dir.glob("config_*.toml"))
        assert len(remaining_backups) == 2

    def test_atomic_write_success(self, temp_dir):
        """测试原子性写入成功"""
        target_file = temp_dir / "atomic_test.txt"
        content = "Atomic write test content"
        
        result = atomic_write(target_file, content)
        
        assert result is True
        assert target_file.exists()
        assert target_file.read_text(encoding="utf-8") == content

    def test_atomic_write_binary_content(self, temp_dir):
        """测试原子性写入二进制内容"""
        target_file = temp_dir / "binary_test.bin"
        content = b"Binary content \x00\x01\x02"
        
        result = atomic_write(target_file, content)
        
        assert result is True
        assert target_file.exists()
        assert target_file.read_bytes() == content

    @patch('tempfile.NamedTemporaryFile')
    def test_atomic_write_failure(self, mock_temp_file, temp_dir):
        """测试原子性写入失败"""
        mock_temp_file.side_effect = OSError("Disk full")
        
        target_file = temp_dir / "failed_write.txt"
        result = atomic_write(target_file, "content")
        
        assert result is False


class TestDiskOperations:
    """磁盘操作测试"""

    def test_get_disk_usage_valid_path(self, temp_dir):
        """测试获取有效路径的磁盘使用情况"""
        usage = get_disk_usage(temp_dir)
        
        required_keys = ["total", "used", "free", "percent_used"]
        for key in required_keys:
            assert key in usage
            assert isinstance(usage[key], (int, float))
            assert usage[key] >= 0
        
        # 基本逻辑检查
        assert usage["total"] == usage["used"] + usage["free"]
        assert 0 <= usage["percent_used"] <= 100

    @patch('shutil.disk_usage')
    def test_get_disk_usage_error(self, mock_disk_usage, temp_dir):
        """测试获取磁盘使用情况时的错误"""
        mock_disk_usage.side_effect = OSError("Permission denied")
        
        usage = get_disk_usage(temp_dir)
        
        assert usage["total"] == 0
        assert usage["used"] == 0
        assert usage["free"] == 0
        assert usage["percent_used"] == 0

    def test_check_disk_space_sufficient(self, temp_dir):
        """测试磁盘空间充足"""
        # 要求1字节，应该总是充足的
        result = check_disk_space(temp_dir, 1)
        assert result is True

    @patch('claudewarp.core.utils.get_disk_usage')
    def test_check_disk_space_insufficient(self, mock_get_disk_usage, temp_dir):
        """测试磁盘空间不足"""
        # 模拟磁盘只有100字节可用
        mock_get_disk_usage.return_value = {
            "total": 1000,
            "used": 900,
            "free": 100,
            "percent_used": 90.0
        }
        
        # 要求200字节，应该不足
        with pytest.raises(DiskSpaceError):
            check_disk_space(temp_dir, 200)


class TestSystemCommands:
    """系统命令测试"""

    def test_run_command_success(self):
        """测试成功运行命令"""
        # 使用跨平台的命令
        if platform.system() == "Windows":
            result = run_command(["echo", "hello"])
        else:
            result = run_command(["echo", "hello"])
        
        assert result["success"] is True
        assert result["returncode"] == 0
        assert "hello" in result["stdout"]
        assert result["stderr"] == ""

    def test_run_command_failure(self):
        """测试运行失败的命令"""
        result = run_command(["nonexistent_command_12345"])
        
        assert result["success"] is False
        assert result["returncode"] != 0

    def test_run_command_with_cwd(self, temp_dir):
        """测试在指定目录运行命令"""
        if platform.system() == "Windows":
            result = run_command(["dir"], cwd=temp_dir)
        else:
            result = run_command(["ls"], cwd=temp_dir)
        
        # 命令可能成功也可能失败，主要测试cwd参数不会导致异常
        assert "returncode" in result

    def test_run_command_with_timeout(self):
        """测试带超时的命令"""
        if platform.system() == "Windows":
            # Windows sleep命令
            result = run_command(["timeout", "2"], timeout=1)
        else:
            # Unix sleep命令
            result = run_command(["sleep", "2"], timeout=1)
        
        assert result["success"] is False
        assert "timeout" in result

    def test_run_command_no_capture_output(self):
        """测试不捕获输出的命令"""
        result = run_command(["echo", "test"], capture_output=False)
        
        assert result["stdout"] == ""
        assert result["stderr"] == ""


class TestUtilityFunctions:
    """工具函数测试"""

    def test_format_file_size_bytes(self):
        """测试格式化字节大小"""
        test_cases = [
            (0, "0 B"),
            (1, "1.0 B"),
            (1023, "1023.0 B"),
            (1024, "1.0 KB"),
            (1536, "1.5 KB"),  # 1.5 * 1024
            (1048576, "1.0 MB"),  # 1024 * 1024
            (1073741824, "1.0 GB"),  # 1024^3
            (1099511627776, "1.0 TB"),  # 1024^4
        ]
        
        for size_bytes, expected in test_cases:
            result = format_file_size(size_bytes)
            assert result == expected

    def test_format_file_size_float(self):
        """测试格式化浮点数大小"""
        result = format_file_size(1536.0)
        assert result == "1.5 KB"

    def test_validate_url_valid_urls(self):
        """测试有效URL验证"""
        valid_urls = [
            "https://www.example.com",
            "http://localhost",
            "https://api.example.com:8080",
            "http://192.168.1.1",
            "https://example.com/path/to/resource",
            "http://localhost:3000/api/v1",
            "https://sub.domain.example.com",
        ]
        
        for url in valid_urls:
            assert validate_url(url) is True

    def test_validate_url_invalid_urls(self):
        """测试无效URL验证"""
        invalid_urls = [
            "example.com",  # 缺少协议
            "ftp://example.com",  # 不支持的协议
            "https://",  # 不完整
            "",  # 空字符串
            "not_a_url",  # 完全无效
            "https:///invalid",  # 无效格式
        ]
        
        for url in invalid_urls:
            assert validate_url(url) is False

    @patch('claudewarp.core.utils.is_windows')
    def test_sanitize_filename_windows(self, mock_is_windows):
        """测试Windows文件名清理"""
        mock_is_windows.return_value = True
        
        test_cases = [
            ("normal_file.txt", "normal_file.txt"),
            ("file<with>bad:chars.txt", "file_with_bad_chars.txt"),
            ("file\"with|illegal*chars?.txt", "file_with_illegal_chars_.txt"),
            ("  spaced file  ", "spaced file"),
            ("", "untitled"),
            ("...", "untitled"),
        ]
        
        for input_name, expected in test_cases:
            result = sanitize_filename(input_name)
            assert result == expected

    @patch('claudewarp.core.utils.is_windows')
    def test_sanitize_filename_unix(self, mock_is_windows):
        """测试Unix文件名清理"""
        mock_is_windows.return_value = False
        
        test_cases = [
            ("normal_file.txt", "normal_file.txt"),
            ("file/with/slashes.txt", "file_with_slashes.txt"),
            ("file\x00with\x00nulls.txt", "file_with_nulls.txt"),
            ("file<with>windows:chars.txt", "file<with>windows:chars.txt"),  # 在Unix上合法
        ]
        
        for input_name, expected in test_cases:
            result = sanitize_filename(input_name)
            assert result == expected

    def test_get_environment_info(self):
        """测试获取环境信息"""
        env_info = get_environment_info()
        
        required_keys = ["platform", "python", "environment", "permissions"]
        for key in required_keys:
            assert key in env_info
        
        # 检查平台信息
        assert "system" in env_info["platform"]
        
        # 检查Python信息
        assert "version" in env_info["python"]
        assert "executable" in env_info["python"]
        
        # 检查环境信息
        assert "home" in env_info["environment"]
        assert "config_dir" in env_info["environment"]


class TestLevelAlignFilter:
    """日志级别对齐过滤器测试"""

    def test_filter_known_levels(self):
        """测试已知日志级别的过滤"""
        filter_obj = LevelAlignFilter()
        
        test_cases = [
            ("DEBUG", "DEBUG"),
            ("INFO", "INFO"),
            ("WARNING", "WARN"),
            ("ERROR", "ERROR"),
            ("CRITICAL", "CRIT"),
        ]
        
        for input_level, expected_short in test_cases:
            # 创建模拟的日志记录
            record = Mock()
            record.levelname = input_level
            
            result = filter_obj.filter(record)
            
            assert result is True
            assert record.levelname_padded.startswith(f"[{expected_short}]")
            assert len(record.levelname_padded) == filter_obj.WIDTH

    def test_filter_unknown_level(self):
        """测试未知日志级别的过滤"""
        filter_obj = LevelAlignFilter()
        
        record = Mock()
        record.levelname = "CUSTOM"
        
        result = filter_obj.filter(record)
        
        assert result is True
        assert record.levelname_padded.startswith("[CUSTOM]")

    def test_filter_none_level(self):
        """测试None日志级别的过滤"""
        filter_obj = LevelAlignFilter()
        
        record = Mock()
        record.levelname = None
        
        result = filter_obj.filter(record)
        
        assert result is True
        assert "[UNKNOWN]" in record.levelname_padded


class TestUtilsEdgeCases:
    """工具函数边界情况测试"""

    def test_ensure_directory_with_file_conflict(self, temp_dir):
        """测试目录路径与现有文件冲突"""
        # 创建一个文件
        file_path = temp_dir / "conflicting_file"
        file_path.write_text("content")
        
        # 如果路径已存在（无论是文件还是目录），ensure_directory 会直接返回
        # 因为它检查 path.exists() 而不区分文件和目录
        result = ensure_directory(file_path)
        assert result == file_path
        # 文件仍然存在，没有被转换为目录
        assert file_path.exists()
        assert file_path.is_file()

    def test_atomic_write_replace_existing_file(self, temp_dir):
        """测试原子写入替换现有文件"""
        target_file = temp_dir / "existing.txt"
        target_file.write_text("old content")
        
        new_content = "new content"
        result = atomic_write(target_file, new_content)
        
        assert result is True
        assert target_file.read_text() == new_content

    def test_safe_copy_file_create_nested_directory(self, temp_dir):
        """测试复制文件时创建嵌套目录"""
        src_file = temp_dir / "source.txt"
        dst_file = temp_dir / "level1" / "level2" / "destination.txt"
        
        src_file.write_text("content")
        
        result = safe_copy_file(src_file, dst_file)
        
        assert result is True
        assert dst_file.exists()
        assert dst_file.parent.exists()

    def test_run_command_empty_command(self):
        """测试运行空命令"""
        result = run_command([])
        
        assert result["success"] is False
        assert "error" in result

    def test_create_backup_with_existing_backups(self, temp_dir):
        """测试在有现有备份的情况下创建新备份"""
        original_file = temp_dir / "test.txt"
        original_file.write_text("content")
        
        # 创建多个备份
        backup_paths = []
        for i in range(3):
            backup_path = create_backup(original_file, max_backups=5)
            backup_paths.append(backup_path)
            # 稍微修改文件内容
            original_file.write_text(f"content {i}")
        
        # 所有备份都应该成功创建
        for backup_path in backup_paths:
            assert backup_path is not None
            assert backup_path.exists()

    def test_unicode_filename_handling(self, temp_dir):
        """测试Unicode文件名处理"""
        unicode_filename = "测试文件_🚀_emoji.txt"
        sanitized = sanitize_filename(unicode_filename)
        
        # Unicode字符应该保留
        assert "测试文件" in sanitized
        assert "🚀" in sanitized
        assert "emoji" in sanitized

    @patch('shutil.disk_usage')
    def test_disk_usage_calculation_edge_case(self, mock_disk_usage):
        """测试磁盘使用率计算的边界情况"""
        # 模拟磁盘已满
        mock_disk_usage.return_value = shutil._ntuple_diskusage(
            total=1000, used=1000, free=0
        )
        
        usage = get_disk_usage("/tmp")
        assert usage["percent_used"] == 100.0
        assert usage["free"] == 0

    def test_format_file_size_very_large(self):
        """测试格式化超大文件大小"""
        # 测试超过TB的大小
        very_large_size = 1024 ** 5  # PB级别
        result = format_file_size(very_large_size)
        
        # 应该显示为TB（最大单位）
        assert "TB" in result
        assert float(result.split()[0]) > 1000