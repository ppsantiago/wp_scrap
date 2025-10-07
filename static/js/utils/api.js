// static/js/utils/api.js
// Centralized API helper for all backend calls

window.API = window.API || {};

/**
 * Helper function to make API calls
 */
async function fetchAPI(url, options = {}) {
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      }
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Error desconocido' }));
      throw new Error(error.detail || `Error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}

/**
 * Domains API
 */
window.API.domains = {
  // Get all domains with pagination
  list: async (limit = 100, offset = 0) => {
    return fetchAPI(`/reports/domains?limit=${limit}&offset=${offset}`);
  },

  // Get domain info by name
  getByName: async (domainName) => {
    return fetchAPI(`/reports/domain/${encodeURIComponent(domainName)}`);
  },

  // Get domain with comments
  getWithComments: async (domainName, includeReports = true) => {
    return fetchAPI(`/reports/domain/${encodeURIComponent(domainName)}/with-comments?include_reports=${includeReports}`);
  },

  // Get domain history (reports)
  getHistory: async (domainName, limit = 20, offset = 0, successOnly = false) => {
    return fetchAPI(`/reports/domain/${encodeURIComponent(domainName)}/history?limit=${limit}&offset=${offset}&success_only=${successOnly}`);
  },

  // Get latest report for domain
  getLatest: async (domainName) => {
    return fetchAPI(`/reports/domain/${encodeURIComponent(domainName)}/latest`);
  },

  // Get domains with recent comments
  getWithRecentComments: async (limit = 20) => {
    return fetchAPI(`/reports/domains/with-recent-comments?limit=${limit}`);
  },

  // Delete domain by name
  delete: async (domainName) => {
    return fetchAPI(`/reports/domain/${encodeURIComponent(domainName)}`, {
      method: 'DELETE'
    });
  }
};

/**
 * Reports API
 */
window.API.reports = {
  // Get report by ID
  getById: async (reportId, format = 'frontend') => {
    return fetchAPI(`/reports/report/${reportId}?format=${format}`);
  },

  // Get report with comments
  getWithComments: async (reportId, format = 'frontend') => {
    return fetchAPI(`/reports/report/${reportId}/with-comments?format=${format}`);
  },

  // Get recent reports
  getRecent: async (days = 7, limit = 50) => {
    return fetchAPI(`/reports/recent?days=${days}&limit=${limit}`);
  },

  // Compare reports
  compare: async (domainName, reportIds, metrics) => {
    const metricsStr = Array.isArray(metrics) ? metrics.join(',') : metrics;
    return fetchAPI(`/reports/compare/${encodeURIComponent(domainName)}?report_ids=${reportIds}&metrics=${metricsStr}`);
  },

  // Get trusted contact options and current selection
  getTrustedContact: async (reportId) => {
    return fetchAPI(`/reports/report/${reportId}/trusted-contact`);
  },

  // Update trusted contact selection
  setTrustedContact: async (reportId, { email = null, phone = null } = {}) => {
    return fetchAPI(`/reports/report/${reportId}/trusted-contact`, {
      method: 'PUT',
      body: JSON.stringify({ email, phone })
    });
  },

  // Generate AI report
  generateIa: async (reportId, { type = 'technical', force_refresh = false } = {}) => {
    return fetchAPI(`/reports/report/${reportId}/generate`, {
      method: 'POST',
      body: JSON.stringify({ type, force_refresh })
    });
  },

  // Retrieve AI generation history
  getGenerationHistory: async (reportId, limit = 20) => {
    return fetchAPI(`/reports/report/${reportId}/generation-history?limit=${limit}`);
  },

  // List AI prompts
  listPrompts: async () => {
    return fetchAPI('/reports/settings/prompts');
  },

  // Update AI prompts
  updatePrompts: async (prompts) => {
    return fetchAPI('/reports/settings/prompts', {
      method: 'PUT',
      body: JSON.stringify({ prompts })
    });
  }
};

/**
 * Comments API
 */
window.API.comments = {
  // Create comment
  create: async (contentType, objectId, author, content, parentId = null) => {
    return fetchAPI('/api/comments', {
      method: 'POST',
      body: JSON.stringify({
        content_type: contentType,
        object_id: objectId,
        author: author,
        content: content,
        parent_id: parentId
      })
    });
  },

  // Get comments for entity
  getForEntity: async (contentType, objectId, includeReplies = true, includeInactive = false) => {
    return fetchAPI(`/api/comments/entity/${contentType}/${objectId}?include_replies=${includeReplies}&include_inactive=${includeInactive}`);
  },

  // Get comment thread
  getThread: async (commentId, maxDepth = 5) => {
    return fetchAPI(`/api/comments/thread/${commentId}?max_depth=${maxDepth}`);
  },

  // Get comment by ID
  getById: async (commentId) => {
    return fetchAPI(`/api/comments/${commentId}`);
  },

  // Update comment
  update: async (commentId, updates) => {
    return fetchAPI(`/api/comments/${commentId}`, {
      method: 'PUT',
      body: JSON.stringify(updates)
    });
  },

  // Delete comment
  delete: async (commentId, softDelete = true) => {
    return fetchAPI(`/api/comments/${commentId}?soft_delete=${softDelete}`, {
      method: 'DELETE'
    });
  },

  // Get comments by author
  getByAuthor: async (author, limit = 50, offset = 0) => {
    return fetchAPI(`/api/comments/author/${encodeURIComponent(author)}?limit=${limit}&offset=${offset}`);
  },

  // Get recent comments
  getRecent: async (limit = 20, contentType = null) => {
    const url = contentType 
      ? `/api/comments/recent?limit=${limit}&content_type=${contentType}`
      : `/api/comments/recent?limit=${limit}`;
    return fetchAPI(url);
  },

  // Search comments
  search: async (query, contentType = null, limit = 20) => {
    const url = contentType
      ? `/api/comments/search?q=${encodeURIComponent(query)}&content_type=${contentType}&limit=${limit}`
      : `/api/comments/search?q=${encodeURIComponent(query)}&limit=${limit}`;
    return fetchAPI(url);
  },

  // Get statistics
  getStatistics: async (contentType = null) => {
    const url = contentType
      ? `/api/comments/statistics?content_type=${contentType}`
      : '/api/comments/statistics';
    return fetchAPI(url);
  },

  // Get domain comments (shortcut)
  forDomain: async (domainId, includeReplies = true) => {
    return fetchAPI(`/api/comments/domain/${domainId}?include_replies=${includeReplies}`);
  },

  // Get report comments (shortcut)
  forReport: async (reportId, includeReplies = true) => {
    return fetchAPI(`/api/comments/report/${reportId}?include_replies=${includeReplies}`);
  }
};

/**
 * Statistics API
 */
window.API.statistics = {
  // Get general statistics
  getGeneral: async () => {
    return fetchAPI('/reports/statistics');
  }
};

/**
 * Jobs API
 */
window.API.jobs = {
  // Get jobs with optional filters
  list: async (status = null, jobType = null, limit = 50, offset = 0) => {
    const params = new URLSearchParams({ limit, offset });
    if (status) params.append('status', status);
    if (jobType) params.append('job_type', jobType);
    return fetchAPI(`/api/jobs?${params}`);
  },

  // Get job by ID
  getById: async (jobId) => {
    return fetchAPI(`/api/jobs/${jobId}`);
  },

  // Get job statistics summary
  getStatsSummary: async () => {
    return fetchAPI('/api/jobs/stats/summary');
  },

  // Create batch scraping job
  createBatchScraping: async ({ domains = null, domainsJson = null, name = null, description = null, createdBy = 'user' } = {}) => {
    const payload = {
      created_by: createdBy,
    };

    if (domains && domains.length) {
      payload.domains = domains;
    }
    if (domainsJson !== null && domainsJson !== undefined) {
      payload.domains_json = domainsJson;
    }
    if (name) payload.name = name;
    if (description) payload.description = description;

    return fetchAPI('/api/jobs/batch-scraping', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // Create single scraping job
  createSingleScraping: async (domain, name = null, description = null, createdBy = 'user') => {
    const payload = {
      domain,
      created_by: createdBy,
    };
    if (name) payload.name = name;
    if (description) payload.description = description;

    return fetchAPI('/api/jobs/single-scraping', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // Cancel job
  cancel: async (jobId) => {
    return fetchAPI(`/api/jobs/${jobId}/cancel`, {
      method: 'POST'
    });
  },

  // Delete job
  delete: async (jobId) => {
    return fetchAPI(`/api/jobs/${jobId}`, {
      method: 'DELETE'
    });
  },

  // Retry failed job
  retry: async (jobId) => {
    return fetchAPI(`/api/jobs/${jobId}/retry`, {
      method: 'POST'
    });
  },

  // Get job progress
  getProgress: async (jobId) => {
    return fetchAPI(`/api/jobs/${jobId}/progress`);
  },

  // Get job logs
  getLogs: async (jobId, limit = 100) => {
    return fetchAPI(`/api/jobs/${jobId}/logs?limit=${limit}`);
  }
};
