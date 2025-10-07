import pytest

from app.services.comment_service import CommentService


@pytest.mark.integration
def test_comment_thread_flow(db_session, sample_domain):
    domain, report = sample_domain

    root = CommentService.create_comment(
        db=db_session,
        content_type="domain",
        object_id=domain.id,
        author="root",
        content="Comentario raíz",
    )

    reply = CommentService.create_comment(
        db=db_session,
        content_type="domain",
        object_id=domain.id,
        author="reply",
        content="Respuesta",
        parent_id=root.id,
    )

    comments = CommentService.get_comments_for_entity(
        db=db_session,
        content_type="domain",
        object_id=domain.id,
        include_replies=True,
    )

    assert len(comments) == 1
    assert comments[0].replies
    assert comments[0].replies[0].id == reply.id


@pytest.mark.integration
def test_comment_search_and_statistics(db_session, sample_domain):
    domain, report = sample_domain

    CommentService.create_comment(
        db=db_session,
        content_type="report",
        object_id=report.id,
        author="seo",
        content="Excelente hallazgo",
    )

    results = CommentService.search_comments(db_session, "excelente", content_type="report")
    assert len(results) == 1

    stats = CommentService.get_comment_statistics(db_session, content_type="report")
    assert stats["total_comments"] == 1
    assert stats["active_comments"] == 1


@pytest.mark.integration
def test_comment_soft_delete_filters(db_session, sample_domain):
    domain, _ = sample_domain

    comment = CommentService.create_comment(
        db=db_session,
        content_type="domain",
        object_id=domain.id,
        author="delete",
        content="Será oculto",
    )

    CommentService.delete_comment(db_session, comment.id, soft_delete=True)

    active_comments = CommentService.get_comments_for_entity(
        db_session,
        content_type="domain",
        object_id=domain.id,
        include_replies=False,
    )

    assert not active_comments

    all_comments = CommentService.get_comments_for_entity(
        db_session,
        content_type="domain",
        object_id=domain.id,
        include_replies=False,
        include_inactive=True,
    )

    assert len(all_comments) == 1
