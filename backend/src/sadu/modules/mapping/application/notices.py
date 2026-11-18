from sadu.shared.ports.notify import Notice

URGENT_ELEMENTS = "notice.map_urgent"
APPROVAL_OVERDUE = "notice.approval_overdue"


def urgent_elements_notice(wall_name: str, urgent: int, link: str) -> Notice:
    return Notice(
        kind=URGENT_ELEMENTS,
        text=f"تلف عاجل في {wall_name} يحتاج قرار مختص، العناصر العاجلة: {urgent}",
        link=link,
        fields={"wall": wall_name, "urgent": urgent},
    )


def approval_overdue_notice(wall_name: str, waiting_days: int, link: str) -> Notice:
    return Notice(
        kind=APPROVAL_OVERDUE,
        text=f"مخطط {wall_name} ينتظر الاعتماد، أيام الانتظار: {waiting_days}",
        link=link,
        fields={"wall": wall_name, "waiting_days": waiting_days},
    )
