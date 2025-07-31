"""
工具函数测试

测试跨平台工具函数的完整性和可靠性。
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

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
    
    # 环境信息
    get_environment_info,
    
    # 日志过滤器
    LevelAlignFilter,
)

from claudewarp.core.exceptions import (
    DiskSpaceError,
    PermissionError as ClaudeWarpPermissionError,
    SystemError,
)


class TestPlatformDetection:
    """测试平台检测功能"""
    
    def test_get_platform_info(self):
        """测试获取平台信息"""
        info = get_platform_info()
        
        assert isinstance(info, dict)
        
        required_keys = [
            "system", "release", "version", "machine", 
            "processor", "architecture", "python_version"
        ]
        
        for key in required_keys:
            assert key in info
            assert isinstance(info[key], str)
    
    @patch('platform.system')
    def test_is_windows_true(self, mock_system):
        """测试Windows系统检测（正确情况）"""
        mock_system.return_value = "Windows"
        assert is_windows() is True
        
        mock_system.return_value = "windows"
        assert is_windows() is True
    
    @patch('platform.system')
    def test_is_windows_false(self, mock_system):
        """测试Windows系统检测（错误情况）"""
        mock_system.return_value = "Darwin"
        assert is_windows() is False
        
        mock_system.return_value = "Linux"
        assert is_windows() is False
    
    @patch('platform.system')
    def test_is_macos_true(self, mock_system):
        """测试macOS系统检测（正确情况）"""
        mock_system.return_value = "Darwin"
        assert is_macos() is True
        
        mock_system.return_value = "darwin"
        assert is_macos() is True
    
    @patch('platform.system')
    def test_is_macos_false(self, mock_system):
        """测试macOS系统检测（错误情况）"""
        mock_system.return_value = "Windows"
        assert is_macos() is False
        
        mock_system.return_value = "Linux"
        assert is_macos() is False
    
    @patch('platform.system')
    def test_is_linux_true(self, mock_system):
        """测试Linux系统检测（正确情况）"""
        mock_system.return_value = "Linux"
        assert is_linux() is True
        
        mock_system.return_value = "linux"
        assert is_linux() is True
    
    @patch('platform.system')
    def test_is_linux_false(self, mock_system):
        """测试Linux系统检测（错误情况）"""
        mock_system.return_value = "Windows"
        assert is_linux() is False
        
        mock_system.return_value = "Darwin"
        assert is_linux() is False
    
    def test_platform_detection_consistency(self):
        """测试平台检测的一致性"""
        # 只有一个平台检测函数应该返回True
        detection_results = [is_windows(), is_macos(), is_linux()]
        true_count = sum(detection_results)
        
        assert true_count == 1, "应该只有一个平台检测函数返回True"


class TestPathHandling:
    """测试路径处理功能"""
    
    def test_get_home_directory(self):
        """测试获取用户主目录"""
        home_dir = get_home_directory()
        
        assert isinstance(home_dir, Path)
        assert home_dir.exists()
        assert home_dir.is_dir()
    
    @patch('claudewarp.core.utils.is_windows')
    @patch.dict(os.environ, {'APPDATA': '/test/appdata'})
    def test_get_config_directory_windows_with_appdata(self, mock_is_windows):
        """测试Windows系统获取配置目录（有APPDATA环境变量）"""
        mock_is_windows.return_value = True
        
        config_dir = get_config_directory("testapp")
        
        assert str(config_dir) == "/test/appdata/testapp"
    
    @patch('claudewarp.core.utils.is_windows')
    @patch('claudewarp.core.utils.get_home_directory')
    @patch.dict(os.environ, {}, clear=True)
    def test_get_config_directory_windows_no_appdata(self, mock_get_home, mock_is_windows):
        """测试Windows系统获取配置目录（无APPDATA环境变量）"""
        mock_is_windows.return_value = True
        mock_get_home.return_value = Path("/test/home")
        
        config_dir = get_config_directory("testapp")
        
        assert str(config_dir) == "/test/home/.testapp"
    
    @patch('claudewarp.core.utils.is_windows')
    @patch.dict(os.environ, {'XDG_CONFIG_HOME': '/test/xdg_config'})
    def test_get_config_directory_unix_with_xdg(self, mock_is_windows):
        """测试Unix系统获取配置目录（有XDG_CONFIG_HOME环境变量）"""
        mock_is_windows.return_value = False
        
        config_dir = get_config_directory("testapp")
        
        assert str(config_dir) == "/test/xdg_config/testapp"
    
    @patch('claudewarp.core.utils.is_windows')
    @patch('claudewarp.core.utils.get_home_directory')
    @patch.dict(os.environ, {}, clear=True)
    def test_get_config_directory_unix_no_xdg(self, mock_get_home, mock_is_windows):
        """测试Unix系统获取配置目录（无XDG_CONFIG_HOME环境变量）"""
        mock_is_windows.return_value = False
        mock_get_home.return_value = Path("/test/home")
        
        config_dir = get_config_directory("testapp")
        
        assert str(config_dir) == "/test/home/.config/testapp"
    
    @patch('claudewarp.core.utils.is_windows')
    @patch('claudewarp.core.utils.is_macos')
    @patch.dict(os.environ, {'LOCALAPPDATA': '/test/localappdata'})
    def test_get_cache_directory_windows(self, mock_is_macos, mock_is_windows):
        """测试Windows系统获取缓存目录"""
        mock_is_windows.return_value = True
        mock_is_macos.return_value = False
        
        cache_dir = get_cache_directory("testapp")
        
        assert str(cache_dir) == "/test/localappdata/testapp/cache"
    
    @patch('claudewarp.core.utils.is_windows')
    @patch('claudewarp.core.utils.is_macos')
    @patch('claudewarp.core.utils.get_home_directory')
    def test_get_cache_directory_macos(self, mock_get_home, mock_is_macos, mock_is_windows):
        """测试macOS系统获取缓存目录"""
        mock_is_windows.return_value = False
        mock_is_macos.return_value = True
        mock_get_home.return_value = Path("/test/home")
        
        cache_dir = get_cache_directory("testapp")
        
        assert str(cache_dir) == "/test/home/Library/Caches/testapp"
    
    @patch('claudewarp.core.utils.is_windows')
    @patch('claudewarp.core.utils.is_macos')
    @patch.dict(os.environ, {'XDG_CACHE_HOME': '/test/xdg_cache'})
    def test_get_cache_directory_linux_with_xdg(self, mock_is_macos, mock_is_windows):
        """测试Linux系统获取缓存目录（有XDG_CACHE_HOME环境变量）"""
        mock_is_windows.return_value = False
        mock_is_macos.return_value = False
        
        cache_dir = get_cache_directory("testapp")
        
        assert str(cache_dir) == "/test/xdg_cache/testapp"


class TestDirectoryAndPermissions:
    """测试目录和权限功能"""
    
    @pytest.fixture
    def temp_dir(self):
        """临时目录fixture"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_ensure_directory_create_new(self, temp_dir):
        """测试创建新目录"""
        new_dir = temp_dir / "new_directory"
        
        result = ensure_directory(new_dir)
        
        assert result == new_dir
        assert new_dir.exists()
        assert new_dir.is_dir()
    
    def test_ensure_directory_existing(self, temp_dir):
        """测试确保已存在的目录"""
        existing_dir = temp_dir / "existing"
        existing_dir.mkdir()
        
        result = ensure_directory(existing_dir)
        
        assert result == existing_dir
        assert existing_dir.exists()
    
    def test_ensure_directory_nested(self, temp_dir):
        """测试创建嵌套目录"""
        nested_dir = temp_dir / "level1" / "level2" / "level3"
        
        result = ensure_directory(nested_dir)
        
        assert result == nested_dir
        assert nested_dir.exists()
        assert nested_dir.is_dir()
    
    @patch('pathlib.Path.mkdir')
    def test_ensure_directory_permission_error(self, mock_mkdir, temp_dir):
        """测试目录创建权限错误"""
        mock_mkdir.side_effect = OSError(13, "Permission denied")
        
        new_dir = temp_dir / "restricted"
        
        with pytest.raises(ClaudeWarpPermissionError):
            ensure_directory(new_dir)
    
    @patch('pathlib.Path.mkdir')
    def test_ensure_directory_system_error(self, mock_mkdir, temp_dir):
        """测试目录创建系统错误"""
        mock_mkdir.side_effect = OSError(28, "No space left on device")
        
        new_dir = temp_dir / "no_space"
        
        with pytest.raises(SystemError):
            ensure_directory(new_dir)
    
    @patch('claudewarp.core.utils.is_windows')
    def test_set_file_permissions_windows(self, mock_is_windows, temp_dir):
        """测试Windows系统文件权限设置"""
        mock_is_windows.return_value = True
        
        test_file = temp_dir / "test.txt"
        test_file.touch()
        
        result = set_file_permissions(test_file, 0o600)
        
        # Windows系统应该返回True但不实际设置权限
        assert result is True
    
    @patch('claudewarp.core.utils.is_windows')
    @patch('os.chmod')
    def test_set_file_permissions_unix_success(self, mock_chmod, mock_is_windows, temp_dir):
        """测试Unix系统文件权限设置成功"""
        mock_is_windows.return_value = False
        mock_chmod.return_value = None
        
        test_file = temp_dir / "test.txt"
        test_file.touch()
        
        result = set_file_permissions(test_file, 0o600)
        
        assert result is True
        mock_chmod.assert_called_once_with(test_file, 0o600)
    
    @patch('claudewarp.core.utils.is_windows')
    @patch('os.chmod')
    def test_set_file_permissions_unix_failure(self, mock_chmod, mock_is_windows, temp_dir):
        """测试Unix系统文件权限设置失败"""
        mock_is_windows.return_value = False
        mock_chmod.side_effect = OSError("Permission denied")
        
        test_file = temp_dir / "test.txt"
        test_file.touch()
        
        result = set_file_permissions(test_file, 0o600)
        
        assert result is False
    
    def test_check_file_permissions_existing_file(self, temp_dir):
        """测试检查已存在文件的权限"""
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")
        
        permissions = check_file_permissions(test_file)
        
        assert isinstance(permissions, dict)
        assert permissions["exists"] is True
        assert permissions["readable"] is True
        assert permissions["writable"] is True
        assert "executable" in permissions
    
    def test_check_file_permissions_nonexistent_file(self, temp_dir):
        """测试检查不存在文件的权限"""
        nonexistent_file = temp_dir / "nonexistent.txt"
        
        permissions = check_file_permissions(nonexistent_file)
        
        assert permissions["exists"] is False
        assert permissions["readable"] is False
        assert permissions["writable"] is False
        assert permissions["executable"] is False


class TestFileOperations:
    """测试文件操作功能"""
    
    @pytest.fixture
    def temp_dir(self):
        """临时目录fixture"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_get_file_size_existing_file(self, temp_dir):
        """测试获取已存在文件的大小"""
        test_file = temp_dir / "test.txt"
        content = "Hello, World!"
        test_file.write_text(content, encoding='utf-8')
        
        size = get_file_size(test_file)
        
        assert size == len(content.encode('utf-8'))
    
    def test_get_file_size_nonexistent_file(self, temp_dir):
        """测试获取不存在文件的大小"""
        nonexistent_file = temp_dir / "nonexistent.txt"
        
        size = get_file_size(nonexistent_file)
        
        assert size == 0
    
    def test_safe_copy_file_success(self, temp_dir):
        """测试安全复制文件成功"""
        src_file = temp_dir / "source.txt"
        dst_file = temp_dir / "destination.txt"
        content = "Test content for copying"
        
        src_file.write_text(content)
        
        result = safe_copy_file(src_file, dst_file)
        
        assert result is True
        assert dst_file.exists()
        assert dst_file.read_text() == content
    
    def test_safe_copy_file_with_backup(self, temp_dir):
        """测试带备份的安全复制文件"""
        src_file = temp_dir / "source.txt"
        dst_file = temp_dir / "destination.txt"
        src_content = "New content"
        dst_content = "Original content"
        
        src_file.write_text(src_content)
        dst_file.write_text(dst_content)
        
        result = safe_copy_file(src_file, dst_file, backup=True)
        
        assert result is True
        assert dst_file.read_text() == src_content
        
        # 检查备份文件是否创建
        backup_files = list(temp_dir.glob("destination.txt.backup.*"))
        assert len(backup_files) >= 1
        assert backup_files[0].read_text() == dst_content
    
    def test_safe_copy_file_no_backup(self, temp_dir):
        """测试不带备份的安全复制文件"""
        src_file = temp_dir / "source.txt"
        dst_file = temp_dir / "destination.txt"
        src_content = "New content"
        dst_content = "Original content"
        
        src_file.write_text(src_content)
        dst_file.write_text(dst_content)
        
        result = safe_copy_file(src_file, dst_file, backup=False)
        
        assert result is True
        assert dst_file.read_text() == src_content
        
        # 检查不应该有备份文件
        backup_files = list(temp_dir.glob("destination.txt.backup.*"))
        assert len(backup_files) == 0
    
    def test_safe_copy_file_source_not_exists(self, temp_dir):
        """测试复制不存在的源文件"""
        src_file = temp_dir / "nonexistent.txt"
        dst_file = temp_dir / "destination.txt"
        
        result = safe_copy_file(src_file, dst_file)
        
        assert result is False
        assert not dst_file.exists()
    
    def test_create_backup_success(self, temp_dir):
        """测试创建备份成功"""
        original_file = temp_dir / "original.txt"
        content = "Content to backup"
        original_file.write_text(content)
        
        backup_path = create_backup(original_file)
        
        assert backup_path is not None
        assert backup_path.exists()
        assert backup_path.read_text() == content
        assert "original_" in backup_path.name
        assert backup_path.suffix == ".txt"
    
    def test_create_backup_custom_dir(self, temp_dir):
        """测试在自定义目录创建备份"""
        original_file = temp_dir / "original.txt"
        backup_dir = temp_dir / "backups"
        content = "Content to backup"
        
        original_file.write_text(content)
        
        backup_path = create_backup(original_file, backup_dir)
        
        assert backup_path is not None
        assert backup_path.parent == backup_dir
        assert backup_path.exists()
        assert backup_path.read_text() == content
    
    def test_create_backup_nonexistent_file(self, temp_dir):
        """测试备份不存在的文件"""
        nonexistent_file = temp_dir / "nonexistent.txt"
        
        backup_path = create_backup(nonexistent_file)
        
        assert backup_path is None
    
    def test_cleanup_old_backups(self, temp_dir):
        """测试清理旧备份文件"""
        backup_dir = temp_dir / "backups"
        backup_dir.mkdir()
        
        # 创建多个备份文件
        original_name = "test.txt"
        for i in range(5):
            backup_file = backup_dir / f"test_{i:02d}.txt"
            backup_file.write_text(f"backup {i}")
        
        # 清理，只保留3个
        cleanup_old_backups(backup_dir, original_name, max_backups=3)
        
        remaining_backups = list(backup_dir.glob("test_*.txt"))
        assert len(remaining_backups) <= 3
    
    def test_atomic_write_text_success(self, temp_dir):
        """测试原子性写入文本文件成功"""
        test_file = temp_dir / "atomic_test.txt"
        content = "This is atomic write test content"
        
        result = atomic_write(test_file, content)
        
        assert result is True
        assert test_file.exists()
        assert test_file.read_text(encoding='utf-8') == content
    
    def test_atomic_write_bytes_success(self, temp_dir):
        """测试原子性写入字节文件成功"""
        test_file = temp_dir / "atomic_test.bin"
        content = b"This is binary content"
        
        result = atomic_write(test_file, content)
        
        assert result is True
        assert test_file.exists()
        assert test_file.read_bytes() == content
    
    def test_atomic_write_create_directory(self, temp_dir):
        """测试原子性写入时创建目录"""
        nested_file = temp_dir / "nested" / "dir" / "test.txt"
        content = "Content in nested directory"
        
        result = atomic_write(nested_file, content)
        
        assert result is True
        assert nested_file.exists()
        assert nested_file.read_text(encoding='utf-8') == content
    
    @patch('tempfile.NamedTemporaryFile')
    def test_atomic_write_failure(self, mock_temp_file, temp_dir):
        """测试原子性写入失败"""
        mock_temp_file.side_effect = OSError("Disk full")
        
        test_file = temp_dir / "test.txt"
        content = "Test content"
        
        result = atomic_write(test_file, content)
        
        assert result is False
        assert not test_file.exists()


class TestDiskSpace:
    """测试磁盘空间功能"""
    
    def test_get_disk_usage(self):
        """测试获取磁盘使用情况"""
        # 使用临时目录来测试
        with tempfile.TemporaryDirectory() as temp_dir:
            usage = get_disk_usage(temp_dir)
            
            assert isinstance(usage, dict)
            assert "total" in usage
            assert "used" in usage
            assert "free" in usage
            assert "percent_used" in usage
            
            assert isinstance(usage["total"], int)
            assert isinstance(usage["used"], int) 
            assert isinstance(usage["free"], int)
            assert isinstance(usage["percent_used"], float)
            
            assert usage["total"] > 0
            assert usage["used"] >= 0
            assert usage["free"] >= 0
            assert 0 <= usage["percent_used"] <= 100
    
    @patch('shutil.disk_usage')
    def test_get_disk_usage_error(self, mock_disk_usage):
        """测试获取磁盘使用情况错误"""
        mock_disk_usage.side_effect = OSError("Access denied")
        
        usage = get_disk_usage("/nonexistent")
        
        expected = {"total": 0, "used": 0, "free": 0, "percent_used": 0}
        assert usage == expected
    
    def test_check_disk_space_sufficient(self):
        """测试检查磁盘空间充足"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 请求很小的空间，应该足够
            result = check_disk_space(temp_dir, 1024)  # 1KB
            
            assert result is True
    
    @patch('claudewarp.core.utils.get_disk_usage')
    def test_check_disk_space_insufficient(self, mock_get_disk_usage):
        """测试检查磁盘空间不足"""
        mock_get_disk_usage.return_value = {
            "total": 1000,
            "used": 900,
            "free": 100,
            "percent_used": 90.0
        }
        
        with pytest.raises(DiskSpaceError):
            check_disk_space("/test", 200)  # 需要200，但只有100可用


class TestSystemCommands:
    """测试系统命令功能"""
    
    def test_run_command_success(self):
        """测试运行命令成功"""
        # 使用简单的echo命令，跨平台兼容
        if is_windows():
            command = ["echo", "hello"]
        else:
            command = ["echo", "hello"]
        
        result = run_command(command)
        
        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["returncode"] == 0
        assert "hello" in result["stdout"]
        assert result["stderr"] == ""
        assert result["command"] == " ".join(command)
    
    def test_run_command_failure(self):
        """测试运行命令失败"""
        # 使用一个不存在的命令
        command = ["nonexistent_command_12345"]
        
        result = run_command(command)
        
        assert isinstance(result, dict)
        assert result["success"] is False
        assert result["returncode"] != 0
        assert result["stdout"] == ""
        assert len(result["stderr"]) > 0
        assert result["command"] == " ".join(command)
    
    @patch('subprocess.run')
    def test_run_command_timeout(self, mock_run):
        """测试运行命令超时"""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("test", 5)
        
        result = run_command(["sleep", "10"], timeout=5)
        
        assert result["success"] is False
        assert result["returncode"] == -1
        assert result["stderr"] == "Command timed out"
        assert result.get("timeout") is True
    
    def test_run_command_with_cwd(self):
        """测试在指定工作目录运行命令"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试文件
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("test")
            
            if is_windows():
                command = ["dir"]
            else:
                command = ["ls"]
            
            result = run_command(command, cwd=temp_dir)
            
            assert result["success"] is True
            assert "test.txt" in result["stdout"]
    
    def test_run_command_no_capture(self):
        """测试不捕获输出的命令运行"""
        command = ["echo", "hello"]
        
        result = run_command(command, capture_output=False)
        
        assert result["success"] is True
        assert result["stdout"] == ""
        assert result["stderr"] == ""


class TestUtilityFunctions:
    """测试工具函数"""
    
    def test_format_file_size_bytes(self):
        """测试格式化字节大小"""
        assert format_file_size(0) == "0 B"
        assert format_file_size(512) == "512.0 B"
        assert format_file_size(1023) == "1023.0 B"
    
    def test_format_file_size_kilobytes(self):
        """测试格式化千字节大小"""
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1536) == "1.5 KB"
        assert format_file_size(1024 * 1023) == "1023.0 KB"
    
    def test_format_file_size_megabytes(self):
        """测试格式化兆字节大小"""
        assert format_file_size(1024 * 1024) == "1.0 MB"
        assert format_file_size(1024 * 1024 * 1.5) == "1.5 MB"
    
    def test_format_file_size_large(self):
        """测试格式化大文件大小"""
        gb = 1024 * 1024 * 1024
        tb = gb * 1024
        
        assert format_file_size(gb) == "1.0 GB"
        assert format_file_size(tb) == "1.0 TB"
        assert format_file_size(tb * 2.5) == "2.5 TB"
    
    def test_validate_url_valid_urls(self):
        """测试验证有效URL"""
        valid_urls = [
            "https://www.example.com",
            "http://example.com",
            "https://api.example.com/v1/",
            "http://localhost:8080",
            "https://192.168.1.1:3000",
            "http://subdomain.example.co.uk/path",
        ]
        
        for url in valid_urls:
            assert validate_url(url) is True, f"URL应该有效: {url}"
    
    def test_validate_url_invalid_urls(self):
        """测试验证无效URL"""
        invalid_urls = [
            "ftp://example.com",
            "not-a-url",
            "example.com",  # 缺少协议
            "https://",
            "http://.com",
            "",
            "javascript:alert('xss')",
        ]
        
        for url in invalid_urls:
            assert validate_url(url) is False, f"URL应该无效: {url}"
    
    @patch('claudewarp.core.utils.is_windows')
    def test_sanitize_filename_windows(self, mock_is_windows):
        """测试Windows系统文件名清理"""
        mock_is_windows.return_value = True
        
        test_cases = [
            ("normal_file.txt", "normal_file.txt"),
            ("file<with>bad:chars.txt", "file_with_bad_chars.txt"),
            ('file"with|bad*chars?.txt', "file_with_bad_chars_.txt"),
            ("file\\with/bad\\chars.txt", "file_with_bad_chars.txt"),
            ("  .file.txt.  ", "file.txt"),
            ("", "untitled"),
        ]
        
        for input_name, expected in test_cases:
            result = sanitize_filename(input_name)
            assert result == expected, f"输入: {input_name}, 期望: {expected}, 实际: {result}"
    
    @patch('claudewarp.core.utils.is_windows')
    def test_sanitize_filename_unix(self, mock_is_windows):
        """测试Unix系统文件名清理"""
        mock_is_windows.return_value = False
        
        test_cases = [
            ("normal_file.txt", "normal_file.txt"),
            ("file/with/slashes.txt", "file_with_slashes.txt"),
            ("file\x00with\x00null.txt", "file_with_null.txt"),
            ("  .hidden_file.txt.  ", "hidden_file.txt"),
            ("", "untitled"),
        ]
        
        for input_name, expected in test_cases:
            result = sanitize_filename(input_name)
            assert result == expected, f"输入: {input_name}, 期望: {expected}, 实际: {result}"
    
    def test_get_environment_info(self):
        """测试获取环境信息"""
        env_info = get_environment_info()
        
        assert isinstance(env_info, dict)
        
        # 检查必需的键
        required_keys = ["platform", "python", "environment", "permissions"]
        for key in required_keys:
            assert key in env_info
        
        # 检查platform信息
        assert isinstance(env_info["platform"], dict)
        
        # 检查Python信息
        python_info = env_info["python"]
        assert isinstance(python_info, dict)
        assert "version" in python_info
        assert "executable" in python_info
        assert "path" in python_info
        
        # 检查环境信息
        environment = env_info["environment"]
        assert isinstance(environment, dict)
        assert "home" in environment
        assert "config_dir" in environment
        assert "cache_dir" in environment
        
        # 检查权限信息
        permissions = env_info["permissions"]
        assert isinstance(permissions, dict)
        assert "can_write_config" in permissions
        assert "can_write_cache" in permissions


class TestLevelAlignFilter:
    """测试日志级别对齐过滤器"""
    
    def test_filter_debug_level(self):
        """测试DEBUG级别过滤"""
        filter_obj = LevelAlignFilter()
        
        # 创建mock记录
        record = Mock()
        record.levelname = "DEBUG"
        
        result = filter_obj.filter(record)
        
        assert result is True
        assert hasattr(record, 'levelname_padded')
        assert record.levelname_padded.startswith("[DEBUG]")
        assert len(record.levelname_padded) == LevelAlignFilter.WIDTH
    
    def test_filter_info_level(self):
        """测试INFO级别过滤"""
        filter_obj = LevelAlignFilter()
        
        record = Mock()
        record.levelname = "INFO"
        
        result = filter_obj.filter(record)
        
        assert result is True
        assert record.levelname_padded.startswith("[INFO]")
        assert len(record.levelname_padded) == LevelAlignFilter.WIDTH
    
    def test_filter_warning_level(self):
        """测试WARNING级别过滤"""
        filter_obj = LevelAlignFilter()
        
        record = Mock()
        record.levelname = "WARNING"
        
        result = filter_obj.filter(record)
        
        assert result is True
        assert record.levelname_padded.startswith("[WARN]")
        assert len(record.levelname_padded) == LevelAlignFilter.WIDTH
    
    def test_filter_error_level(self):
        """测试ERROR级别过滤"""
        filter_obj = LevelAlignFilter()
        
        record = Mock()
        record.levelname = "ERROR"
        
        result = filter_obj.filter(record)
        
        assert result is True
        assert record.levelname_padded.startswith("[ERROR]")
        assert len(record.levelname_padded) == LevelAlignFilter.WIDTH
    
    def test_filter_critical_level(self):
        """测试CRITICAL级别过滤"""
        filter_obj = LevelAlignFilter()
        
        record = Mock()
        record.levelname = "CRITICAL"
        
        result = filter_obj.filter(record)
        
        assert result is True
        assert record.levelname_padded.startswith("[CRIT]")
        assert len(record.levelname_padded) == LevelAlignFilter.WIDTH
    
    def test_filter_unknown_level(self):
        """测试未知级别过滤"""
        filter_obj = LevelAlignFilter()
        
        record = Mock()
        record.levelname = "UNKNOWN_LEVEL"
        
        result = filter_obj.filter(record)
        
        assert result is True
        assert record.levelname_padded.startswith("[UNKNOWN_LEVEL]")
    
    def test_filter_none_level(self):
        """测试空级别过滤"""
        filter_obj = LevelAlignFilter()
        
        record = Mock()
        record.levelname = None
        
        result = filter_obj.filter(record)
        
        assert result is True
        assert record.levelname_padded.startswith("[UNKNOWN]")
    
    def test_all_levels_same_width(self):
        """测试所有级别都有相同宽度"""
        filter_obj = LevelAlignFilter()
        
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "FATAL", "NOTSET"]
        
        for level in levels:
            record = Mock()
            record.levelname = level
            
            filter_obj.filter(record)
            
            assert len(record.levelname_padded) == LevelAlignFilter.WIDTH


class TestEdgeCases:
    """测试边界情况和错误处理"""
    
    def test_empty_string_inputs(self):
        """测试空字符串输入"""
        assert format_file_size(0) == "0 B"
        assert validate_url("") is False
        assert sanitize_filename("") == "untitled"
    
    def test_none_inputs(self):
        """测试None输入的处理"""
        # 大多数函数应该能优雅处理None输入或有适当的类型检查
        with pytest.raises((TypeError, AttributeError)):
            get_file_size(None)
        
        with pytest.raises((TypeError, AttributeError)):
            check_file_permissions(None)
    
    def test_invalid_path_inputs(self):
        """测试无效路径输入"""
        # 测试包含非法字符的路径
        if is_windows():
            invalid_paths = ["CON", "PRN", "AUX", "NUL"]
        else:
            invalid_paths = ["/dev/null/invalid", ""]
        
        for invalid_path in invalid_paths:
            if invalid_path:  # 跳过空字符串，因为Path("")可能有效
                result = check_file_permissions(invalid_path)
                assert isinstance(result, dict)
    
    def test_very_long_inputs(self):
        """测试很长的输入"""
        long_string = "a" * 10000
        
        # 文件名清理应该能处理很长的字符串
        result = sanitize_filename(long_string)
        assert isinstance(result, str)
        assert len(result) <= len(long_string)
        
        # URL验证应该能处理很长的URL
        long_url = "https://example.com/" + "a" * 1000
        result = validate_url(long_url)
        assert isinstance(result, bool)
    
    def test_unicode_inputs(self):
        """测试Unicode输入"""
        unicode_filename = "测试文件名_файл_🎉.txt"
        
        result = sanitize_filename(unicode_filename)  
        assert isinstance(result, str)
        # Unicode字符应该被保留（除非是非法字符）
        
        unicode_url = "https://example.com/测试路径"
        result = validate_url(unicode_url)
        assert isinstance(result, bool)


# 测试辅助函数
def create_test_file_with_content(path: Path, content: str) -> Path:
    """创建带内容的测试文件"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return path


def create_test_directory_structure(base_path: Path) -> dict[str, Path]:
    """创建测试目录结构"""
    structure = {}
    
    # 创建目录
    dirs = ["dir1", "dir2", "dir1/subdir1", "dir2/subdir2"]
    for dir_name in dirs:
        dir_path = base_path / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)
        structure[dir_name] = dir_path
    
    # 创建文件
    files = [
        ("file1.txt", "Content of file 1"),
        ("dir1/file2.txt", "Content of file 2"),
        ("dir1/subdir1/file3.txt", "Content of file 3"),
        ("dir2/file4.txt", "Content of file 4"),
    ]
    
    for file_path, content in files:
        full_path = base_path / file_path
        create_test_file_with_content(full_path, content)
        structure[file_path] = full_path
    
    return structure


# Pytest fixtures
@pytest.fixture
def temp_dir():
    """临时目录fixture"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def test_file_structure(temp_dir):
    """测试文件结构fixture"""
    return create_test_directory_structure(temp_dir)


@pytest.fixture
def sample_text_file(temp_dir):
    """示例文本文件fixture"""
    file_path = temp_dir / "sample.txt"
    content = "This is a sample text file for testing purposes."
    return create_test_file_with_content(file_path, content)


@pytest.fixture
def sample_binary_file(temp_dir):
    """示例二进制文件fixture"""
    file_path = temp_dir / "sample.bin"
    content = b"\x00\x01\x02\x03\x04\x05\xFF\xFE\xFD"
    file_path.write_bytes(content)
    return file_path