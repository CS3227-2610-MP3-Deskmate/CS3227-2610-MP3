"""Article authoring by Support Officers (KB-1) and reading by Requesters (KB-2),
each within the current workspace."""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from deskmate.accounts.models import Role
from deskmate.knowledge.forms import DUPLICATE, ArticleForm
from deskmate.knowledge.models import TITLE_UNIQUE, Article
from deskmate.views import forbidden


def _officer(view):
    """Apply the existing sign-in and role responses to an authoring view."""

    @wraps(view)
    @login_required(login_url="sign-in", redirect_field_name=None)
    def guarded(request, *args, **kwargs):
        """Check the stored role before any article is read."""
        if request.user.role != Role.SUPPORT_OFFICER:
            return forbidden(request, "This page is not for your role.")
        return view(request, *args, **kwargs)

    return guarded


def _requester(view):
    """Apply the existing sign-in and role responses to a reading view."""

    @wraps(view)
    @login_required(login_url="sign-in", redirect_field_name=None)
    def guarded(request, *args, **kwargs):
        """Check the stored role before any article is read."""
        if request.user.role != Role.REQUESTER:
            return forbidden(request, "This page is not for your role.")
        return view(request, *args, **kwargs)

    return guarded


def _article_id(value):
    """Return `value` as a normalised decimal article identifier (Routes).

    The route accepts only ASCII digits, and leading zeros name the same
    article. An identifier too long for the record's integer column cannot
    name one, so it gets the same generic 404 as a missing article.
    """
    value = value.lstrip("0") or "0"
    if len(value) > 19:
        raise Http404
    return value


@require_GET
@_officer
def article_list(request):
    """List only the current stored workspace's articles in creation order."""
    return render(
        request,
        "knowledge/list.html",
        {
            "title": "Knowledge base",
            "articles": Article.objects.filter(workspace_id=request.user.workspace_id),
        },
    )


@require_http_methods(["GET", "POST"])
@_officer
def article_form(request, article_id=None):
    """Create or atomically edit an article, handling only title conflicts locally."""
    workspace_id = request.user.workspace_id
    if article_id is not None:
        article_id = _article_id(article_id)
    article = (
        Article(workspace_id=workspace_id)
        if article_id is None
        else get_object_or_404(Article, pk=article_id, workspace_id=workspace_id)
    )
    form = ArticleForm(
        data=request.POST if request.method == "POST" else None, instance=article
    )
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                form.save()
        except IntegrityError as error:
            diagnostic = getattr(error.__cause__, "diag", None)
            if getattr(diagnostic, "constraint_name", None) != TITLE_UNIQUE:
                raise
            form.add_error("title", DUPLICATE)
        else:
            return redirect("article-edit", article_id=article.pk)
    return render(
        request,
        "knowledge/form.html",
        {
            "title": "New article" if article_id is None else "Edit article",
            "form": form.redisplay(),
        },
    )


@require_GET
@_requester
def article_reading_list(request):
    """List only the current stored workspace's articles in creation order."""
    return render(
        request,
        "knowledge/reading_list.html",
        {
            "title": "Knowledge base",
            "articles": Article.objects.filter(workspace_id=request.user.workspace_id),
        },
    )


@require_GET
@_requester
def article_reading(request, article_id):
    """Show an article in the current stored workspace, or the generic 404."""
    article = get_object_or_404(
        Article,
        pk=_article_id(article_id),
        workspace_id=request.user.workspace_id,
    )
    return render(
        request,
        "knowledge/article.html",
        {"title": "Article", "article": article},
    )
