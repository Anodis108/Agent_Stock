/**
 * Cây Kiến Thức LLM Engineer Handbook
 * Phase 4 & Phase 5: Dynamic Tree, Content Viewer & Realtime Search Validation
 */

document.addEventListener('DOMContentLoaded', () => {
  console.log('🌳 [Knowledge Tree] Initializing application...');

  if (typeof KNOWLEDGE_DATA === 'undefined') {
    console.error('❌ KNOWLEDGE_DATA is not defined. Please check knowledge-data.js load order.');
    return;
  }

  // 1. Initialize Stats on Welcome Screen
  initWelcomeStats();

  // 2. Render Full Dynamic Tree from KNOWLEDGE_DATA
  renderKnowledgeTree();

  // 3. Initialize Interactive Behaviors & Toolbar Controls
  initTreeInteractions();
  initToolbarControls();
  initRealtimeSearch();
  initWelcomeModuleCards();
  initBrandNavigation();

  // Update Status Badge
  const statusBadge = document.getElementById('setup-status');
  if (statusBadge) {
    statusBadge.textContent = 'Phase 5: Search & Full MVP';
  }

  console.log('✅ [Knowledge Tree] Phase 5: Fully Initialized & Verified.');
});

/**
 * Updates stats in Welcome View from metadata
 */
function initWelcomeStats() {
  const stats = KNOWLEDGE_DATA.metadata;
  const modEl = document.getElementById('stat-modules');
  const lesEl = document.getElementById('stat-lessons');
  const topEl = document.getElementById('stat-topics');

  if (modEl) modEl.textContent = stats.totalModules;
  if (lesEl) lesEl.textContent = stats.totalLessons;
  if (topEl) topEl.textContent = stats.totalTopics;
}

/**
 * Builds the entire HTML tree dynamically from KNOWLEDGE_DATA
 */
function renderKnowledgeTree() {
  const treeContainer = document.getElementById('tree-container');
  if (!treeContainer) return;

  const data = KNOWLEDGE_DATA;
  let html = `<ul class="tree-root">`;

  // Root Node
  html += `
    <li class="tree-node is-expanded" data-level="0" id="node-root">
      <div class="node-header">
        <span class="toggle-icon">▼</span>
        <span class="node-icon">📚</span>
        <span class="node-title">${escapeHtml(data.metadata.title)}</span>
        <span class="node-badge">${data.metadata.totalModules} Modules</span>
      </div>
      <ul class="tree-children">
  `;

  // Iterate Modules
  data.modules.forEach((mod) => {
    // Expand Module 1 and Intro by default
    const isModExpanded = mod.id === 'module-1' || mod.id === 'module-intro';
    const modToggleIcon = isModExpanded ? '▼' : '▶';
    const modDisplay = isModExpanded ? 'block' : 'none';
    const modExpandedClass = isModExpanded ? 'is-expanded' : '';

    html += `
      <li class="tree-node ${modExpandedClass}" data-level="1" data-node-type="module" data-id="${mod.id}">
        <div class="node-header">
          <span class="toggle-icon">${modToggleIcon}</span>
          <span class="node-icon">${mod.icon || '📦'}</span>
          <span class="node-title" title="${escapeHtml(mod.title)}">${escapeHtml(mod.title)}</span>
          <span class="node-badge">${mod.badge || `${mod.lessons.length} bài`}</span>
        </div>
        <ul class="tree-children" style="display: ${modDisplay};">
    `;

    // Iterate Lessons
    mod.lessons.forEach((lesson) => {
      const isLesExpanded = false;
      const lesToggleIcon = isLesExpanded ? '▼' : '▶';
      const lesDisplay = isLesExpanded ? 'block' : 'none';
      const lesExpandedClass = isLesExpanded ? 'is-expanded' : '';

      html += `
        <li class="tree-node ${lesExpandedClass}" data-level="2" data-node-type="lesson" data-id="${lesson.id}">
          <div class="node-header">
            <span class="toggle-icon">${lesToggleIcon}</span>
            <span class="node-icon">📖</span>
            <span class="node-title" title="${escapeHtml(lesson.title)}">${escapeHtml(lesson.title)}</span>
            <span class="node-badge">${lesson.badge || `${lesson.topics.length} mục`}</span>
          </div>
          <ul class="tree-children" style="display: ${lesDisplay};">
      `;

      // Iterate Topics (Leaf nodes)
      lesson.topics.forEach((topic) => {
        html += `
          <li class="tree-node is-leaf" data-level="3" data-node-type="topic" data-id="${topic.id}">
            <div class="node-header">
              <span class="node-bullet">•</span>
              <span class="node-icon">🔹</span>
              <span class="node-title" title="${escapeHtml(topic.title)}">${escapeHtml(topic.title)}</span>
            </div>
          </li>
        `;
      });

      html += `</ul></li>`; // End Lesson
    });

    html += `</ul></li>`; // End Module
  });

  html += `</ul></li></ul>`; // End Root

  treeContainer.innerHTML = html;
}

/**
 * Handles clicks inside the dynamic tree
 */
function initTreeInteractions() {
  const treeContainer = document.getElementById('tree-container');
  if (!treeContainer) return;

  treeContainer.addEventListener('click', (event) => {
    const nodeHeader = event.target.closest('.node-header');
    if (!nodeHeader) return;

    const treeNode = nodeHeader.closest('.tree-node');
    if (!treeNode) return;

    const nodeType = treeNode.getAttribute('data-node-type');
    const nodeId = treeNode.getAttribute('data-id');

    // 1. Root node clicked -> show welcome view
    if (treeNode.id === 'node-root') {
      const toggleIcon = nodeHeader.querySelector('.toggle-icon');
      const children = treeNode.querySelector(':scope > .tree-children');
      if (event.target.closest('.toggle-icon')) {
        toggleNodeExpansion(treeNode, children, toggleIcon);
      } else {
        showWelcomeView();
      }
      return;
    }

    // 2. Parent node (Module or Lesson) -> Toggle expand/collapse
    const childrenContainer = treeNode.querySelector(':scope > .tree-children');
    const toggleIcon = nodeHeader.querySelector('.toggle-icon');

    if (childrenContainer) {
      toggleNodeExpansion(treeNode, childrenContainer, toggleIcon);
    } else if (nodeType === 'topic') {
      // 3. Leaf node (Topic) -> Select & render article content
      selectTopic(nodeId, treeNode);
    }
  });
}

/**
 * Toggles expand/collapse state of a tree node
 */
function toggleNodeExpansion(node, childrenContainer, toggleIcon) {
  if (!childrenContainer) return;
  const isExpanded = node.classList.contains('is-expanded');

  if (isExpanded) {
    node.classList.remove('is-expanded');
    childrenContainer.style.display = 'none';
    if (toggleIcon) toggleIcon.textContent = '▶';
  } else {
    node.classList.add('is-expanded');
    childrenContainer.style.display = 'block';
    if (toggleIcon) toggleIcon.textContent = '▼';
  }
}

/**
 * Selects a topic, highlights it, and populates the article view
 */
function selectTopic(topicId, targetNode = null) {
  let targetTopic = null;
  let targetLesson = null;
  let targetModule = null;

  for (const mod of KNOWLEDGE_DATA.modules) {
    for (const les of mod.lessons) {
      for (const top of les.topics) {
        if (top.id === topicId) {
          targetTopic = top;
          targetLesson = les;
          targetModule = mod;
          break;
        }
      }
      if (targetTopic) break;
    }
    if (targetTopic) break;
  }

  if (!targetTopic) return;

  // Update active state in tree DOM
  document.querySelectorAll('.tree-node.is-active').forEach(n => n.classList.remove('is-active'));
  const nodeEl = targetNode || document.querySelector(`.tree-node[data-id="${topicId}"]`);
  if (nodeEl) {
    nodeEl.classList.add('is-active');

    // Ensure parents are expanded
    let parent = nodeEl.parentElement.closest('.tree-node');
    while (parent) {
      parent.classList.add('is-expanded');
      const children = parent.querySelector(':scope > .tree-children');
      const toggle = parent.querySelector(':scope > .node-header > .toggle-icon');
      if (children) children.style.display = 'block';
      if (toggle) toggle.textContent = '▼';
      parent = parent.parentElement.closest('.tree-node');
    }
  }

  // Render article view
  renderArticleContent(targetTopic, targetLesson, targetModule);
}

/**
 * Renders the Article View dynamically for the selected topic
 */
function renderArticleContent(topic, lesson, module) {
  const welcomeView = document.getElementById('welcome-view');
  const articleView = document.getElementById('article-view');
  const breadcrumbEl = document.getElementById('content-breadcrumb');
  const contentBodyEl = document.getElementById('content-body');
  const viewport = document.getElementById('content-viewport');

  if (welcomeView) welcomeView.style.display = 'none';
  if (articleView) articleView.style.display = 'flex';

  // 1. Breadcrumbs
  if (breadcrumbEl) {
    breadcrumbEl.innerHTML = `
      <span class="crumb crumb-link" id="crumb-home-link" title="Về màn hình chính">LLM Engineer Handbook</span>
      <span class="crumb-separator">/</span>
      <span class="crumb">${escapeHtml(module.title)}</span>
      <span class="crumb-separator">/</span>
      <span class="crumb">${escapeHtml(lesson.title)}</span>
      <span class="crumb-separator">/</span>
      <span class="crumb crumb-current">${escapeHtml(topic.title)}</span>
    `;

    const homeCrumb = document.getElementById('crumb-home-link');
    if (homeCrumb) {
      homeCrumb.addEventListener('click', showWelcomeView);
    }
  }

  // 2. Article Body
  if (contentBodyEl) {
    let bodyHtml = `
      <div class="article-header">
        <span class="article-tag">${escapeHtml(module.title.split(':')[0] || 'Chủ đề')}</span>
        <h2 class="article-title">${escapeHtml(topic.title)}</h2>
        ${topic.lead ? `<p class="article-lead">${escapeHtml(topic.lead)}</p>` : ''}
      </div>
    `;

    // Concept Section
    if (topic.concept && topic.concept.trim()) {
      bodyHtml += `
        <div class="content-section">
          <h3 class="section-title">💡 Khái niệm & Kiến trúc</h3>
          <div class="concept-content">
            ${formatMarkdownContent(topic.concept)}
          </div>
        </div>
      `;
    }

    // Code Example Section
    if (topic.code && topic.code.trim()) {
      bodyHtml += `
        <div class="content-section">
          <h3 class="section-title">💻 Code mẫu thực chiến</h3>
          <div class="code-block">
            <div class="code-header">
              <span class="code-lang">${escapeHtml(topic.codeLang || 'python')}</span>
              <button type="button" class="copy-btn" title="Sao chép code">Copy</button>
            </div>
            <pre><code>${escapeHtml(topic.code)}</code></pre>
          </div>
        </div>
      `;
    }

    // Best Practice / Tip Section
    if (topic.tip && topic.tip.trim()) {
      bodyHtml += `
        <div class="content-section">
          <div class="callout-card callout-tip">
            <div class="callout-title">📌 Mẹo & Lưu ý thực chiến</div>
            <p>${escapeHtml(topic.tip)}</p>
          </div>
        </div>
      `;
    }

    contentBodyEl.innerHTML = bodyHtml;

    // Attach copy button handler for newly rendered code block
    initCopyCodeButtons();
  }

  // Scroll viewport to top
  if (viewport) {
    viewport.scrollTop = 0;
  }
}

/**
 * Returns to Welcome Screen
 */
function showWelcomeView() {
  const welcomeView = document.getElementById('welcome-view');
  const articleView = document.getElementById('article-view');
  const viewport = document.getElementById('content-viewport');

  if (welcomeView) welcomeView.style.display = 'block';
  if (articleView) articleView.style.display = 'none';

  document.querySelectorAll('.tree-node.is-active').forEach(node => {
    node.classList.remove('is-active');
  });

  if (viewport) {
    viewport.scrollTop = 0;
  }
}

/**
 * Clicking the brand title or logo returns to welcome view
 */
function initBrandNavigation() {
  const brand = document.getElementById('brand-home');
  if (brand) {
    brand.addEventListener('click', showWelcomeView);
  }
}

/**
 * Clicking a module card on the welcome screen expands that module in the tree
 */
function initWelcomeModuleCards() {
  document.querySelectorAll('.module-card[data-mod-id]').forEach(card => {
    card.addEventListener('click', () => {
      const modId = card.getAttribute('data-mod-id');
      const modNode = document.querySelector(`.tree-node[data-id="${modId}"]`);
      if (modNode) {
        modNode.classList.add('is-expanded');
        const children = modNode.querySelector(':scope > .tree-children');
        const toggle = modNode.querySelector(':scope > .node-header > .toggle-icon');
        if (children) children.style.display = 'block';
        if (toggle) toggle.textContent = '▼';
        modNode.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    });
  });
}

/**
 * Initializes toolbar buttons (Expand All, Collapse All)
 */
function initToolbarControls() {
  const expandAllBtn = document.getElementById('expand-all-btn');
  const collapseAllBtn = document.getElementById('collapse-all-btn');

  if (expandAllBtn) {
    expandAllBtn.addEventListener('click', () => {
      document.querySelectorAll('.tree-node').forEach(node => {
        const children = node.querySelector(':scope > .tree-children');
        const toggle = node.querySelector(':scope > .node-header > .toggle-icon');
        if (children) {
          node.classList.add('is-expanded');
          children.style.display = 'block';
          if (toggle) toggle.textContent = '▼';
        }
      });
    });
  }

  if (collapseAllBtn) {
    collapseAllBtn.addEventListener('click', () => {
      document.querySelectorAll('.tree-node[data-level]:not([data-level="0"])').forEach(node => {
        const children = node.querySelector(':scope > .tree-children');
        const toggle = node.querySelector(':scope > .node-header > .toggle-icon');
        if (children) {
          node.classList.remove('is-expanded');
          children.style.display = 'none';
          if (toggle) toggle.textContent = '▶';
        }
      });
    });
  }
}

/**
 * Phase 5: Realtime Search, Tree Filtering, Highlighting & Empty State
 */
function initRealtimeSearch() {
  const searchInput = document.getElementById('tree-search-input');
  const clearSearchBtn = document.getElementById('clear-search-btn');

  if (!searchInput) return;

  let debounceTimer = null;

  searchInput.addEventListener('input', () => {
    const query = searchInput.value;
    if (clearSearchBtn) clearSearchBtn.hidden = !query.trim();

    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      handleTreeSearch(query);
    }, 150);
  });

  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      clearSearchFilter();
    }
  });

  if (clearSearchBtn) {
    clearSearchBtn.addEventListener('click', clearSearchFilter);
  }
}

/**
 * Filters the tree nodes based on search query
 */
function handleTreeSearch(query) {
  const trimmed = query.trim();
  if (!trimmed) {
    clearSearchFilter();
    return;
  }

  // 1. Reset all previous highlights and hidden states
  document.querySelectorAll('.is-search-hidden').forEach(n => n.classList.remove('is-search-hidden'));
  document.querySelectorAll('.search-highlight').forEach(mark => {
    mark.outerHTML = mark.textContent;
  });

  // Safe Regex matching (escape special characters)
  const escapedQuery = trimmed.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const regex = new RegExp(`(${escapedQuery})`, 'gi');

  // 2. Perform search via helper
  const searchResults = searchTopicsByKeyword(trimmed);
  const matchingTopicIds = new Set();
  const matchingLessonIds = new Set();
  const matchingModuleIds = new Set();

  searchResults.forEach(res => {
    matchingTopicIds.add(res.topic.id);
    matchingLessonIds.add(res.lessonId);
    matchingModuleIds.add(res.moduleId);
  });

  // Also check if lesson or module title matches directly
  document.querySelectorAll('.tree-node[data-node-type="lesson"]').forEach(node => {
    const titleEl = node.querySelector(':scope > .node-header > .node-title');
    if (titleEl && titleEl.textContent.toLowerCase().includes(trimmed.toLowerCase())) {
      matchingLessonIds.add(node.getAttribute('data-id'));
      const parentMod = node.closest('.tree-node[data-node-type="module"]');
      if (parentMod) matchingModuleIds.add(parentMod.getAttribute('data-id'));
    }
  });

  document.querySelectorAll('.tree-node[data-node-type="module"]').forEach(node => {
    const titleEl = node.querySelector(':scope > .node-header > .node-title');
    if (titleEl && titleEl.textContent.toLowerCase().includes(trimmed.toLowerCase())) {
      matchingModuleIds.add(node.getAttribute('data-id'));
    }
  });

  const allTopicNodes = document.querySelectorAll('.tree-node[data-node-type="topic"]');
  const allLessonNodes = document.querySelectorAll('.tree-node[data-node-type="lesson"]');
  const allModuleNodes = document.querySelectorAll('.tree-node[data-node-type="module"]');

  // 3. Filter Topics & Highlight Titles
  allTopicNodes.forEach(topicNode => {
    const topicId = topicNode.getAttribute('data-id');
    const titleEl = topicNode.querySelector(':scope > .node-header > .node-title');
    if (matchingTopicIds.has(topicId)) {
      topicNode.classList.remove('is-search-hidden');
      if (titleEl) {
        const text = titleEl.textContent;
        if (regex.test(text)) {
          titleEl.innerHTML = escapeHtml(text).replace(regex, '<mark class="search-highlight">$1</mark>');
        }
      }
    } else {
      topicNode.classList.add('is-search-hidden');
    }
  });

  // 4. Update Lessons
  allLessonNodes.forEach(lessonNode => {
    const lessonId = lessonNode.getAttribute('data-id');
    const hasVisibleTopics = lessonNode.querySelectorAll('.tree-node[data-node-type="topic"]:not(.is-search-hidden)').length > 0;
    const isDirectMatch = matchingLessonIds.has(lessonId);

    if (hasVisibleTopics || isDirectMatch) {
      lessonNode.classList.remove('is-search-hidden');
      lessonNode.classList.add('is-expanded');
      const children = lessonNode.querySelector(':scope > .tree-children');
      const toggle = lessonNode.querySelector(':scope > .node-header > .toggle-icon');
      if (children) children.style.display = 'block';
      if (toggle) toggle.textContent = '▼';

      const titleEl = lessonNode.querySelector(':scope > .node-header > .node-title');
      if (titleEl && isDirectMatch && regex.test(titleEl.textContent)) {
        titleEl.innerHTML = escapeHtml(titleEl.textContent).replace(regex, '<mark class="search-highlight">$1</mark>');
      }
    } else {
      lessonNode.classList.add('is-search-hidden');
    }
  });

  // 5. Update Modules
  allModuleNodes.forEach(moduleNode => {
    const modId = moduleNode.getAttribute('data-id');
    const hasVisibleLessons = moduleNode.querySelectorAll('.tree-node[data-node-type="lesson"]:not(.is-search-hidden)').length > 0;
    const isDirectMatch = matchingModuleIds.has(modId);

    if (hasVisibleLessons || isDirectMatch) {
      moduleNode.classList.remove('is-search-hidden');
      moduleNode.classList.add('is-expanded');
      const children = moduleNode.querySelector(':scope > .tree-children');
      const toggle = moduleNode.querySelector(':scope > .node-header > .toggle-icon');
      if (children) children.style.display = 'block';
      if (toggle) toggle.textContent = '▼';
    } else {
      moduleNode.classList.add('is-search-hidden');
    }
  });

  // 6. Handle Empty / No Results State
  const treeRootEl = document.querySelector('.tree-root');
  let noResEl = document.getElementById('tree-no-results');
  const totalMatches = searchResults.length;

  if (totalMatches === 0 && matchingLessonIds.size === 0 && matchingModuleIds.size === 0) {
    if (treeRootEl) treeRootEl.style.display = 'none';
    if (!noResEl) {
      noResEl = document.createElement('div');
      noResEl.id = 'tree-no-results';
      noResEl.className = 'tree-no-results';
      const container = document.getElementById('tree-container');
      if (container) container.appendChild(noResEl);
    }
    noResEl.innerHTML = `
      <div class="no-results-icon">🔎</div>
      <p>Không tìm thấy nội dung phù hợp với <strong>"${escapeHtml(trimmed)}"</strong></p>
      <button type="button" class="btn-reset-search" id="btn-reset-search">Xóa bộ lọc</button>
    `;
    noResEl.style.display = 'block';
    const resetBtn = document.getElementById('btn-reset-search');
    if (resetBtn) resetBtn.onclick = clearSearchFilter;
  } else {
    if (treeRootEl) treeRootEl.style.display = 'block';
    if (noResEl) noResEl.style.display = 'none';
  }

  // 7. Update Search Count Badge
  updateSearchCountBadge(totalMatches);
}

/**
 * Resets search filter, restores original tree, and removes highlights
 */
function clearSearchFilter() {
  const searchInput = document.getElementById('tree-search-input');
  const clearSearchBtn = document.getElementById('clear-search-btn');
  const countBadge = document.getElementById('search-result-count');
  const treeRootEl = document.querySelector('.tree-root');
  const noResEl = document.getElementById('tree-no-results');

  if (searchInput) {
    searchInput.value = '';
    searchInput.focus();
  }
  if (clearSearchBtn) clearSearchBtn.hidden = true;
  if (countBadge) countBadge.remove();

  if (treeRootEl) treeRootEl.style.display = 'block';
  if (noResEl) noResEl.style.display = 'none';

  // Unhide all nodes
  document.querySelectorAll('.is-search-hidden').forEach(n => n.classList.remove('is-search-hidden'));

  // Remove highlights
  document.querySelectorAll('.search-highlight').forEach(mark => {
    mark.outerHTML = mark.textContent;
  });
}

/**
 * Displays or updates search match counter
 */
function updateSearchCountBadge(count) {
  const toolbar = document.querySelector('.tree-toolbar');
  if (!toolbar) return;

  let badge = document.getElementById('search-result-count');
  if (!badge) {
    badge = document.createElement('div');
    badge.id = 'search-result-count';
    badge.className = 'search-result-count';
    toolbar.appendChild(badge);
  }

  if (count > 0) {
    badge.textContent = `Tìm thấy ${count} chủ đề phù hợp`;
    badge.style.display = 'block';
  } else {
    badge.textContent = 'Không có kết quả trùng khớp';
    badge.style.display = 'block';
  }
}

/**
 * Initializes Copy Code button functionality
 */
function initCopyCodeButtons() {
  document.querySelectorAll('.copy-btn').forEach(btn => {
    btn.onclick = async () => {
      const codeBlock = btn.closest('.code-block');
      const codeElement = codeBlock ? codeBlock.querySelector('code') : null;
      if (!codeElement) return;

      try {
        await navigator.clipboard.writeText(codeElement.innerText);
        const originalText = btn.textContent;
        btn.textContent = 'Copied!';
        btn.style.color = '#10b981';
        setTimeout(() => {
          btn.textContent = originalText;
          btn.style.color = '';
        }, 2000);
      } catch (err) {
        console.error('Failed to copy text: ', err);
      }
    };
  });
}

/**
 * Simple Markdown-like formatter for concept text
 */
function formatMarkdownContent(rawText) {
  if (!rawText) return '';

  let text = escapeHtml(rawText);

  // Markdown tables (| a | b |)
  if (text.includes('|') && text.includes('---')) {
    text = text.replace(/((\|[^\n]+\|\r?\n)+)/g, (tableMatch) => {
      const rows = tableMatch.trim().split(/\r?\n/).filter(r => r.trim());
      if (rows.length < 2) return tableMatch;
      let html = '<div class="data-table-wrapper"><table class="data-table">';
      // Header
      const headerCols = rows[0].split('|').slice(1, -1).map(c => `<th>${c.trim()}</th>`).join('');
      html += `<thead><tr>${headerCols}</tr></thead><tbody>`;
      // Body rows
      for (let i = 1; i < rows.length; i++) {
        if (rows[i].includes('---')) continue;
        const cols = rows[i].split('|').slice(1, -1).map(c => `<td>${c.trim()}</td>`).join('');
        html += `<tr>${cols}</tr>`;
      }
      html += '</tbody></table></div>';
      return html;
    });
  }

  // Inline code: `code`
  text = text.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Bold: **bold**
  text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

  // Split lines for lists and paragraphs
  const lines = text.split(/\r?\n/);
  let inList = false;
  let output = [];

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith('- ')) {
      if (!inList) {
        output.push('<ul class="content-list">');
        inList = true;
      }
      output.push(`<li>${trimmed.substring(2)}</li>`);
    } else {
      if (inList) {
        output.push('</ul>');
        inList = false;
      }
      if (trimmed.startsWith('&gt; ')) {
        output.push(`<blockquote class="content-quote">${trimmed.substring(5)}</blockquote>`);
      } else if (trimmed) {
        if (!trimmed.startsWith('<div class="data-table-wrapper">') && !trimmed.endsWith('</table></div>')) {
          output.push(`<p>${trimmed}</p>`);
        } else {
          output.push(trimmed);
        }
      }
    }
  }
  if (inList) output.push('</ul>');

  return output.join('\n');
}

/**
 * Escapes HTML entities
 */
function escapeHtml(str) {
  if (typeof str !== 'string') return str;
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
