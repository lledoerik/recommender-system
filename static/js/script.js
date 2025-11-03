// Sistema de rating amb estrelles
const stars = document.querySelectorAll('.star');
const ratingValue = document.getElementById('ratingValue');
const ratingInput = document.getElementById('ratingInput');
let currentRating = 0;

stars.forEach((star, index) => {
    // Click per seleccionar rating
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

    // Hover per preview
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

// Gestió del formulari
const form = document.getElementById('recommendForm');
const resultsSection = document.getElementById('resultsSection');
const animeGrid = document.getElementById('animeGrid');
const loadingIndicator = document.getElementById('loadingIndicator');
const resultsCount = document.getElementById('resultsCount');

// URL de la API - dinàmica segons l'entorn
const API_URL = window.location.origin;  // Utilitza el mateix domini

// Emmagatzemar l'última cerca per si cal triar entre múltiples
let lastSearch = null;

form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const animeName = document.getElementById('animeSearch').value;
    const rating = currentRating;

    if (rating === 0) {
        alert('Si us plau, selecciona una valoració!');
        return;
    }

    // Guardar cerca
    lastSearch = { anime: animeName, rating: rating };

    // Mostrar secció de resultats i loading
    resultsSection.classList.remove('hidden');
    loadingIndicator.classList.remove('hidden');
    animeGrid.innerHTML = '';

    // Scroll suau fins als resultats
    resultsSection.scrollIntoView({behavior: 'smooth'});

    try {
        // Crida a l'API de Flask
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
            // Múltiples coincidències - mostrar selector
            const data = await response.json();
            showAnimeSelector(data.matches, data.query);
            loadingIndicator.classList.add('hidden');
            return;
        }

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Error en obtenir recomanacions');
        }

        const data = await response.json();
        displayResults(data.recommendations, animeName, rating);

    } catch (error) {
        console.error('Error:', error);
        loadingIndicator.classList.add('hidden');

        let errorMessage = 'Error en obtenir les recomanacions.';

        if (error.message.includes("No s'ha trobat")) {
            errorMessage = `No s'ha trobat l'anime "${animeName}". Si us plau, prova amb un altre nom.`;
        } else if (error.message.includes('Failed to fetch')) {
            errorMessage = 'No es pot connectar amb el servidor. Assegura\'t que l\'API Flask està en funcionament.';
        } else {
            errorMessage = error.message;
        }

        animeGrid.innerHTML = `<div class="error-message">${errorMessage}</div>`;
    }
});

function showAnimeSelector(matches, query) {
    /**
     * Mostra un selector quan hi ha múltiples coincidències
     */
    animeGrid.innerHTML = '';
    
    const selectorDiv = document.createElement('div');
    selectorDiv.className = 'anime-selector';
    selectorDiv.innerHTML = `
        <h3>S'han trobat ${matches.length} animes amb "${query}"</h3>
        <p>Selecciona l'anime correcte:</p>
        <div class="anime-options">
            ${matches.map((match, index) => `
                <button class="anime-option" data-anime="${escapeHtml(match.name)}" data-index="${index}">
                    <div class="option-title">${escapeHtml(match.name)}</div>
                    ${match.genre ? `<div class="option-genre">Gènere: ${escapeHtml(match.genre)}</div>` : ''}
                </button>
            `).join('')}
        </div>
    `;
    
    animeGrid.appendChild(selectorDiv);
    
    // Afegir event listeners als botons
    document.querySelectorAll('.anime-option').forEach(button => {
        button.addEventListener('click', async () => {
            const selectedAnime = button.dataset.anime;
            
            // Tornar a fer la cerca amb l'anime específic
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
                    throw new Error('Error en obtenir recomanacions');
                }
                
                const data = await response.json();
                displayResults(data.recommendations, selectedAnime, lastSearch.rating);
                
            } catch (error) {
                console.error('Error:', error);
                loadingIndicator.classList.add('hidden');
                animeGrid.innerHTML = `<div class="error-message">Error en obtenir les recomanacions.</div>`;
            }
        });
    });
}

function escapeHtml(unsafe) {
    /**
     * Escapa caràcters HTML per evitar XSS
     */
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function displayResults(recommendations, animeName, rating) {
    loadingIndicator.classList.add('hidden');
    animeGrid.innerHTML = '';

    if (!recommendations || recommendations.length === 0) {
        animeGrid.innerHTML = '<div class="error-message">No s\'han trobat recomanacions.</div>';
        return;
    }

    // Missatge diferent segons la valoració

    let message = '';
    if (rating >= 4) {
        message = `Animes similars a "${animeName}"`;
    } else if (rating <= 2) {
        message = `Alternatives diferents a "${animeName}"`;
    } else {
        message = `Animes recomanats basats en "${animeName}"`;
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

    // Calcular color de correlació
    const correlationPercent = Math.abs(anime.correlation) * 100;
    let correlationColor = '#10b981'; // verd
    if (correlationPercent < 50) {
        correlationColor = '#ef4444'; // vermell
    } else if (correlationPercent < 70) {
        correlationColor = '#f59e0b'; // taronja
    }

    // Text de similitud segons correlació
    let similarityText = 'Similitud';
    if (anime.correlation < 0) {
        similarityText = 'Diferència';
    }

    card.innerHTML = `
        <div class="anime-title">${escapeHtml(anime.title)}</div>
        <div class="anime-info">
            <div class="anime-score">
                ★ ${anime.score}
            </div>
            ${anime.genre ? `<div>Gènere: ${escapeHtml(anime.genre)}</div>` : ''}
            ${anime.year ? `<div>Any: ${anime.year}</div>` : ''}
            ${anime.correlation !== undefined ? 
                `<div style="color: ${correlationColor}; font-weight: 600;">
                    ${similarityText}: ${(Math.abs(anime.correlation) * 100).toFixed(0)}%
                </div>` : ''}
        </div>
    `;

    return card;
}

// ============================================================================
// FUNCIONALITAT DEL FOOTER - Informació del Model
// ============================================================================

async function loadModelInfo() {
    /**
     * Carrega la informació del model actual i l'actualitza al footer
     * Aquesta funció es crida quan la pàgina es carrega
     */
    try {
        const response = await fetch(`${API_URL}/api/model-info`);
        
        if (!response.ok) {
            console.error('No s\'ha pogut obtenir la informació del model');
            return;
        }
        
        const modelInfo = await response.json();
        
        // Actualitzar el footer amb la informació del model
        updateFooter(modelInfo);
        
    } catch (error) {
        console.error('Error carregant informació del model:', error);
        // Si hi ha error, mostrar informació bàsica
        updateFooter({
            version: '?',
            num_animes: '?',
            num_users: '?'
        });
    }
}

function updateFooter(modelInfo) {
    /**
     * Actualitza el contingut del footer amb la informació del model
     * 
     * @param {Object} modelInfo - Objecte amb la informació del model
     */
    const footer = document.getElementById('footer');
    
    if (!footer) return;
    
    // Formatatge de la data si existeix
    let loadedDate = '';
    if (modelInfo.loaded_at) {
        const date = new Date(modelInfo.loaded_at);
        loadedDate = ` | Carregat: ${date.toLocaleDateString('ca-ES')}`;
    }
    
    // Indicador si s'està entrenant
    let trainingBadge = '';
    if (modelInfo.training_in_progress) {
        trainingBadge = ' <span class="training-badge">🔄 Entrenant...</span>';
    }
    
    // Actualitzar HTML del footer
    footer.innerHTML = `
        <div class="footer-content">
            <div class="model-info">
                Model v${modelInfo.version || '?'}${trainingBadge}
            </div>
            <div class="stats-info">
                ${modelInfo.num_animes || '?'} animes | 
                ${modelInfo.num_users || '?'} usuaris${loadedDate}
            </div>
        </div>
    `;
}

// ============================================================================
// AUTOCOMPLETAT (opcional)
// ============================================================================

const animeSearchInput = document.getElementById('animeSearch');
let availableAnimes = [];

async function loadAvailableAnimes() {
    try {
        const response = await fetch(`${API_URL}/api/animes`);
        const data = await response.json();
        return data.animes;
    } catch (error) {
        console.error('Error carregant animes:', error);
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
        // Aquí pots mostrar les suggerències si vols implementar un dropdown
        console.log('Suggerències:', suggestions);
    }
});

// ============================================================================
// INICIALITZACIÓ
// ============================================================================

// Carregar informació del model quan es carrega la pàgina
document.addEventListener('DOMContentLoaded', () => {
    loadModelInfo();
    
    // Actualitzar cada 30 segons per detectar si s'està entrenant
    setInterval(loadModelInfo, 30000);
});
