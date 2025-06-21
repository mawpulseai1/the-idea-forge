// Global variable to store the network instance
let network = null;

// Function to render the graph
function renderGraph(graphData) {
    const container = document.getElementById('conceptual-graph');
    if (!container) return;
    
    // Clear previous network if it exists
    if (network !== null) {
        network.destroy();
        container.innerHTML = '';
    }
    
    const nodes = new vis.DataSet(graphData.nodes);
    const edges = new vis.DataSet(graphData.edges);
    const data = { nodes, edges };
    
    const options = {
        nodes: { 
            borderWidth: 2, 
            size: 20, 
            font: { face: 'Segoe UI' },
            color: {
                border: '#2B7CE9',
                background: '#97C2FC',
                highlight: {
                    border: '#2B7CE9',
                    background: '#D2E5FF'
                }
            }
        },
        edges: { 
            smooth: { type: 'continuous' },
            color: {
                color: '#848484',
                highlight: '#2B7CE9',
                hover: '#2B7CE9'
            }
        },
        physics: { 
            stabilization: false, 
            barnesHut: { 
                gravitationalConstant: -2000, 
                centralGravity: 0.3, 
                springLength: 95, 
                springConstant: 0.04, 
                damping: 0.09, 
                avoidOverlap: 0.1 
            } 
        },
        interaction: { 
            hover: true, 
            navigationButtons: true, 
            zoomView: true,
            tooltipDelay: 200,
            hideEdgesOnDrag: true
        },
        manipulation: { enabled: false }
    };
    
    // Create new network instance
    network = new vis.Network(container, data, options);
    
    // Fit the network to the container
    network.once('stabilizationIterationsDone', function() {
        network.fit({
            animation: {
                duration: 1000,
                easingFunction: 'easeInOutQuad'
            }
        });
    });
    
    // Handle window resize
    window.addEventListener('resize', function() {
        if (network) {
            network.fit({
                animation: {
                    duration: 500,
                    easingFunction: 'easeInOutQuad'
                }
            });
        }
    });
}

// Function to initialize the graph when the page loads or when navigating back
function initializeGraph() {
    const graphDataElement = document.getElementById('graph-data');
    if (graphDataElement) {
        try {
            const graphData = JSON.parse(graphDataElement.textContent);
            const resultsArea = document.getElementById('results-area');
            if (resultsArea) {
                resultsArea.style.display = 'block';
            }
            renderGraph(graphData);
        } catch (e) {
            console.error('Error parsing graph data:', e);
        }
    }
}

// Initialize graph when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Check if we have graph data in the page
    const graphDataScript = document.querySelector('script[type="application/json"][data-graph]');
    
    if (graphDataScript) {
        try {
            const graphData = JSON.parse(graphDataScript.textContent);
            const resultsArea = document.getElementById('results-area');
            if (resultsArea) {
                resultsArea.style.display = 'block';
            }
            renderGraph(graphData);
        } catch (e) {
            console.error('Error parsing graph data:', e);
        }
    }
    
    // Handle browser back/forward navigation
    window.addEventListener('popstate', function() {
        // Small delay to ensure the DOM is updated
        setTimeout(initializeGraph, 100);
    });
});
