"""Small, dependency-free User-Agent sniffing — just enough to show
'Chrome on Windows' / 'Safari on iPhone' in a sessions list. Not meant
to be exhaustive; falls back to 'Unknown device' rather than guessing
wrong, since this is display-only and never used for logic.
"""
import re


def parse_device_label(user_agent: str) -> str:
    if not user_agent:
        return "Unknown device"

    ua = user_agent

    if "iPhone" in ua:
        os_label = "iPhone"
    elif "iPad" in ua:
        os_label = "iPad"
    elif "Android" in ua:
        os_label = "Android"
    elif "Windows" in ua:
        os_label = "Windows"
    elif "Macintosh" in ua or "Mac OS X" in ua:
        os_label = "Mac"
    elif "Linux" in ua:
        os_label = "Linux"
    else:
        os_label = "Unknown OS"

    if "Edg/" in ua:
        browser = "Edge"
    elif "OPR/" in ua or "Opera" in ua:
        browser = "Opera"
    elif "Chrome/" in ua and "Chromium" not in ua:
        browser = "Chrome"
    elif "CriOS" in ua:
        browser = "Chrome"
    elif "FxiOS" in ua:
        browser = "Firefox"
    elif "Firefox/" in ua:
        browser = "Firefox"
    elif "Safari/" in ua and "Version/" in ua:
        browser = "Safari"
    else:
        browser = None

    if browser:
        return f"{browser} on {os_label}"
    return os_label


def get_client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
