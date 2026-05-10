def mask_identifier(value: str, visible_digits: int = 4) -> str:
    compact = value.strip().replace(" ", "").replace("-", "")
    if not compact:
        return ""
    if len(compact) <= visible_digits:
        return "*" * len(compact)
    return f"{'*' * (len(compact) - visible_digits)}{compact[-visible_digits:]}"

