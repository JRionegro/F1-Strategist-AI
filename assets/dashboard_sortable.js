(function () {
    const SORTABLE_SRC = "https://cdnjs.cloudflare.com/ajax/libs/Sortable/1.15.2/Sortable.min.js";
    const CONTAINER_ID = "dashboard-grid-inner";
    const DATA_FLAG = "dashboardSortableInit";

    function ensureSortableLoaded(callback) {
        if (window.Sortable) {
            callback();
            return;
        }

        const existing = document.querySelector("script[data-sortable-cdn]");
        if (existing) {
            if (existing.dataset.loaded === "true") {
                callback();
            } else {
                existing.addEventListener("load", () => callback(), { once: true });
            }
            return;
        }

        const script = document.createElement("script");
        script.src = SORTABLE_SRC;
        script.async = true;
        script.dataset.sortableCdn = "true";
        script.addEventListener("load", () => {
            script.dataset.loaded = "true";
            callback();
        });
        document.head.appendChild(script);
    }

    function dispatchOrder(container) {
        const ids = Array.from(container.querySelectorAll(".dashboard-grid-col"))
            .map((node) => node.dataset.dashboardId)
            .filter(Boolean);

        container.dispatchEvent(
            new CustomEvent("dashboardorder", {
                detail: ids,
                bubbles: true,
            })
        );
    }

    function initSortable() {
        const container = document.getElementById(CONTAINER_ID);
        if (!container) {
            return;
        }

        // Already initialised on this exact DOM node — skip
        if (container.dataset[DATA_FLAG] === "true") {
            return;
        }

        if (!window.Sortable) {
            ensureSortableLoaded(initSortable);
            return;
        }

        // FIX: handle must be a *child* element of the draggable tile.
        // Using ".card-header" lets users drag from the card title bar.
        // The draggable selector stays as ".dashboard-grid-col".
        window.Sortable.create(container, {
            animation: 150,
            handle: ".card-header",
            draggable: ".dashboard-grid-col",
            ghostClass: "sortable-ghost",
            chosenClass: "sortable-chosen",
            onEnd: function () {
                dispatchOrder(container);
            },
        });

        container.dataset[DATA_FLAG] = "true";
    }

    // FIX: Dash does NOT emit a "dash-rendered" event.
    // Use a MutationObserver to detect when Dash replaces #dashboard-grid-inner
    // so Sortable is (re)initialised on every render cycle.
    function startObserver() {
        const observer = new MutationObserver(function (mutations) {
            for (const mutation of mutations) {
                for (const node of mutation.addedNodes) {
                    if (!(node instanceof Element)) continue;
                    // The added node might be the container itself or contain it
                    if (node.id === CONTAINER_ID ||
                        node.querySelector("#" + CONTAINER_ID)) {
                        setTimeout(initSortable, 50);
                        return;
                    }
                }
            }
        });

        observer.observe(document.body, { childList: true, subtree: true });
    }

    function bootstrap() {
        ensureSortableLoaded(initSortable);
        startObserver();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", bootstrap);
    } else {
        setTimeout(bootstrap, 0);
    }
})();
