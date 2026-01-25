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

        if (container.dataset[DATA_FLAG] === "true") {
            return;
        }

        if (!window.Sortable) {
            ensureSortableLoaded(initSortable);
            return;
        }

        window.Sortable.create(container, {
            animation: 150,
            handle: ".dashboard-grid-col",
            draggable: ".dashboard-grid-col",
            onEnd: function () {
                dispatchOrder(container);
            },
        });

        container.dataset[DATA_FLAG] = "true";
    }

    function bootstrap() {
        ensureSortableLoaded(initSortable);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", bootstrap);
    } else {
        setTimeout(bootstrap, 0);
    }

    document.addEventListener("dash-rendered", () => {
        setTimeout(initSortable, 0);
    });
})();
