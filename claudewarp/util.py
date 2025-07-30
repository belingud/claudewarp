
from datetime import datetime

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

