// API URL - dynamic based on environment
const API_URL = window.location.origin;

// State management
let currentState = {
    mediaId: null,
    offset: 0,
    limit: 6,
    total: 0,
    isLoading: false,
    source: null
};

// DOM Elements
const form = document.getElementById('recommendForm');
const resultsSection = document.getElementById('resultsSection');
const mediaGrid = document.getElementById('mediaGrid');
const loadingIndicator = document.getElementById('loadingIndicator');
const resultsCount = document.getElementById('resultsCount');
const mediaSearchInput = document.getElementById('mediaSearch');

// Modal Elements
const modalOverlay = document.getElementById('modalOverlay');
const modalTitle = document.getElementById('modalTitle');
const modalSubtitle = document.getElementById('modalSubtitle');
const modalContent = document.getElementById('modalContent');
const modalClose = document.getElementById('modalClose');

// Oracle phrases for loading states
const oraclePhrases = [
    "L'oracle contempla els astres...",
    "Les visions es formen en la boira...",
    "Pitia entra en trànsit...",
    "Els vapors d'Apol·lo revelen secrets...",
    "L'esperit de Delfos desperta...",
    "Les ombres del futur s'aclareixen..."
];

function getRandomPhrase() {
    return oraclePhrases[Math.floor(Math.random() * oraclePhrases.length)];
}

// Modal functions
function openModal(title, subtitle) {
    modalTitle.textContent = title;
    modalSubtitle.textContent = subtitle;
    modalOverlay.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    modalOverlay.classList.add('hidden');
    document.body.style.overflow = '';
}

// Close modal on button click
modalClose.addEventListener('click', closeModal);

// Close modal on overlay click
modalOverlay.addEventListener('click', (e) => {
    if (e.target === modalOverlay) {
        closeModal();
    }
});

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !modalOverlay.classList.contains('hidden')) {
        closeModal();
    }
});

// Form submission
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const title = mediaSearchInput.value.trim();
    if (!title) return;

    // Reset state
    currentState = {
        mediaId: null,
        offset: 0,
        limit: 6,
        total: 0,
        isLoading: false,
        source: null
    };

    // Show loading
    resultsSection.classList.remove('hidden');
    showLoading();
    mediaGrid.innerHTML = '';
    resultsSection.scrollIntoView({ behavior: 'smooth' });

    try {
        const response = await fetch(`${API_URL}/api/recommendations`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, limit: currentState.limit, offset: 0 })
        });

        if (response.status === 300) {
            // Multiple matches - show modal selector
            const data = await response.json();
            hideLoading();
            resultsSection.classList.add('hidden');
            showMediaSelector(data.matches, data.query);
            return;
        }

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'L\'oracle no pot respondre en aquest moment');
        }

        const data = await response.json();
        currentState.mediaId = data.source.id;
        currentState.source = data.source;
        currentState.total = data.pagination.total;
        currentState.offset = data.pagination.limit;

        displayResults(data.recommendations, data.source, data.pagination);

    } catch (error) {
        console.error('Error:', error);
        hideLoading();
        mediaGrid.innerHTML = `<div class="error-message">${escapeHtml(error.message)}</div>`;
    }
});

function showLoading() {
    loadingIndicator.classList.remove('hidden');
    loadingIndicator.querySelector('p').textContent = getRandomPhrase();
}

function hideLoading() {
    loadingIndicator.classList.add('hidden');
}

function showMediaSelector(matches, query) {
    // Open modal with options
    openModal(
        `Quina visió de "${query}" cerques?`,
        `L'oracle ha trobat ${matches.length} visions. Selecciona'n una:`
    );

    // Generate modal content
    modalContent.innerHTML = `
        <div class="modal-grid">
            ${matches.map((match) => `
                <button type="button" class="modal-option" data-id="${escapeHtml(match.id)}">
                    ${match.poster_url
                        ? `<img src="${match.poster_url}" alt="${escapeHtml(match.title)}" class="modal-option-poster" loading="lazy">`
                        : `<div class="modal-option-no-poster">🎬</div>`
                    }
                    <div class="modal-option-content">
                        <div class="modal-option-title">${escapeHtml(match.title)}</div>
                        <div class="modal-option-meta">
                            <span class="source-badge ${match.source}">${formatSource(match.source)}</span>
                            ${match.year ? `<span class="year-badge">${match.year}</span>` : ''}
                        </div>
                        ${match.genre ? `<div class="modal-option-genre">${escapeHtml(match.genre)}</div>` : ''}
                    </div>
                </button>
            `).join('')}
        </div>
    `;

    // Add click handlers to modal options
    modalContent.querySelectorAll('.modal-option').forEach(button => {
        button.addEventListener('click', async () => {
            const mediaId = button.dataset.id;

            // Close modal and show loading
            closeModal();

            // Reset state
            currentState = {
                mediaId: mediaId,
                offset: 0,
                limit: 6,
                total: 0,
                isLoading: false,
                source: null
            };

            resultsSection.classList.remove('hidden');
            showLoading();
            mediaGrid.innerHTML = '';
            resultsSection.scrollIntoView({ behavior: 'smooth' });

            try {
                const response = await fetch(`${API_URL}/api/recommendations`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ media_id: mediaId, limit: currentState.limit, offset: 0 })
                });

                if (!response.ok) throw new Error('L\'oracle no pot respondre en aquest moment');

                const data = await response.json();
                currentState.source = data.source;
                currentState.total = data.pagination.total;
                currentState.offset = data.pagination.limit;

                displayResults(data.recommendations, data.source, data.pagination);
            } catch (error) {
                hideLoading();
                mediaGrid.innerHTML = `<div class="error-message">${escapeHtml(error.message)}</div>`;
            }
        });
    });
}

function displayResults(recommendations, source, pagination) {
    hideLoading();

    if (!recommendations || recommendations.length === 0) {
        mediaGrid.innerHTML = '<div class="error-message">L\'oracle no ha tingut cap visió.</div>';
        return;
    }

    resultsCount.innerHTML = `Visions relacionades amb "<strong>${escapeHtml(source.title)}</strong>" (${formatSource(source.source_type)})`;

    // Add cards with staggered animation
    recommendations.forEach((media, index) => {
        const card = createMediaCard(media, index);
        mediaGrid.appendChild(card);
    });

    // Add or update "Load more" button
    updateLoadMoreButton(pagination);
}

function appendResults(recommendations, pagination) {
    hideLoading();

    // Remove existing load more button before adding new cards
    const existingBtn = document.querySelector('.load-more-container');
    if (existingBtn) existingBtn.remove();

    const startIndex = document.querySelectorAll('.media-card').length;

    // Add new cards with staggered animation
    recommendations.forEach((media, index) => {
        const card = createMediaCard(media, index);
        mediaGrid.appendChild(card);
    });

    // Add or update "Load more" button
    updateLoadMoreButton(pagination);
}

function updateLoadMoreButton(pagination) {
    // Remove existing button
    const existingBtn = document.querySelector('.load-more-container');
    if (existingBtn) existingBtn.remove();

    if (pagination.has_more) {
        const remaining = pagination.total - (pagination.offset + pagination.limit);
        const container = document.createElement('div');
        container.className = 'load-more-container';
        container.innerHTML = `
            <button type="button" class="btn load-more-btn" id="loadMoreBtn">
                <span class="btn-text">Revelar més visions</span>
                <span class="btn-count">${Math.min(remaining, currentState.limit)} més disponibles</span>
            </button>
            <div class="vision-progress">
                <div class="vision-progress-bar" style="width: ${Math.round(((pagination.offset + pagination.limit) / pagination.total) * 100)}%"></div>
            </div>
            <span class="vision-count">${pagination.offset + pagination.limit} de ${pagination.total} visions revelades</span>
        `;
        mediaGrid.appendChild(container);

        // Add click handler
        document.getElementById('loadMoreBtn').addEventListener('click', loadMore);
    } else if (pagination.total > 0) {
        // All loaded message
        const container = document.createElement('div');
        container.className = 'load-more-container all-revealed';
        container.innerHTML = `
            <div class="oracle-complete">
                <span class="oracle-icon">✨</span>
                <span>L'oracle ha revelat totes les seves visions</span>
            </div>
        `;
        mediaGrid.appendChild(container);
    }
}

async function loadMore() {
    if (currentState.isLoading || !currentState.mediaId) return;

    currentState.isLoading = true;
    const btn = document.getElementById('loadMoreBtn');
    btn.disabled = true;
    btn.querySelector('.btn-text').textContent = getRandomPhrase();
    btn.classList.add('loading');

    try {
        const response = await fetch(`${API_URL}/api/recommendations`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                media_id: currentState.mediaId,
                limit: currentState.limit,
                offset: currentState.offset
            })
        });

        if (!response.ok) throw new Error('L\'oracle no pot respondre');

        const data = await response.json();
        currentState.offset += data.recommendations.length;
        currentState.total = data.pagination.total;

        appendResults(data.recommendations, data.pagination);

    } catch (error) {
        console.error('Error loading more:', error);
        btn.querySelector('.btn-text').textContent = 'Error - Torna-ho a provar';
        btn.disabled = false;
        btn.classList.remove('loading');
    } finally {
        currentState.isLoading = false;
    }
}

function createMediaCard(media, index = 0) {
    const card = document.createElement('div');
    card.className = 'media-card';
    card.style.setProperty('--animation-delay', `${index * 0.1}s`);

    // Calculate similarity percentage for visual display
    const similarityPercent = media.similarity ? Math.round(media.similarity * 100) : null;

    card.innerHTML = `
        ${media.poster_url ? `
            <div class="poster-container">
                <img class="media-poster" src="${media.poster_url}" alt="${escapeHtml(media.title)}" loading="lazy">
                ${similarityPercent ? `<div class="similarity-badge">${similarityPercent}%</div>` : ''}
            </div>
        ` : `<div class="media-poster-placeholder">${similarityPercent ? `<div class="similarity-badge">${similarityPercent}%</div>` : ''}</div>`}
        <div class="media-content">
            <div class="media-title">${escapeHtml(media.title)}</div>
            <div class="media-meta">
                <span class="source-badge ${media.source}">${formatSource(media.source)}</span>
                ${media.year ? `<span class="year-badge">${media.year}</span>` : ''}
            </div>
            ${media.score || media.genre ? `
                <div class="media-info">
                    ${media.score ? `<div class="media-score">${media.score}</div>` : ''}
                    ${media.genre ? `<div class="media-genre">${escapeHtml(media.genre)}</div>` : ''}
                </div>
            ` : ''}
        </div>
    `;

    return card;
}

function formatSource(source) {
    const labels = {
        'tmdb_movie': 'Pel·lícula',
        'tmdb_tv': 'Sèrie',
        'anilist': 'Anime'
    };
    return labels[source] || source;
}

function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return String(unsafe)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Load system info on page load
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch(`${API_URL}/api/system-info`);
        if (response.ok) {
            const info = await response.json();
            console.log('System info:', info);
        }
    } catch (error) {
        console.error('Could not load system info:', error);
    }
});
