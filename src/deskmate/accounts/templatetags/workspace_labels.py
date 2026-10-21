"""Read the common workspace label from canonical demo membership (ACC-1.2)."""

from django import template

from deskmate.accounts import demo
from deskmate.accounts.models import User

register = template.Library()


@register.simple_tag(takes_context=True)
def workspace_label(context):
    """Return the stored workspace's canonical code, or unavailable; let reads fail."""
    user = context.request.user
    if not user.is_authenticated or user._state.adding:
        return "unavailable"
    members = list(
        User.objects.filter(workspace_id=user.workspace_id).values_list(
            "username", "role"
        )[:4]
    )
    if len(members) != len(demo.ACCOUNTS):
        return "unavailable"
    code = members[0][0].rpartition("-")[2]
    if len(code) != demo.CODE_LENGTH or any(char not in demo.ALPHABET for char in code):
        return "unavailable"
    expected = {(f"{prefix}-{code}", role) for prefix, role in demo.ACCOUNTS}
    return code if set(members) == expected else "unavailable"
