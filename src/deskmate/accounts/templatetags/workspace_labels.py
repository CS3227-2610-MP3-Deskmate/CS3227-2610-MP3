"""Read the common workspace label from canonical demo membership (ACC-1.2)."""

from django import template

from deskmate.accounts import membership

register = template.Library()


@register.simple_tag(takes_context=True)
def workspace_label(context):
    """Return the stored workspace's canonical code, or unavailable; let reads fail."""
    user = context.request.user
    if not user.is_authenticated or user._state.adding:
        return "unavailable"
    return membership.resolve(user.workspace_id).code or "unavailable"
