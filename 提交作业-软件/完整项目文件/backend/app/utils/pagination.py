def to_offset(page: int, page_size: int) -> int:
    """页码转 SQL offset（页码从 1 开始）。"""
    return (page - 1) * page_size
