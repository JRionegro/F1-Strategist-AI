/**
 * Resizable Dashboards using interact.js
 * Allows users to resize dashboard panels by dragging corners/edges
 */

// Load interact.js from CDN
(function() {
    var script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/interactjs@1.10.17/dist/interact.min.js';
    script.onload = initResizable;
    document.head.appendChild(script);
})();

function initResizable() {
    // Wait for DOM to be ready and dashboards to load
    function setupResizable() {
        var dashboards = document.querySelectorAll('.dashboard-grid-col');
        
        if (dashboards.length === 0) {
            // Retry after a short delay if dashboards not loaded yet
            setTimeout(setupResizable, 500);
            return;
        }

        interact('.dashboard-grid-col')
            .resizable({
                // Resize from all edges and corners
                edges: { left: true, right: true, bottom: true, top: true },
                
                listeners: {
                    move: function(event) {
                        var target = event.target;
                        var x = (parseFloat(target.getAttribute('data-x')) || 0);
                        var y = (parseFloat(target.getAttribute('data-y')) || 0);

                        // Update element's width and height
                        target.style.width = event.rect.width + 'px';
                        target.style.height = event.rect.height + 'px';
                        
                        // Remove flex constraints to allow free resizing
                        target.style.flex = 'none';
                        target.style.maxWidth = 'none';

                        // Translate when resizing from top or left edges
                        x += event.deltaRect.left;
                        y += event.deltaRect.top;

                        target.style.transform = 'translate(' + x + 'px,' + y + 'px)';
                        target.setAttribute('data-x', x);
                        target.setAttribute('data-y', y);
                    }
                },
                
                modifiers: [
                    // Minimum size
                    interact.modifiers.restrictSize({
                        min: { width: 250, height: 200 }
                    })
                ],

                inertia: true
            });
        
        console.log('Resizable dashboards initialized for', dashboards.length, 'panels');
    }

    // Initial setup
    setupResizable();
    
    // Re-setup when dashboards are updated (Dash callbacks may recreate them)
    var observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes.length > 0) {
                // Check if dashboard grid was updated
                var container = document.querySelector('.dashboard-grid-container');
                if (container && container.contains(mutation.target)) {
                    setTimeout(setupResizable, 100);
                }
            }
        });
    });
    
    // Observe changes to the dashboard container
    setTimeout(function() {
        var container = document.querySelector('.dashboard-grid-container');
        if (container) {
            observer.observe(container.parentNode, { childList: true, subtree: true });
        }
    }, 1000);
}
