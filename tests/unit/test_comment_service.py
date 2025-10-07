from datetime import datetime, timedelta

import pytest

from app.models import Comment
from app.services.comment_service import CommentService


@pytest.mark.unit
def test_create_comment_success(db_session, sample_domain):
    domain, _ = sample_domain

    comment = CommentService.create_comment(
        db=db_session,
        content_type="domain",
        object_id=domain.id,
        author="pytest",
        content="Comentario de prueba",
    )

    assert comment.id is not None
    assert comment.content == "Comentario de prueba"
    assert comment.author == "pytest"


@pytest.mark.unit
def test_create_comment_invalid_parent(db_session, sample_domain):
    domain, _ = sample_domain

    orphan = CommentService.create_comment(
        db=db_session,
        content_type="domain",
        object_id=domain.id,
        author="orphan",
        content="Sin padre",
        parent_id=None,
    )

    ghost = CommentService.create_comment(
        db=db_session,
        content_type="domain",
        object_id=domain.id,
        author="ghost",
        content="Parent inexistente",
        parent_id=9999,
    )

    assert ghost.parent_id == 9999
    assert ghost.id != orphan.id


@pytest.mark.unit
def test_update_comment_pin_and_content(db_session, sample_domain):
    domain, _ = sample_domain

    comment = CommentService.create_comment(
        db=db_session,
        content_type="domain",
        object_id=domain.id,
        author="pytest",
        content="Original",
    )

    updated = CommentService.update_comment(
        db=db_session,
        comment_id=comment.id,
        content="Actualizado",
        is_pinned=True,
    )

    assert updated.content == "Actualizado"
    assert updated.is_pinned is True


@pytest.mark.unit
def test_delete_comment_soft(db_session, sample_domain):
    domain, _ = sample_domain

    comment = CommentService.create_comment(
        db=db_session,
        content_type="domain",
        object_id=domain.id,
        author="pytest",
        content="Para borrar",
    )

    CommentService.delete_comment(db=db_session, comment_id=comment.id, soft_delete=True)

    stored = db_session.get(Comment, comment.id)
    assert stored.is_active is False


@pytest.mark.unit
def test_delete_comment_hard(db_session, sample_domain):
    domain, _ = sample_domain

    comment = CommentService.create_comment(
        db=db_session,
        content_type="domain",
        object_id=domain.id,
        author="pytest",
        content="Eliminar definitivamente",
    )

    CommentService.delete_comment(db=db_session, comment_id=comment.id, soft_delete=False)

    assert db_session.get(Comment, comment.id) is None


@pytest.mark.unit
def test_get_comment_by_id(db_session, sample_domain):
    domain, _ = sample_domain

    comment = CommentService.create_comment(
        db=db_session,
        content_type="domain",
        object_id=domain.id,
        author="pytest",
        content="Buscar",
    )

    fetched = CommentService.get_comment_by_id(db_session, comment.id)
    assert fetched is not None
    assert fetched.id == comment.id


@pytest.mark.unit
def test_get_comments_by_author(db_session, sample_domain):
    domain, _ = sample_domain

    old_comment = CommentService.create_comment(
        db=db_session,
        content_type="domain",
        object_id=domain.id,
        author="pytest-author",
        content="Antiguo",
    )
    # Ajustar timestamps para validar orden
    old_comment.created_at = datetime.utcnow() - timedelta(minutes=5)
    db_session.commit()

    new_comment = CommentService.create_comment(
        db=db_session,
        content_type="domain",
        object_id=domain.id,
        author="pytest-author",
        content="Reciente",
    )

    comments = CommentService.get_comments_by_author(db_session, author="pytest-author")
    assert len(comments) == 2
    assert comments[0].id == new_comment.id
