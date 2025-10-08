window.App = window.App || {};

(function() {
  let promptsState = {
    items: [],
    isSaving: false,
  };

  const selectors = {
    tablist: '#prompts-tablist',
    panels: '#prompts-panels',
    textarea: '.prompt-textarea',
    saveBtn: '#save-prompts-btn',
    resetBtn: '#reset-prompts-btn',
    status: '#prompts-status',
  };

  function setStatus(message, type = 'info') {
    const statusEl = document.querySelector(selectors.status);
    if (!statusEl) return;
    statusEl.textContent = message;
    statusEl.dataset.statusType = type;
  }

  function renderPrompts(prompts) {
    promptsState.items = prompts;
    const tablist = document.querySelector(selectors.tablist);
    const panelsContainer = document.querySelector(selectors.panels);
    if (!tablist || !panelsContainer) return;

    if (!Array.isArray(prompts) || prompts.length === 0) {
      tablist.innerHTML = '';
      panelsContainer.innerHTML = '<p class="muted">No hay prompts configurados.</p>';
      return;
    }
    const tabButtons = [];
    const panelMarkup = [];

    prompts.forEach((prompt, index) => {
      const tabId = `prompt-tab-${prompt.type}`;
      const panelId = `prompt-panel-${prompt.type}`;
      const isActive = index === 0;

      tabButtons.push(`
        <button
          role="tab"
          type="button"
          id="${tabId}"
          class="prompts-tab"
          aria-selected="${isActive}"
          aria-controls="${panelId}"
          data-prompt-type="${prompt.type}"
          tabindex="${isActive ? '0' : '-1'}"
        >
          ${formatType(prompt.type)}
        </button>
      `);

      panelMarkup.push(renderPromptPanel(prompt, {
        tabId,
        panelId,
        isActive,
      }));
    });

    tablist.innerHTML = tabButtons.join('');
    panelsContainer.innerHTML = panelMarkup.join('');

    bindTabEvents();
    bindPromptEditors();
  }

  function renderPromptPanel(prompt, { tabId, panelId, isActive }) {
    const updatedAt = prompt.updated_at ? new Date(prompt.updated_at).toLocaleString() : '—';
    const updatedBy = prompt.updated_by || 'Desconocido';

    return `
      <section
        role="tabpanel"
        id="${panelId}"
        class="prompt-panel${isActive ? ' is-active' : ''}"
        aria-labelledby="${tabId}"
        data-prompt-type="${prompt.type}"
        ${isActive ? '' : 'hidden'}
      >
        <header class="prompt-panel__meta">
          <span class="prompt-panel__badge">${formatType(prompt.type)}</span>
          <span class="muted">Última edición: ${updatedAt} · ${updatedBy}</span>
        </header>
        <div class="prompt-panel__content">
          <div class="prompt-panel__editor">
            <label for="prompt-${prompt.type}">Prompt template (Markdown)</label>
            <textarea id="prompt-${prompt.type}" class="prompt-textarea" rows="14">${escapeHtml(
              prompt.prompt_template || ''
            )}</textarea>
          </div>
          <div class="prompt-panel__preview">
            <h4>Preview</h4>
            <div class="prompt-preview prompt-preview--empty">
              No hay contenido para previsualizar.
            </div>
          </div>
        </div>
      </section>
    `;
  }

  function bindTabEvents() {
    const tablist = document.querySelector(selectors.tablist);
    if (!tablist) return;

    const tabs = Array.from(tablist.querySelectorAll('[role="tab"]'));
    const panels = Array.from(document.querySelectorAll('.prompt-panel'));

    function activateTab(tab) {
      const type = tab.dataset.promptType;
      tabs.forEach((btn) => {
        const isSelected = btn === tab;
        btn.setAttribute('aria-selected', String(isSelected));
        btn.setAttribute('tabindex', isSelected ? '0' : '-1');
        if (isSelected) {
          btn.classList.add('is-active');
          btn.focus();
        } else {
          btn.classList.remove('is-active');
        }
      });

      panels.forEach((panel) => {
        const match = panel.dataset.promptType === type;
        if (match) {
          panel.removeAttribute('hidden');
          panel.classList.add('is-active');
          const textarea = panel.querySelector('.prompt-textarea');
          if (textarea) {
            updatePreviewForTextarea(textarea);
          }
        } else {
          panel.setAttribute('hidden', '');
          panel.classList.remove('is-active');
        }
      });
    }

    function handleTabClick(event) {
      const tab = event.currentTarget;
      activateTab(tab);
    }

    function handleTabKeydown(event) {
      const currentIndex = tabs.indexOf(event.currentTarget);
      if (currentIndex === -1) return;

      let newIndex = null;
      if (['ArrowRight', 'ArrowDown'].includes(event.key)) {
        newIndex = (currentIndex + 1) % tabs.length;
      } else if (['ArrowLeft', 'ArrowUp'].includes(event.key)) {
        newIndex = (currentIndex - 1 + tabs.length) % tabs.length;
      } else if (event.key === 'Home') {
        newIndex = 0;
      } else if (event.key === 'End') {
        newIndex = tabs.length - 1;
      }

      if (newIndex !== null) {
        event.preventDefault();
        activateTab(tabs[newIndex]);
      }
    }

    tabs.forEach((tab) => {
      tab.addEventListener('click', handleTabClick);
      tab.addEventListener('keydown', handleTabKeydown);
    });
  }

  function bindPromptEditors() {
    const panelsContainer = document.querySelector(selectors.panels);
    if (!panelsContainer) return;

    panelsContainer.querySelectorAll('.prompt-textarea').forEach((textarea) => {
      textarea.addEventListener('input', handlePromptInput);
      updatePreviewForTextarea(textarea);
    });
  }

  function updatePreviewForTextarea(textarea) {
    if (!textarea) return;
    const panel = textarea.closest('[data-prompt-type]');
    if (!panel) return;

    const previewContainer = panel.querySelector('.prompt-preview');
    if (!previewContainer) return;

    const value = textarea.value.trim();
    if (!value) {
      previewContainer.innerHTML = '<p class="muted">No hay contenido para previsualizar.</p>';
      previewContainer.classList.add('prompt-preview--empty');
      return;
    }

    previewContainer.classList.remove('prompt-preview--empty');

    if (typeof window === 'undefined') {
      previewContainer.textContent = value;
      return;
    }

    if (typeof window.marked === 'function' || (window.marked && typeof window.marked.parse === 'function')) {
      const parseFn = typeof window.marked.parse === 'function' ? window.marked.parse.bind(window.marked) : window.marked;
      try {
        previewContainer.innerHTML = parseFn(value, { breaks: true, gfm: true });
      } catch (error) {
        console.warn('Error renderizando preview Markdown:', error);
        previewContainer.textContent = value;
      }
    } else {
      previewContainer.textContent = value;
    }
  }

  function handlePromptInput(event) {
    const textarea = event.target;
    updatePreviewForTextarea(textarea);
  }

  function formatType(type) {
    if (!type) return 'Desconocido';
    const map = {
      technical: 'Reporte técnico',
      commercial: 'Reporte comercial',
      deliverable: 'Reporte entregable',
    };
    return map[type] || type;
  }

  function escapeHtml(text) {
    if (typeof text !== 'string') return '';
    const map = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;',
    };
    return text.replace(/[&<>"']/g, (m) => map[m]);
  }

  function getEditedPrompts() {
    const panelsContainer = document.querySelector(selectors.panels);
    if (!panelsContainer) return [];

    return Array.from(panelsContainer.querySelectorAll('[data-prompt-type]')).map((panel) => {
      const type = panel.dataset.promptType;
      const textarea = panel.querySelector('.prompt-textarea');
      return {
        type,
        prompt_template: textarea ? textarea.value : '',
      };
    });
  }

  async function loadPrompts() {
    try {
      const response = await window.API.reports.listPrompts();
      renderPrompts(response.prompts || []);
      setStatus('Prompts cargados.', 'success');
    } catch (error) {
      console.error('Error cargando prompts IA:', error);
      const panelsContainer = document.querySelector(selectors.panels);
      if (panelsContainer) {
        panelsContainer.innerHTML = '<div class="error-message">No se pudieron cargar los prompts IA.</div>';
      }
      const tablist = document.querySelector(selectors.tablist);
      if (tablist) {
        tablist.innerHTML = '';
      }
      setStatus('Error al cargar prompts IA.', 'error');
    }
  }

  async function savePrompts() {
    if (promptsState.isSaving) return;

    const payload = getEditedPrompts();
    if (payload.length === 0) {
      setStatus('No hay prompts para guardar.', 'info');
      return;
    }

    promptsState.isSaving = true;
    toggleActions(true);
    setStatus('Guardando cambios...', 'info');

    try {
      const response = await window.API.reports.updatePrompts(payload);
      renderPrompts(response.prompts || []);
      setStatus('Prompts actualizados correctamente.', 'success');
    } catch (error) {
      console.error('Error guardando prompts IA:', error);
      setStatus('Error al guardar los prompts.', 'error');
    } finally {
      promptsState.isSaving = false;
      toggleActions(false);
    }
  }

  function resetPrompts() {
    renderPrompts(promptsState.items);
    setStatus('Se restauraron los cambios sin guardar.', 'info');
  }

  function toggleActions(disabled) {
    const saveBtn = document.querySelector(selectors.saveBtn);
    const resetBtn = document.querySelector(selectors.resetBtn);

    if (saveBtn) {
      saveBtn.disabled = disabled;
      saveBtn.textContent = disabled ? 'Guardando...' : 'Guardar cambios';
    }
    if (resetBtn) {
      resetBtn.disabled = disabled;
    }
  }

  function ensureMarked() {
    if (typeof window === 'undefined') return;
    if (typeof window.marked === 'function' || (window.marked && typeof window.marked.parse === 'function')) {
      return;
    }

    if (!document.getElementById('marked-js')) {
      const script = document.createElement('script');
      script.id = 'marked-js';
      script.src = 'https://cdn.jsdelivr.net/npm/marked/marked.min.js';
      script.async = true;
      script.onerror = () => console.error('No se pudo cargar marked.js para previews.');
      document.head.appendChild(script);
    }
  }

  function bindGlobalActions() {
    const saveBtn = document.querySelector(selectors.saveBtn);
    const resetBtn = document.querySelector(selectors.resetBtn);

    if (saveBtn) {
      saveBtn.addEventListener('click', savePrompts);
    }

    if (resetBtn) {
      resetBtn.addEventListener('click', resetPrompts);
    }
  }

  window.App.initSettings = async function() {
    ensureMarked();
    await loadPrompts();
    bindGlobalActions();
  };
})();
