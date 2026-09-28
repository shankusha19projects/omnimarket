# Deep Signal — OmniMarket design system

A custom theme (theme-factory "create your own theme") for an institutional terminal.

## Philosophy

Information is the ornament. The interface recedes into near-black depth so that numbers — the only thing that matters — come forward in crisp tabular monospace. Structure is carried by hairlines, not boxes; hierarchy by weight, size and letter-spacing, not color. Color is reserved for meaning: green and red for direction (always paired with ▲ ▼ and a sign so meaning never depends on hue), electric cyan for focus and selection, amber for attention and "live" signals, violet for interpretation as distinct from fact.

Every surface should feel machined: 1px borders that align across panels, a faint top-light gradient on each panel, generous but disciplined spacing, uppercase micro-labels tracked wide, and motion that only ever explains a change (fades on arrival, a sweep while refreshing, a pulse for open markets).

Provenance is part of the visual language: every data surface carries a small `SOURCE` badge whose status dot tells you at a glance whether a value is live, cached or stale.

## Palette (dark)

| Token | Hex | Use |
|---|---|---|
| `--bg-0` | `#05070b` | canvas |
| `--panel` | `#0e131b` | cards / panels |
| `--line` / `--line-2` | `#1b2431` / `#243041` | hairlines |
| `--text` / `--text-2` / `--text-3` | `#e7ecf3` / `#a3afc0` / `#6b778a` | text hierarchy |
| `--accent` | `#37c8f5` | focus, selection, primary |
| `--amber` | `#f5b544` | attention, live, scores |
| `--violet` | `#8d8cff` | interpretation, secondary series |
| `--up` / `--down` | `#22d38b` / `#ff5470` | direction |

The light theme redefines the same tokens (`#eef1f5` canvas, white panels, deeper greens/reds for contrast). A system mode follows the OS preference.

## Type

* **IBM Plex Sans** — UI text
* **JetBrains Mono** — all numbers (tabular figures)
* **Space Grotesk** — page titles and headline figures

## Components

Panels (`.panel`), KPI quote cards with sparklines, dense sticky-header sortable tables, direction pills, provenance popovers, segmented controls, skeleton shimmer loaders, empty/error states, command palette, refresh drawer, treemap heatmaps, curve and matrix charts. See `frontend/src/styles/*.css` and `frontend/src/components/ui.tsx`.
