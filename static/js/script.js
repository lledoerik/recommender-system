// API URL - dynamic based on environment
const API_URL = window.location.origin;

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

    // Show loading
    resultsSection.classList.remove('hidden');
    loadingIndicator.classList.remove('hidden');
    mediaGrid.innerHTML = '';
    resultsSection.scrollIntoView({ behavior: 'smooth' });

    try {
        const response = await fetch(`${API_URL}/api/recommendations`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title })
        });

        if (response.status === 300) {
            // Multiple matches - show modal selector
            const data = await response.json();
            loadingIndicator.classList.add('hidden');
            resultsSection.classList.add('hidden');
            showMediaSelector(data.matches, data.query);
            return;
        }

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'L\'oracle no pot respondre en aquest moment');
        }

        const data = await response.json();
        displayResults(data.recommendations, data.source);

    } catch (error) {
        console.error('Error:', error);
        loadingIndicator.classList.add('hidden');
        mediaGrid.innerHTML = `<div class="error-message">${escapeHtml(error.message)}</div>`;
    }
});

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
            resultsSection.classList.remove('hidden');
            loadingIndicator.classList.remove('hidden');
            mediaGrid.innerHTML = '';
            resultsSection.scrollIntoView({ behavior: 'smooth' });

            try {
                const response = await fetch(`${API_URL}/api/recommendations`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ media_id: mediaId })
                });

                if (!response.ok) throw new Error('L\'oracle no pot respondre en aquest moment');

                const data = await response.json();
                displayResults(data.recommendations, data.source);
            } catch (error) {
                loadingIndicator.classList.add('hidden');
                mediaGrid.innerHTML = `<div class="error-message">${escapeHtml(error.message)}</div>`;
            }
        });
    });
}

function displayResults(recommendations, source) {
    loadingIndicator.classList.add('hidden');
    mediaGrid.innerHTML = '';

    if (!recommendations || recommendations.length === 0) {
        mediaGrid.innerHTML = '<div class="error-message">L\'oracle no ha tingut cap visió.</div>';
        return;
    }

    resultsCount.textContent = `Visions relacionades amb "${source.title}" (${formatSource(source.source_type)})`;

    recommendations.forEach(media => {
        const card = createMediaCard(media);
        mediaGrid.appendChild(card);
    });
}

function createMediaCard(media) {
    const card = document.createElement('div');
    card.className = 'media-card';

    card.innerHTML = `
        ${media.poster_url ? `
            <img class="media-poster" src="${media.poster_url}" alt="${escapeHtml(media.title)}" loading="lazy">
        ` : '<div class="media-poster-placeholder"></div>'}
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
