// static/js/components/comments.js
// Reusable comments component for domains and reports

window.App = window.App || {};

/**
 * Comments Component - Renders and manages comments for any entity
 * @param {string} containerId - DOM element ID where comments will be rendered
 * @param {string} contentType - Type of entity ('domain' or 'report')
 * @param {number} objectId - ID of the entity
 * @param {object} options - Configuration options
 */
window.App.CommentsComponent = class {
  constructor(containerId, contentType, objectId, options = {}) {
    this.container = document.getElementById(containerId);
    if (!this.container) {
      console.error(`Container ${containerId} not found`);
      return;
    }

    this.contentType = contentType;
    this.objectId = objectId;
    this.options = {
      allowReplies: true,
      maxDepth: 3,
      showAuthorInput: true,
      defaultAuthor: localStorage.getItem('commentAuthor') || '',
      ...options
    };

    this.comments = [];
    this.init();
  }

  /**
   * Initialize component
   */
  async init() {
    this.render();
    await this.loadComments();
  }

  /**
   * Load comments from API
   */
  async loadComments() {
    try {
      const response = await window.API.comments.getForEntity(
        this.contentType,
        this.objectId,
        true,
        false
      );

      this.comments = response.comments || [];
      this.render();
    } catch (error) {
      console.error('Error loading comments:', error);
      this.showError('Error al cargar comentarios');
    }
  }

  /**
   * Render component
   */
  render() {
    const html = `
      <div class="comments-section">
        <div class="comments-header">
          <h4>💬 Comentarios (${this.comments.length})</h4>
        </div>
        
        <div class="comments-form-container">
          ${this.renderCommentForm()}
        </div>

        <div class="comments-list">
          ${this.comments.length > 0 
            ? this.comments.map(c => this.renderComment(c)).join('') 
            : '<p class="no-comments">No hay comentarios aún. ¡Sé el primero en comentar!</p>'}
        </div>
      </div>
    `;

    this.container.innerHTML = html;
    this.attachEventListeners();
  }

  /**
   * Render comment form
   */
  renderCommentForm(parentId = null) {
    const formId = parentId ? `comment-form-${parentId}` : 'comment-form-main';
    const isReply = parentId !== null;

    return `
      <form class="comment-form ${isReply ? 'comment-reply-form' : ''}" data-form-id="${formId}" data-parent-id="${parentId || ''}">
        ${this.options.showAuthorInput ? `
          <input 
            type="text" 
            class="comment-author-input" 
            placeholder="Tu nombre" 
            value="${this.escapeHtml(this.options.defaultAuthor)}"
            required
          />
        ` : ''}
        <textarea 
          class="comment-content-input" 
          placeholder="${isReply ? 'Escribe tu respuesta...' : 'Escribe un comentario...'}" 
          rows="3"
          required
        ></textarea>
        <div class="comment-form-actions">
          ${isReply ? '<button type="button" class="btn comment-cancel-btn">Cancelar</button>' : ''}
          <button type="submit" class="btn-primary">${isReply ? 'Responder' : 'Comentar'}</button>
        </div>
      </form>
    `;
  }

  /**
   * Render single comment with replies
   */
  renderComment(comment, depth = 0) {
    const hasReplies = comment.replies && comment.replies.length > 0;
    const canReply = this.options.allowReplies && depth < this.options.maxDepth;
    const timeAgo = this.getTimeAgo(comment.created_at);

    return `
      <div class="comment ${comment.is_pinned ? 'comment-pinned' : ''}" data-comment-id="${comment.id}" data-depth="${depth}">
        <div class="comment-header">
          <div class="comment-author">
            ${comment.is_pinned ? '<span class="pinned-badge">📌</span>' : ''}
            <strong>${this.escapeHtml(comment.author)}</strong>
            <span class="comment-time">${timeAgo}</span>
          </div>
        </div>
        <div class="comment-content">
          ${this.escapeHtml(comment.content)}
        </div>
        <div class="comment-actions">
          ${canReply ? `<button class="comment-reply-btn btn-link" data-comment-id="${comment.id}">Responder</button>` : ''}
          ${hasReplies ? `<span class="comment-replies-count">${comment.reply_count} ${comment.reply_count === 1 ? 'respuesta' : 'respuestas'}</span>` : ''}
        </div>
        
        <div class="comment-reply-form-container" id="reply-form-${comment.id}" style="display: none;"></div>

        ${hasReplies ? `
          <div class="comment-replies">
            ${comment.replies.map(reply => this.renderComment(reply, depth + 1)).join('')}
          </div>
        ` : ''}
      </div>
    `;
  }

  /**
   * Attach event listeners
   */
  attachEventListeners() {
    // Main comment form
    const mainForm = this.container.querySelector('[data-form-id="comment-form-main"]');
    if (mainForm) {
      mainForm.addEventListener('submit', (e) => this.handleCommentSubmit(e));
    }

    // Reply buttons
    const replyButtons = this.container.querySelectorAll('.comment-reply-btn');
    replyButtons.forEach(btn => {
      btn.addEventListener('click', (e) => this.handleReplyClick(e));
    });
  }

  /**
   * Handle reply button click
   */
  handleReplyClick(e) {
    const commentId = e.target.dataset.commentId;
    const replyContainer = this.container.querySelector(`#reply-form-${commentId}`);
    
    if (replyContainer.style.display === 'none') {
      // Show reply form
      replyContainer.innerHTML = this.renderCommentForm(commentId);
      replyContainer.style.display = 'block';

      // Attach form events
      const form = replyContainer.querySelector('form');
      form.addEventListener('submit', (e) => this.handleCommentSubmit(e));

      const cancelBtn = replyContainer.querySelector('.comment-cancel-btn');
      if (cancelBtn) {
        cancelBtn.addEventListener('click', () => {
          replyContainer.style.display = 'none';
          replyContainer.innerHTML = '';
        });
      }
    } else {
      // Hide reply form
      replyContainer.style.display = 'none';
      replyContainer.innerHTML = '';
    }
  }

  /**
   * Handle comment form submit
   */
  async handleCommentSubmit(e) {
    e.preventDefault();
    const form = e.target;
    const parentId = form.dataset.parentId || null;

    const authorInput = form.querySelector('.comment-author-input');
    const contentInput = form.querySelector('.comment-content-input');

    const author = authorInput ? authorInput.value.trim() : this.options.defaultAuthor;
    const content = contentInput.value.trim();

    if (!author || !content) {
      alert('Por favor completa todos los campos');
      return;
    }

    // Save author to localStorage
    if (authorInput) {
      localStorage.setItem('commentAuthor', author);
    }

    try {
      // Disable form
      const submitBtn = form.querySelector('button[type="submit"]');
      submitBtn.disabled = true;
      submitBtn.textContent = 'Enviando...';

      await window.API.comments.create(
        this.contentType,
        this.objectId,
        author,
        content,
        parentId ? parseInt(parentId) : null
      );

      // Reload comments
      await this.loadComments();

      // Clear form
      contentInput.value = '';
      
      // Hide reply form if it was a reply
      if (parentId) {
        const replyContainer = this.container.querySelector(`#reply-form-${parentId}`);
        if (replyContainer) {
          replyContainer.style.display = 'none';
          replyContainer.innerHTML = '';
        }
      }
    } catch (error) {
      console.error('Error posting comment:', error);
      alert('Error al publicar comentario. Por favor intenta de nuevo.');
      
      // Re-enable form
      const submitBtn = form.querySelector('button[type="submit"]');
      submitBtn.disabled = false;
      submitBtn.textContent = parentId ? 'Responder' : 'Comentar';
    }
  }

  /**
   * Show error message
   */
  showError(message) {
    this.container.innerHTML = `<div class="error-message">${message}</div>`;
  }

  /**
   * Escape HTML to prevent XSS
   */
  escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Get time ago from timestamp
   */
  getTimeAgo(timestamp) {
    if (!timestamp) return '';
    
    const date = new Date(timestamp);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);

    const intervals = {
      año: 31536000,
      mes: 2592000,
      semana: 604800,
      día: 86400,
      hora: 3600,
      minuto: 60
    };

    for (const [name, value] of Object.entries(intervals)) {
      const count = Math.floor(seconds / value);
      if (count >= 1) {
        return `hace ${count} ${name}${count !== 1 ? (name === 'mes' ? 'es' : 's') : ''}`;
      }
    }

    return 'hace un momento';
  }
};

/**
 * Initialize comments for a container
 * Convenience function for easy initialization
 */
window.App.initComments = function(containerId, contentType, objectId, options = {}) {
  return new window.App.CommentsComponent(containerId, contentType, objectId, options);
};
