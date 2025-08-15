from datetime import datetime

from pydantic import ValidationError


def _format_datetime(iso_string: str) -> str:
    """格式化日期时间

    Args:
        iso_string: ISO格式的日期时间字符串

    Returns:
        str: 格式化的日期时间
    """
    try:
        dt = datetime.fromisoformat(iso_string)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        print(f"Unexpected error: {e}")
        return iso_string


def _mask_api_key(api_key: str, show_chars: int = 4) -> str:
    """遮蔽API密钥

    Args:
        api_key: 原始API密钥
        show_chars: 显示的字符数

    Returns:
        str: 遮蔽后的API密钥
    """
    if len(api_key) <= show_chars * 2:
        return "*" * len(api_key)

    return f"{api_key[:show_chars]}{'*' * (len(api_key) - show_chars * 2)}{api_key[-show_chars:]}"


def format_validation_error(e: ValidationError) -> str:
    """格式化Pydantic验证错误, 提取核心信息"""
    error_messages = []
    for error in e.errors():
        msg = error["msg"]
        # 移除 "Value error, " 前缀
        if msg.startswith("Value error, "):
            msg = msg[len("Value error, ") :]
        error_messages.append(msg)
    return "\n".join(error_messages)
