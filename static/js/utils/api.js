// static/js/utils/api.js
// Centralized API helper for all backend calls

window.API = window.API || {};

/**
 * Base API configuration
 */
const API_BASE = '';

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
  }
};

/**
 * Comments API
 */
window.API.comments = {
  // Create comment
  create: async (contentType, objectId, author, content, parentId = null) => {
    return fetchAPI('/comments', {
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
    return fetchAPI(`/comments/entity/${contentType}/${objectId}?include_replies=${includeReplies}&include_inactive=${includeInactive}`);
  },

  // Get comment thread
  getThread: async (commentId, maxDepth = 5) => {
    return fetchAPI(`/comments/thread/${commentId}?max_depth=${maxDepth}`);
  },

  // Get comment by ID
  getById: async (commentId) => {
    return fetchAPI(`/comments/${commentId}`);
  },

  // Update comment
  update: async (commentId, updates) => {
    return fetchAPI(`/comments/${commentId}`, {
      method: 'PUT',
      body: JSON.stringify(updates)
    });
  },

  // Delete comment
  delete: async (commentId, softDelete = true) => {
    return fetchAPI(`/comments/${commentId}?soft_delete=${softDelete}`, {
      method: 'DELETE'
    });
  },

  // Get comments by author
  getByAuthor: async (author, limit = 50, offset = 0) => {
    return fetchAPI(`/comments/author/${encodeURIComponent(author)}?limit=${limit}&offset=${offset}`);
  },

  // Get recent comments
  getRecent: async (limit = 20, contentType = null) => {
    const url = contentType 
      ? `/comments/recent?limit=${limit}&content_type=${contentType}`
      : `/comments/recent?limit=${limit}`;
    return fetchAPI(url);
  },

  // Search comments
  search: async (query, contentType = null, limit = 20) => {
    const url = contentType
      ? `/comments/search?q=${encodeURIComponent(query)}&content_type=${contentType}&limit=${limit}`
      : `/comments/search?q=${encodeURIComponent(query)}&limit=${limit}`;
    return fetchAPI(url);
  },

  // Get statistics
  getStatistics: async (contentType = null) => {
    const url = contentType
      ? `/comments/statistics?content_type=${contentType}`
      : '/comments/statistics';
    return fetchAPI(url);
  },

  // Get domain comments (shortcut)
  forDomain: async (domainId, includeReplies = true) => {
    return fetchAPI(`/comments/domain/${domainId}?include_replies=${includeReplies}`);
  },

  // Get report comments (shortcut)
  forReport: async (reportId, includeReplies = true) => {
    return fetchAPI(`/comments/report/${reportId}?include_replies=${includeReplies}`);
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
 * Tools API (existing scraper)
 */
window.API.tools = {
  // Check/scrape domain
  checkDomain: async (domain) => {
    return fetchAPI(`/check-domain?domain=${encodeURIComponent(domain)}`);
  }
};
