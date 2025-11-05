// Star rating system
const stars = document.querySelectorAll('.star');
const ratingValue = document.getElementById('ratingValue');
const ratingInput = document.getElementById('ratingInput');
let currentRating = 0;

stars.forEach((star, index) => {
    // Click to select rating
    star.addEventListener('click', (e) => {
        const rect = star.getBoundingClientRect();
        const clickX = e.clientX - rect.left;
        const starWidth = rect.width;
        const starNumber = index + 1;

        if (clickX < starWidth / 2) {
            currentRating = starNumber - 0.5;
        } else {
            currentRating = starNumber;
        }

        updateRating(currentRating);
    });

    // Hover for preview
    star.addEventListener('mousemove', (e) => {
        const rect = star.getBoundingClientRect();
        const hoverX = e.clientX - rect.left;
        const starWidth = rect.width;
        const starNumber = index + 1;

        let previewRating;
        if (hoverX < starWidth / 2) {
            previewRating = starNumber - 0.5;
        } else {
            previewRating = starNumber;
        }

        highlightStars(previewRating);
    });
});

document.getElementById('starRating').addEventListener('mouseleave', () => {
    highlightStars(currentRating);
});

function updateRating(rating) {
    currentRating = rating;
    ratingInput.value = rating;
    ratingValue.textContent = `${rating}/5`;
    highlightStars(rating);
}

function highlightStars(rating) {
    stars.forEach((star, index) => {
        const starNumber = index + 1;

        star.classList.remove('full', 'half');

        if (rating >= starNumber) {
            star.classList.add('full');
        } else if (rating >= starNumber - 0.5) {
            star.classList.add('half');
        }
    });
}

// Form handling
const form = document.getElementById('recommendForm');
const resultsSection = document.getElementById('resultsSection');
const animeGrid = document.getElementById('animeGrid');
const loadingIndicator = document.getElementById('loadingIndicator');
const resultsCount = document.getElementById('resultsCount');

// API URL - dynamic based on environment
const API_URL = window.location.origin;

// Store last search for multiple choice handling
let lastSearch = null;

form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const animeName = document.getElementById('animeSearch').value;
    const rating = currentRating;

    if (rating === 0) {
        alert('Please select a rating!');
        return;
    }

    // Save search
    lastSearch = { anime: animeName, rating: rating };

    // Show results section and loading
    resultsSection.classList.remove('hidden');
    loadingIndicator.classList.remove('hidden');
    animeGrid.innerHTML = '';

    // Smooth scroll to results
    resultsSection.scrollIntoView({behavior: 'smooth'});

    try {
        // Call Flask API
        const response = await fetch(`${API_URL}/api/recommendations`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                anime: animeName,
                rating: rating
            })
        });

        if (response.status === 300) {
            // Multiple matches - show selector
            const data = await response.json();
            showAnimeSelector(data.matches, data.query);
            loadingIndicator.classList.add('hidden');
            return;
        }

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Error getting recommendations');
        }

        const data = await response.json();
        displayResults(data.recommendations, data.anime, rating);

    } catch (error) {
        console.error('Error:', error);
        loadingIndicator.classList.add('hidden');

        let errorMessage = 'Error getting recommendations.';

        if (error.message.includes("not found")) {
            errorMessage = `Anime "${animeName}" not found. Please try another name.`;
        } else if (error.message.includes('Failed to fetch')) {
            errorMessage = 'Cannot connect to server. Make sure the Flask API is running.';
        } else {
            errorMessage = error.message;
        }

        animeGrid.innerHTML = `<div class="error-message">${errorMessage}</div>`;
    }
});

function showAnimeSelector(matches, query) {
    /**
     * Show selector when there are multiple matches
     */
    animeGrid.innerHTML = '';
    
    const selectorDiv = document.createElement('div');
    selectorDiv.className = 'anime-selector';
    selectorDiv.innerHTML = `
        <h3>Found ${matches.length} animes with "${query}"</h3>
        <p>Select the correct anime:</p>
        <div class="anime-options">
            ${matches.map((match, index) => `
                <button class="anime-option" data-anime="${escapeHtml(match.name)}" data-index="${index}">
                    <div class="option-title">${escapeHtml(match.name)}</div>
                    ${match.genre ? `<div class="option-genre">Genre: ${escapeHtml(match.genre)}</div>` : ''}
                </button>
            `).join('')}
        </div>
    `;
    
    animeGrid.appendChild(selectorDiv);
    
    // Add event listeners to buttons
    document.querySelectorAll('.anime-option').forEach(button => {
        button.addEventListener('click', async () => {
            const selectedAnime = button.dataset.anime;
            
            // Re-do search with specific anime
            loadingIndicator.classList.remove('hidden');
            animeGrid.innerHTML = '';
            
            try {
                const response = await fetch(`${API_URL}/api/recommendations`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        anime: selectedAnime,
                        rating: lastSearch.rating
                    })
                });
                
                if (!response.ok) {
                    throw new Error('Error getting recommendations');
                }
                
                const data = await response.json();
                displayResults(data.recommendations, data.anime, lastSearch.rating);
                
            } catch (error) {
                console.error('Error:', error);
                loadingIndicator.classList.add('hidden');
                animeGrid.innerHTML = `<div class="error-message">Error getting recommendations.</div>`;
            }
        });
    });
}

function escapeHtml(unsafe) {
    /**
     * Escape HTML characters to prevent XSS
     */
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function displayResults(recommendations, exactAnimeName, rating) {
    loadingIndicator.classList.add('hidden');
    animeGrid.innerHTML = '';

    if (!recommendations || recommendations.length === 0) {
        animeGrid.innerHTML = '<div class="error-message">No recommendations found.</div>';
        return;
    }

    // Different message based on rating
    let message = '';
    if (rating >= 4) {
        message = `Animes similar to "${exactAnimeName}"`;
    } else if (rating <= 2) {
        message = `Different alternatives to "${exactAnimeName}"`;
    } else {
        message = `Recommended animes based on "${exactAnimeName}"`;
    }
    
    resultsCount.textContent = message;

    recommendations.forEach(anime => {
        const card = createAnimeCard(anime);
        animeGrid.appendChild(card);
    });
}

function createAnimeCard(anime) {
    const card = document.createElement('div');
    card.className = 'anime-card';

    // Calculate correlation color
    const correlationPercent = Math.abs(anime.correlation) * 100;
    let correlationColor = '#10b981'; // green
    if (correlationPercent < 50) {
        correlationColor = '#ef4444'; // red
    } else if (correlationPercent < 70) {
        correlationColor = '#f59e0b'; // orange
    }

    // Similarity text based on correlation
    let similarityText = 'Similarity';
    if (anime.correlation < 0) {
        similarityText = 'Difference';
    }

    card.innerHTML = `
        <div class="anime-title">${escapeHtml(anime.title)}</div>
        <div class="anime-info">
            <div class="anime-score">
                ★ ${anime.score}
            </div>
            ${anime.genre ? `<div>Genre: ${escapeHtml(anime.genre)}</div>` : ''}
            ${anime.year ? `<div>Year: ${anime.year}</div>` : ''}
            ${anime.correlation !== undefined ? 
                `<div style="color: ${correlationColor}; font-weight: 600;">
                    ${similarityText}: ${(Math.abs(anime.correlation) * 100).toFixed(0)}%
                </div>` : ''}
        </div>
    `;

    return card;
}

// ============================================================================
// FOOTER FUNCTIONALITY - Model Information
// ============================================================================

async function loadModelInfo() {
    /**
     * Load current model information and update footer
     * This function is called when the page loads
     */
    try {
        const response = await fetch(`${API_URL}/api/model-info`);
        
        if (!response.ok) {
            console.error('Could not get model information');
            return;
        }
        
        const modelInfo = await response.json();
        
        // Update footer with model information
        updateFooter(modelInfo);
        
    } catch (error) {
        console.error('Error loading model info:', error);
        // If error, show basic information
        updateFooter({
            version: '?',
            num_animes: '?',
            num_users: '?'
        });
    }
}

function updateFooter(modelInfo) {
    /**
     * Update footer content with model information
     * 
     * @param {Object} modelInfo - Object with model information
     */
    const footer = document.getElementById('footer');
    
    if (!footer) return;
    
    // Format date if it exists
    let loadedDate = '';
    if (modelInfo.loaded_at) {
        const date = new Date(modelInfo.loaded_at);
        loadedDate = ` | Loaded: ${date.toLocaleDateString('en-US')}`;
    }
    
    // Indicator if training
    let trainingBadge = '';
    if (modelInfo.training_in_progress) {
        trainingBadge = ' <span class="training-badge">Training...</span>';
    }
    
    // Update footer HTML
    footer.innerHTML = `
        <div class="footer-content">
            <div class="model-info">
                Model v${modelInfo.version || '?'}${trainingBadge}
            </div>
            <div class="stats-info">
                ${modelInfo.num_animes || '?'} animes | 
                ${modelInfo.num_users || '?'} users${loadedDate}
            </div>
        </div>
    `;
}

// ============================================================================
// AUTOCOMPLETE (optional)
// ============================================================================

const animeSearchInput = document.getElementById('animeSearch');
let availableAnimes = [];

async function loadAvailableAnimes() {
    try {
        const response = await fetch(`${API_URL}/api/animes`);
        const data = await response.json();
        return data.animes;
    } catch (error) {
        console.error('Error loading animes:', error);
        return [];
    }
}

loadAvailableAnimes().then(animes => {
    availableAnimes = animes;
});

animeSearchInput.addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase();
    if (query.length > 2) {
        const suggestions = availableAnimes.filter(anime =>
            anime.name.toLowerCase().includes(query)
        ).slice(0, 5);
        // Here you can show suggestions if you want to implement a dropdown
        console.log('Suggestions:', suggestions);
    }
});

// ============================================================================
// INITIALIZATION
// ============================================================================

// Load model info when page loads
document.addEventListener('DOMContentLoaded', () => {
    loadModelInfo();
    
    // Update every 30 seconds to detect if training
    setInterval(loadModelInfo, 30000);
});
