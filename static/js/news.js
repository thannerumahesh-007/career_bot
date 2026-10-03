/* ======================================================
   CareerBot Corporate & Technology News Client Module
   Dynamic Category Switching, Real-Time Search, Refresh & AI Takeaway
   ====================================================== */

let activeCategory = 'all';

document.addEventListener('DOMContentLoaded', () => {
    const refreshBtn = document.getElementById('refreshNewsBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            loadNews(true);
        });
    }

    // Capture initial category from URL if present (supports ?category= or ?tab=)
    const urlParams = new URLSearchParams(window.location.search);
    const catParam = urlParams.get('category') || urlParams.get('tab');
    if (catParam) {
        activeCategory = catParam;
        document.querySelectorAll('.category-pill-btn').forEach(btn => {
            if (btn.getAttribute('data-category') === catParam) {
                btn.classList.add('btn-primary-custom', 'active');
                btn.classList.remove('btn-outline-custom');
            } else {
                btn.classList.remove('btn-primary-custom', 'active');
                btn.classList.add('btn-outline-custom');
            }
        });
    }
});

function switchNewsCategory(catId) {
    activeCategory = catId;

    // Update Category Pills UI
    document.querySelectorAll('.category-pill-btn').forEach(btn => {
        if (btn.getAttribute('data-category') === catId) {
            btn.classList.add('btn-primary-custom', 'active');
            btn.classList.remove('btn-outline-custom');
        } else {
            btn.classList.remove('btn-primary-custom', 'active');
            btn.classList.add('btn-outline-custom');
        }
    });

    loadNews(false);
}

function handleNewsSearch() {
    loadNews(false);
}

function clearNewsSearch() {
    const searchInput = document.getElementById('newsSearchInput');
    if (searchInput) searchInput.value = '';
    loadNews(false);
}

async function loadNews(forceRefresh = false) {
    const spinner = document.getElementById('newsLoadingSpinner');
    const newsGrid = document.getElementById('newsGrid');
    const alertContainer = document.getElementById('newsAlertContainer');
    const refreshIcon = document.getElementById('refreshIcon');
    const searchInput = document.getElementById('newsSearchInput');
    const query = searchInput ? searchInput.value.trim() : '';

    if (alertContainer) alertContainer.innerHTML = '';
    if (spinner) spinner.classList.remove('d-none');
    if (newsGrid) newsGrid.classList.add('d-none');
    if (refreshIcon && forceRefresh) refreshIcon.classList.add('spin-animation');

    const params = new URLSearchParams();
    if (activeCategory) params.set('category', activeCategory);
    if (query) params.set('q', query);
    if (forceRefresh) params.set('refresh', 'true');

    try {
        const response = await fetch(`/api/news?${params.toString()}`);
        const data = await response.json();

        if (response.ok && data.status === 'ok') {
            renderNewsArticles(data.articles || []);
            updateNewsHeader(data.total || 0, data.category_label || 'Corporate News', query, data.last_updated);
        } else {
            const errType = data.error_type || 'api_error';
            const errMsg = data.message || 'Unable to fetch news at this time.';
            showNewsError(errMsg, errType);
            renderNewsArticles([]);
        }
    } catch (err) {
        console.error('Error fetching corporate news:', err);
        showNewsError('A network error occurred while contacting the news service. Please check your connection.', 'network_error');
        renderNewsArticles([]);
    } finally {
        if (spinner) spinner.classList.add('d-none');
        if (newsGrid) newsGrid.classList.remove('d-none');
        if (refreshIcon) refreshIcon.classList.remove('spin-animation');
        if (window.lucide) lucide.createIcons();
    }
}

function updateNewsHeader(total, categoryLabel, query, lastUpdated) {
    const countBadge = document.getElementById('articleCountBadge');
    if (countBadge) countBadge.innerText = `${total} Articles`;

    const heading = document.getElementById('resultsHeading');
    if (heading) {
        if (query) {
            heading.innerText = `Results for "${query}" in ${categoryLabel}`;
        } else {
            heading.innerText = `${categoryLabel} Headlines`;
        }
    }

    const lastUpdatedText = document.getElementById('lastUpdatedText');
    if (lastUpdatedText && lastUpdated) {
        lastUpdatedText.innerText = `Updated: ${lastUpdated}`;
    }
}

function renderNewsArticles(articles) {
    const newsGrid = document.getElementById('newsGrid');
    if (!newsGrid) return;

    if (!articles || articles.length === 0) {
        newsGrid.innerHTML = `
            <div class="col-12">
                <div class="card card-custom p-5 text-center text-muted">
                    <i data-lucide="newspaper" style="width: 48px; height: 48px;" class="mx-auto mb-3 opacity-50"></i>
                    <h5>No Articles Found</h5>
                    <p class="small mb-3">No current corporate news matched your criteria. Try another search keyword or switch categories.</p>
                    <button class="btn btn-outline-custom btn-sm mx-auto" onclick="clearNewsSearch()">Show All News</button>
                </div>
            </div>
        `;
        if (window.lucide) lucide.createIcons();
        return;
    }

    let html = '';
    articles.forEach((item, index) => {
        const imgBlock = item.image_url ? `
            <div class="news-card-img-wrapper" style="height: 160px; overflow: hidden; background-color: var(--bg-subtle);">
                <img src="${escapeHtml(item.image_url)}" alt="${escapeHtml(item.title)}" 
                     class="w-100 h-100 object-fit-cover" 
                     loading="lazy" 
                     onerror="this.onerror=null; this.closest('.news-card-img-wrapper').style.display='none';">
            </div>
        ` : '';

        html += `
            <div class="col-md-6 col-lg-4 d-flex">
                <div class="card card-custom h-100 w-100 p-0 overflow-hidden d-flex flex-column hover-shadow transition">
                    ${imgBlock}
                    <div class="p-4 d-flex flex-column flex-grow-1">
                        <div class="d-flex justify-content-between align-items-center mb-2 flex-wrap gap-1">
                            <span class="badge bg-primary-light text-primary fw-semibold small">
                                <i data-lucide="building" style="width: 12px; height: 12px;" class="me-1"></i>${escapeHtml(item.source)}
                            </span>
                            <span class="badge bg-subtle text-muted border-color small">
                                <i data-lucide="clock" style="width: 12px; height: 12px;" class="me-1"></i>${escapeHtml(item.published_relative)}
                            </span>
                        </div>

                        <div class="mb-2">
                            <span class="badge bg-subtle text-accent border-color" style="font-size: 0.72rem;">
                                ${escapeHtml(item.category)}
                            </span>
                        </div>

                        <h6 class="fw-bold mb-2 text-main leading-snug">
                            <a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer" class="text-main text-decoration-none hover-primary">
                                ${escapeHtml(item.title)}
                            </a>
                        </h6>

                        <p class="text-muted small line-clamp-3 mb-3 flex-grow-1">
                            ${escapeHtml(item.description)}
                        </p>

                        <div class="ai-takeaway-container mb-3 d-none" id="aiTakeaway_${index + 1}">
                            <div class="p-2.5 bg-subtle rounded-3 border border-color">
                                <small class="text-primary fw-semibold d-flex align-items-center gap-1 mb-1">
                                    <i data-lucide="sparkles" style="width: 13px; height: 13px;"></i> Gemini Executive Takeaway:
                                </small>
                                <p class="small text-main mb-0 takeaway-content" style="font-size: 0.82rem;"></p>
                            </div>
                        </div>

                        <div class="pt-3 border-top border-color d-flex justify-content-between align-items-center mt-auto">
                            <button type="button" 
                                    class="btn btn-sm btn-subtle text-primary ai-summary-btn d-inline-flex align-items-center gap-1"
                                    data-target="aiTakeaway_${index + 1}"
                                    data-title="${escapeHtml(item.title)}"
                                    data-description="${escapeHtml(item.description)}"
                                    onclick="triggerAiSummary(this)"
                                    title="Get AI executive summary for this article">
                                <i data-lucide="sparkles" style="width: 13px; height: 13px;"></i> AI Takeaway
                            </button>

                            <a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer" 
                               class="btn btn-sm btn-primary-custom d-inline-flex align-items-center gap-1">
                                Read Full Article <i data-lucide="external-link" style="width: 13px; height: 13px;"></i>
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    newsGrid.innerHTML = html;
    if (window.lucide) lucide.createIcons();
}

function showNewsError(message, errorType) {
    const alertContainer = document.getElementById('newsAlertContainer');
    if (!alertContainer) return;

    const alertClass = errorType === 'rate_limit' ? 'alert-warning' : 'alert-danger';
    alertContainer.innerHTML = `
        <div class="alert ${alertClass} border-0 shadow-sm d-flex align-items-center justify-content-between p-3 mb-4 rounded-3">
            <div class="d-flex align-items-center gap-2">
                <i data-lucide="alert-triangle" style="width: 20px; height: 20px;" class="flex-shrink-0"></i>
                <div>
                    <strong>News Service Notice:</strong> ${escapeHtml(message)}
                </div>
            </div>
            <button class="btn btn-sm btn-outline-custom ms-3" onclick="loadNews(true)">Try Again</button>
        </div>
    `;
    if (window.lucide) lucide.createIcons();
}

async function triggerAiSummary(btn) {
    const targetId = btn.getAttribute('data-target');
    const title = btn.getAttribute('data-title');
    const description = btn.getAttribute('data-description');
    const container = document.getElementById(targetId);

    if (!container) return;

    // Toggle if already loaded
    if (!container.classList.contains('d-none') && container.querySelector('.takeaway-content').innerText.trim()) {
        container.classList.add('d-none');
        btn.innerHTML = `<i data-lucide="sparkles" style="width: 13px; height: 13px;"></i> AI Takeaway`;
        if (window.lucide) lucide.createIcons();
        return;
    }

    const contentEl = container.querySelector('.takeaway-content');
    contentEl.innerText = 'Analyzing business impact with Gemini AI...';
    container.classList.remove('d-none');
    btn.disabled = true;

    try {
        const response = await fetch('/api/news/ai-summary', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': getCsrfToken()
            },
            body: JSON.stringify({
                title: title,
                description: description
            })
        });

        const data = await response.json();
        if (response.ok && data.status === 'ok') {
            contentEl.innerText = data.summary;
            btn.innerHTML = `<i data-lucide="sparkles" style="width: 13px; height: 13px;"></i> Hide Takeaway`;
        } else {
            contentEl.innerText = `${title}. Key corporate market development reported by industry sources.`;
            btn.innerHTML = `<i data-lucide="sparkles" style="width: 13px; height: 13px;"></i> Hide Takeaway`;
        }
    } catch (e) {
        contentEl.innerText = `${title}. Key corporate development reported by industry sources.`;
    } finally {
        btn.disabled = false;
        if (window.lucide) lucide.createIcons();
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.innerText = String(text);
    return div.innerHTML;
}
