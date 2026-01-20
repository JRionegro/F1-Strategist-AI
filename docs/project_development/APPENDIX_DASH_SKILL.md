# Dash Dashboard Appendix (Project Rules)

This appendix captures the rules we **must** follow when adding or refactoring Dash dashboards in this project.
Use it as a checklist to avoid layout flicker, remounts, or sizing regressions.

## Layout and Structure
- Place dashboard tiles directly into the shared grid container (`dashboard-grid-container`).
- Do **not** wrap dashboards in inner `dbc.Col` with fixed widths; the grid sets width (33% landscape, 50% portrait).
- Each dashboard tile should be a single root container (card/div) plus an outer wrapper `html.Div(id="<name>-wrapper")`
  only when the wrapper is used by a refresh callback.
- Keep heights consistent via card classes (e.g., `mb-3 h-100`) rather than inline widths.
- Avoid inline widths that fight the grid; prefer CSS in `assets/responsive_grid.css` when needed.

## Rendering and Refresh Patterns
- Initial mount: build the static shell in `update_dashboards`; use wrappers for panels that refresh via stores.
- Independent refresh: use dedicated callbacks targeting `*-wrapper` with `allow_duplicate=True` to avoid remounting AI
  or unrelated panels.
- Race Overview: refresh body via `simulation-time-store` without rebuilding the whole dashboard list.
- AI panel: render in its own callback (`ai-dashboard-slot`) to keep it stable when other dashboards refresh.

## Stores and Timing
- Read simulation time from `simulation-time-store` in refresh callbacks; fall back to `simulation_controller` only when
  the store is missing.
- Throttle heavy refreshes using `_DASHBOARD_UPDATE_INTERVAL` logic; keep fast badges or labels on their own light
  callbacks.
- Never add new callbacks that mutate `chat-messages-container` directly; the store-to-container sync is the single
  writer.

## Caching
- Use lightweight caching to avoid recomputing unchanged dashboards (see `_cached_weather_component`, telemetry, race
  control). Cache keys must include session key and any driver/lap parameters.
- When returning cached components, ensure the wrapper IDs stay stable so downstream refresh callbacks keep working.

## Error and Loading States
- Provide loading placeholders without extra grid columns (no nested `dbc.Col(width=4)`).
- Error cards should keep the same outer structure and wrapper IDs used by the normal panel.

## Adding a New Dashboard (checklist)
1. Add its option to `dashboard-selector` if user-toggleable.
2. In `update_dashboards`, create the shell:
   - If it will self-refresh, wrap in `html.Div(id="<name>-wrapper")` and mount the initial content (or placeholder).
   - Keep markup free of inner width-constraining columns; let the grid size it.
3. Add a dedicated refresh callback if it needs periodic/store-driven updates. Use `allow_duplicate=True` on the wrapper
   output and gate with `selected_dashboards` + `session-store` loaded check.
4. Reuse `simulation-time-store` instead of adding new intervals. If you add new intervals, document why.
5. Add caching if the render is expensive; key on session, driver(s), lap, or time as appropriate.
6. Verify no callback writes directly to components that another callback also writes (single-writer rule).
7. Test at least: (a) initial load, (b) simulation running with `simulation-time-store` updates, (c) pause/resume,
   (d) toggling dashboard selection.

## What to Avoid
- Nested grid/column wrappers that conflict with the shared grid sizing.
- Re-rendering AI or other panels on every tick—keep them on dedicated callbacks.
- Creating new stores for timing when `simulation-time-store` suffices.
- Multiple writers to the same output without `allow_duplicate=True` and explicit ownership.

Keep this appendix close when touching Dash code to prevent regressions and layout flicker.

## Track Map Inspiration and Credits
- F1 Race Replay (MIT License) provided the initial idea for animating car sprites over precomputed polylines. See:
  - `src/arcade_replay.py` (Arcade window setup, game loop, pyglet renderer)
  - `src/interfaces/race_replay.py` (animation orchestration, frame stepping)
  - `src/ui_components.py` (track geometry helpers, driver sprite updates)
- Reuse obligations under MIT: retain the original copyright notice and permission text when sharing binaries or source.
- Adaptation note: when porting to Dash/Plotly we replace Arcade sprites with scatter traces and feed tween data from `FastF1PositionProvider` caches.
