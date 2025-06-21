// Global variable to track if we're handling a project change
let isHandlingProjectChange = false;

// Initialize session view if we're on a session page
function initializeSessionView() {
    // Add any session-specific initialization code here
    console.log('Initializing session view');
    
    // Example: Initialize any session-specific UI components
    const sessionContent = document.querySelector('.session-content');
    if (sessionContent) {
        // Add any session-specific UI initialization here
    }
}

// Make handleProjectChange globally available
window.handleProjectChange = async function(event) {
    // Prevent default form submission and propagation
    event.preventDefault();
    event.stopPropagation();
    
    // Prevent multiple simultaneous requests
    if (isHandlingProjectChange) return;
    isHandlingProjectChange = true;
    
    const selectedProjectId = event.target.value;
    const url = selectedProjectId ? `/?project_id=${selectedProjectId}` : '/';
    
    try {
        // Show loading state
        const sessionHistoryList = document.getElementById('session-history-list');
        if (sessionHistoryList) {
            sessionHistoryList.innerHTML = '<p>Loading sessions...</p>';
        }
        
        // Fetch the updated content
        const response = await fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'text/html'
            },
            credentials: 'same-origin'
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Error loading project sessions:', errorText);
            throw new Error(`Failed to load project sessions: ${response.status}`);
        }
        
        const html = await response.text();
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;
        
        // Extract and update the session history
        const newSessionList = tempDiv.querySelector('#session-history-list');
        if (sessionHistoryList) {
            if (newSessionList) {
                sessionHistoryList.innerHTML = newSessionList.innerHTML;
            } else {
                sessionHistoryList.innerHTML = '<p>No sessions found for this project.</p>';
            }
        }
        
        // Update the project name in the sidebar if available
        const projectNameElement = tempDiv.querySelector('.history-sidebar p strong');
        const currentProjectNameElement = document.querySelector('.history-sidebar p strong');
        if (projectNameElement && currentProjectNameElement) {
            currentProjectNameElement.textContent = projectNameElement.textContent;
        }
        
        // Update the URL without reloading the page
        window.history.pushState({ projectId: selectedProjectId }, '', url);
        
    } catch (error) {
        console.error('Error loading project sessions:', error);
        const sessionHistoryList = document.getElementById('session-history-list');
        if (sessionHistoryList) {
            sessionHistoryList.innerHTML = `
                <p>Error loading sessions: ${error.message}</p>
                <button onclick="window.location.reload()" class="button">Refresh Page</button>
            `;
        }
    } finally {
        isHandlingProjectChange = false;
    }
};

// Function to save main content to sessionStorage
function saveMainContent() {
    const resultsArea = document.getElementById('results-area');
    if (resultsArea && resultsArea.innerHTML.trim()) {
        sessionStorage.setItem('mainContent', resultsArea.innerHTML);
        sessionStorage.setItem('mainContentTimestamp', Date.now());
    }
}

// Function to restore main content from sessionStorage
function restoreMainContent() {
    const resultsArea = document.getElementById('results-area');
    const savedContent = sessionStorage.getItem('mainContent');
    const savedTime = sessionStorage.getItem('mainContentTimestamp');
    
    // Only restore if content was saved within the last hour (3600000 ms)
    if (resultsArea && savedContent && savedTime && (Date.now() - parseInt(savedTime) < 3600000)) {
        resultsArea.innerHTML = savedContent;
        resultsArea.style.display = 'block';
        return true;
    }
    return false;
}

// Clear saved content when needed
function clearSavedMainContent() {
    sessionStorage.removeItem('mainContent');
    sessionStorage.removeItem('mainContentTimestamp');
}

// Initialize event listeners when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Make sure the project selector has the event listener
    const projectSelect = document.getElementById('project_id');
    if (projectSelect) {
        projectSelect.addEventListener('change', handleProjectChange);
    }
    
    // Handle form submission
    const form = document.getElementById('alchemist-form');
    if (form) {
        form.addEventListener('submit', handleFormSubmit);
    }
    
    // Delegate click events for dynamically loaded content
    document.addEventListener('click', async function(event) {
        // Handle delete button clicks - use event delegation for dynamically loaded content
        if (event.target.matches('.delete-btn, .delete-btn *')) {
            const deleteBtn = event.target.closest('.delete-btn');
            if (deleteBtn) {
                event.preventDefault();
                event.stopPropagation();
                handleDeleteClick(event);
                return false;
            }
        }
        
        // Handle session loading with client-side navigation
        const sessionLink = event.target.closest('.session-link');
        if (sessionLink) {
            event.preventDefault();
            event.stopPropagation();
            
            const sessionUrl = sessionLink.getAttribute('href');
            const sessionId = sessionUrl.split('/').pop();
            
            // Save current main content before navigating
            saveMainContent();
            
            // Get DOM elements
            const resultsArea = document.getElementById('results-area');
            const loadingSpinner = document.getElementById('loading-spinner');
            const mainContent = document.querySelector('main');
            const sessionHistoryList = document.getElementById('session-history-list');
            
            // Update UI states
            if (loadingSpinner) loadingSpinner.style.display = 'block';
            if (mainContent) mainContent.style.display = 'none';
            if (sessionHistoryList) sessionHistoryList.style.display = 'none';
            
            try {
                // Load session content via AJAX
                const response = await fetch(sessionUrl, {
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'Accept': 'text/html'
                    },
                    credentials: 'same-origin'
                });
                
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                
                const html = await response.text();
                
                // Create a temporary container to parse the HTML
                const tempContainer = document.createElement('div');
                tempContainer.innerHTML = html;
                
                // Find the session content in the response
                const sessionContent = tempContainer.querySelector('.session-content');
                
                if (sessionContent && resultsArea) {
                    // Update the URL without reloading the page
                    window.history.pushState({ 
                        sessionId: sessionId, 
                        isSession: true,
                        handled: true  // Mark this state as handled by us
                    }, '', sessionUrl);
                    
                    // Update the results area with the session content
                    resultsArea.innerHTML = '';
                    resultsArea.appendChild(sessionContent);
                    resultsArea.style.display = 'block';
                    
                    // Show the main content
                    if (mainContent) mainContent.style.display = 'block';
                    
                    // Re-initialize any necessary JavaScript for the session view
                    if (typeof initializeSessionView === 'function') {
                        initializeSessionView();
                    }
                    
                    // Scroll to top
                    window.scrollTo(0, 0);
                } else {
                    console.error('Could not find session content in response');
                    // Fall back to full page load if we can't find the content
                    window.location.href = sessionUrl;
                }
            } catch (error) {
                console.error('Error loading session:', error);
                // Fall back to normal navigation if AJAX fails
                window.location.href = sessionUrl;
            } finally {
                if (loadingSpinner) loadingSpinner.style.display = 'none';
            }
            
            return false;
        }
    });
    
    // Handle popstate (back/forward navigation)
    // Single popstate handler for all navigation
    window.addEventListener('popstate', async function(event) {
        // Prevent default behavior that might cause a page reload
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }
        
        const url = new URL(window.location.href);
        const isSessionPage = url.pathname.startsWith('/session/');
        const isMainPage = url.pathname === '/' || url.pathname === '';
        
        try {
            // Show loading state
            const loadingSpinner = document.getElementById('loading-spinner');
            const mainContent = document.querySelector('main');
            const resultsArea = document.getElementById('results-area');
            const sessionHistoryList = document.getElementById('session-history-list');
            
            if (loadingSpinner) loadingSpinner.style.display = 'block';
            
            // If this is a popstate from our own navigation, handle it
            if (event.state && event.state.handled) {
                return;
            }
            
            // If we're on a session page, load it via AJAX
            if (isSessionPage) {
                // Save current main content before navigating to session
                saveMainContent();
                
                const response = await fetch(url.pathname, {
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'Accept': 'text/html'
                    },
                    credentials: 'same-origin'
                });
                
                if (!response.ok) throw new Error('Failed to load session');
                
                const html = await response.text();
                if (mainContent) {
                    mainContent.innerHTML = html;
                    // Hide session history list when viewing a session
                    if (sessionHistoryList) sessionHistoryList.style.display = 'none';
                    // Show the main content
                    mainContent.style.display = 'block';
                    // Re-initialize any session-specific JavaScript
                    if (typeof initializeSessionView === 'function') {
                        initializeSessionView();
                    }
                }
            } 
            // If we're on the main page, show the session list and restore content
            else if (isMainPage) {
                const projectId = url.searchParams.get('project_id');
                
                // Show the main content and session history
                if (mainContent) mainContent.style.display = 'block';
                if (sessionHistoryList) sessionHistoryList.style.display = 'block';
                
                // Always try to restore saved content first
                const contentRestored = restoreMainContent();
                
                // If no content was restored, load the session history
                if (!contentRestored) {
                    await reloadSessionHistory(projectId);
                }
                
                // Make sure results area is visible
                if (resultsArea) {
                    resultsArea.style.display = 'block';
                }
                
                window.scrollTo(0, 0);
            }
            
        } catch (error) {
            console.error('Error during navigation:', error);
            // Fall back to full page reload if something goes wrong
            window.location.reload();
        } finally {
            const loadingSpinner = document.getElementById('loading-spinner');
            if (loadingSpinner) loadingSpinner.style.display = 'none';
        }
    });
});

async function handleFormSubmit(event) {
    // Prevent default form submission
    event.preventDefault();
    event.stopPropagation();
    
    const userInput = document.getElementById('user_input');
    const projectSelect = document.getElementById('project_id');
    const projectId = projectSelect ? projectSelect.value : null;
    const loadingSpinner = document.getElementById('loading-spinner');
    const resultsArea = document.getElementById('results-area');
    const mainContent = document.querySelector('main');
    const sessionHistoryList = document.getElementById('session-history-list');
    
    if (!userInput || !userInput.value.trim()) {
        alert('Please enter some text to alchemize!');
        return false;
    }
    
    try {
        // Show loading state and update UI
        if (loadingSpinner) loadingSpinner.style.display = 'block';
        if (resultsArea) resultsArea.style.display = 'none';
        if (mainContent) mainContent.style.display = 'none';
        if (sessionHistoryList) sessionHistoryList.style.display = 'block';
        
        // Clear any saved content when submitting a new query
        clearSavedMainContent();
        
        const formData = {
            user_input: userInput.value.trim()
        };
        
        // Only add project_id if it exists and is not empty
        if (projectId) {
            formData.project_id = projectId;
        }
        
        const response = await fetch('/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json'
            },
            body: JSON.stringify(formData),
            credentials: 'same-origin'
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Form submission error:', errorText);
            throw new Error(`Server responded with status ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Form submission successful:', data);
        
        // Update the UI with the response
        if (data && typeof updateUIWithResponse === 'function') {
            await updateUIWithResponse(data);
        }
        
        // Clear the input field
        if (userInput) userInput.value = '';
        
        // Show the main content and results
        if (mainContent) mainContent.style.display = 'block';
        if (resultsArea) resultsArea.style.display = 'block';
        
        // Reload session history to show the new session
        if (projectId) {
            await reloadSessionHistory(projectId);
        } else {
            await reloadSessionHistory();
        }
        
        // Update URL without page reload
        const newUrl = `/?project_id=${projectId || ''}`;
        window.history.pushState({ path: newUrl }, '', newUrl);
        
        return true;
        
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred. Please try again.');
    } finally {
        if (loadingSpinner) loadingSpinner.style.display = 'none';
    }
}

function updateUIWithResponse(data) {
    const resultsArea = document.getElementById('results-area');
    const keyTermsDisplay = document.getElementById('key-terms-display');
    const promptsList = document.getElementById('prompts-list');
    const conceptualGraphDiv = document.getElementById('conceptual-graph');
    
    if (!resultsArea || !keyTermsDisplay || !promptsList || !conceptualGraphDiv) return;
    
    // Update key terms
    keyTermsDisplay.textContent = data.key_terms.join(', ');
    
    // Update prompts
    promptsList.innerHTML = '';
    data.prompts.forEach(prompt => {
        const li = document.createElement('li');
        li.textContent = prompt;
        promptsList.appendChild(li);
    });
    
    // Update graph if data is available
    if (data.graph_data) {
        // Clear previous graph if it exists
        if (window.conceptualGraph) {
            window.conceptualGraph.destroy();
        }
        
        // Create new graph
        const container = document.getElementById('conceptual-graph');
        const options = {
            nodes: {
                shape: 'box',
                margin: 10,
                font: {
                    size: 14,
                    color: '#333'
                },
                borderWidth: 1,
                color: {
                    border: '#7a82ab',
                    background: '#e0e6f6',
                    highlight: {
                        border: '#5c678a',
                        background: '#d1d7ed'
                    }
                }
            },
            edges: {
                width: 2,
                color: '#7a82ab',
                smooth: {
                    type: 'cubicBezier',
                    forceDirection: 'horizontal'
                }
            },
            physics: {
                enabled: true,
                hierarchical: {
                    direction: 'LR',
                    sortMethod: 'directed'
                }
            },
            layout: {
                improvedLayout: true
            }
        };
        
        window.conceptualGraph = new vis.Network(container, data.graph_data, options);
    }
    
    // Show results area
    resultsArea.style.display = 'block';
    resultsArea.scrollIntoView({ behavior: 'smooth' });
}

async function reloadSessionHistory(projectId) {
    const url = projectId ? `/?project_id=${projectId}` : '/';
    
    try {
        const response = await fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        if (!response.ok) throw new Error('Failed to reload session history');
        
        const html = await response.text();
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;
        
        const newSessionList = tempDiv.querySelector('#session-history-list');
        const currentSessionList = document.getElementById('session-history-list');
        
        if (newSessionList && currentSessionList) {
            currentSessionList.innerHTML = newSessionList.innerHTML;
        }
    } catch (error) {
        console.error('Error reloading session history:', error);
    }
}





async function handleDeleteClick(event) {
    event.preventDefault();
    event.stopPropagation();
    
    const button = event.target.closest('.delete-btn');
    if (!button) return false;
    
    const sessionId = button.getAttribute('data-session-id');
    if (!sessionId) return false;
    
    if (!confirm('Are you sure you want to delete this session? This action cannot be undone.')) {
        return false;
    }
    
    try {
        const response = await fetch(`/session/${sessionId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin'
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error('Delete error response:', errorText);
            throw new Error(`Server responded with status ${response.status}`);
        }

        const result = await response.json();
        console.log('Delete successful:', result);
        
        // Remove the session item from the UI
        const sessionItem = document.getElementById(`session-${sessionId}`);
        if (sessionItem) {
            // Add fade out animation
            sessionItem.style.transition = 'opacity 0.3s';
            sessionItem.style.opacity = '0';
            
            // Remove after animation completes
            setTimeout(() => {
                sessionItem.remove();
                
                // If there are no more sessions, show a message
                const sessionList = document.getElementById('session-history-list');
                if (sessionList) {
                    const sessionItems = sessionList.querySelectorAll('.session-item');
                    if (sessionItems.length === 0) {
                        sessionList.innerHTML = '<p>No past sessions yet for this project. Start Alchemizing!</p>';
                    }
                }
            }, 300);
        }
        
        return true;
    } catch (error) {
        console.error('Error deleting session:', error);
        alert(`Error deleting session: ${error.message}`);
        return false;
    }
}

// Remove the duplicate popstate handler to prevent conflicts
