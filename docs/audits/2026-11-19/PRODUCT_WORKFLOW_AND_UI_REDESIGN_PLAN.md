# TrainTrace Product Workflow and UI Redesign Plan

**Status:** Implementation underway — product flow implemented; visual consolidation and complete browser journey remain open  
**Review date:** 2026-11-19  
**Basis:** PRD v5.2, 2026-11-17 clarification, current React screen/navigation code, inference and decision flows, and the screenshots shared in this conversation.

## Executive assessment

TrainTrace has real product capabilities: queued PyTorch training, validation-based candidate comparison, live and saved metrics, reproducibility replays, human decisions, versioned model registration, checkpoint comparison, registered-model inference, and investigation lineage. The problem is that the interface presents these as many separate destinations and gates. It asks users to learn internal lifecycle terms before they can answer the practical question: “Which trained model works best for my data, and why?”

Based on the source structure and screenshots available here, the UI is functional but not yet visually impressive or coherent enough to claim a premium finish. It looks template-like in part because many screens are composed from the same generic panel/form pattern, the navigation exposes too many concepts at once, and the CSS is split across large overlapping layers and late overrides. A live browser review could not be completed in this environment because the browser access host was unavailable.

## What the product is for

The PRD positions TrainTrace as an evidence-led deep-learning investigation tool. Its distinguishing value is the chain:

**Question → approach/configuration → training run → evidence → comparison → human decision → (optional) release**

The product should make that chain easy to follow. Model registration is a lifecycle/release operation, not a prerequisite for trying a trained checkpoint on an uploaded image. Reproducibility analysis is supporting evidence, not a mandatory page in every experiment. History is the record of the investigation, not a separate step users must visit to finish work.

## Key findings from current code

1. **Inference is split into two different workflows on one page.** `Inference.jsx` has “Compare completed run checkpoints” and “Predict with the active registered version.” The first can compare trained runs without registration; the second uses an activated registered release. This distinction is present in code but is not prominent enough in the overall journey.
2. **Registration is presented as a required next step.** `WorkflowNavigation.jsx` makes Decisions → Registry → Inference the main progression. `Registry.jsx` gates registration on a selected decision and completed final test evaluation. That is appropriate for promoting a release, but it incorrectly feels like the only way to test a model.
3. **Candidate testing and final evaluation need clearer names and boundaries.** The user can run uploaded-image predictions on completed checkpoints. An image prediction is not an accuracy measurement unless the true label is known. The final holdout test is a one-time post-selection evaluation; it should not be used to compare multiple candidates. The PRD’s comparison language and current holdout gate should be reconciled explicitly.
4. **“Audits” is a confusing label for reproducibility workflows.** `Audits.jsx` combines run evidence with Protocol A repeatability and Protocol B seed sensitivity. Those are useful research tools, but they are optional and should be called “Reproducibility” in user-facing navigation and placed alongside comparison/run evidence.
5. **History duplicates decision/reasoning access.** `History.jsx` presents predecessor links, candidate decisions, evidence, and report downloads, while Decisions, Registry lineage, and reports also expose parts of that story. The reasoning chain belongs in an investigation timeline/report, not as a mandatory primary navigation destination.
6. **The sidebar has nine destinations.** `app/config.js` exposes Investigations, Training, Compare, Audits, Decisions, History, Registry, Inference, and Search. These mix workflow steps, optional analyses, and utility destinations at the same navigation level.
7. **The styling system has accumulated competing layers.** `main.jsx` imports `index.css` and `mlflow-design.css`; `index.css` imports eight broad stylesheets, including `foundation.css`, `shell-components.css`, `application-components.css`, `theme-overrides.css`, `shape-system.css`, and `workspace-refresh.css`. Several are large and late-loaded, so a component’s appearance depends on cascade order rather than a small, clear set of design tokens and component rules.
8. **Screen components are large and share generic patterns.** `Training.jsx` and `Inference.jsx` are each about 750 lines; CSS files range from roughly 240 to 800 lines. Reusing generic panels for distinct tasks makes the product feel like a form template and makes visual fixes risky.
9. **The existing graph issues are real UX failures, not just decoration.** Screenshots show legend labels crowding chart plots and axes/labels that are hard to read. Charts need bounded containers, responsive layout, short series labels, and readable tooltips/legends as part of the component contract.

## Clarifications to make before implementation

### Registration

- **Candidate checkpoint comparison/inference:** available from completed runs; no registration required. Use this for “try both models on my image.”
- **Registered serving:** register a selected, finally evaluated candidate as a named immutable version, then activate it for the stable inference endpoint. This is a release/provenance feature.
- **Accuracy on one uploaded image:** show “correct/incorrect” only if the user supplies the expected class or the image comes from a labeled evaluation set. Otherwise show prediction, confidence, and latency, not “accuracy.”

### Audits and History

- Rename **Audits** to **Reproducibility** and keep it optional. Make its purpose explicit: repeated same-seed execution checks repeatability; multiple controlled seeds estimate sensitivity.
- Remove **History** from primary navigation. Put the investigation timeline and decision report inside the investigation workspace, with links from Compare, Decisions, and registered model lineage.

### Final holdout evaluation

Keep final test data sealed during candidate comparison. Select one candidate based on validation evidence, then run the one final holdout evaluation. Make the one-candidate reservation rule visible before submission, and explain how to start a new investigation if the researcher wants another final candidate. Do not present final test accuracy as a filter for unselected candidates.

## Proposed information architecture

### Primary navigation

1. **Investigations** — objective, hypothesis, progress, candidate count, latest decision, and compact lineage/timeline.
2. **Runs** — configure a run and monitor its live execution; completed runs link directly to comparison and checkpoint inspection.
3. **Compare** — candidate table, validation trajectories, trade-offs, and run-level image-checkpoint comparison.
4. **Models** — registered releases, activation state, lineage, and serving status. Registration remains reachable from the selected candidate decision as an action.

### Contextual utilities

- **Reproducibility**: optional section/tab under Compare or a selected run’s evidence view.
- **Investigation history/report**: timeline/report in the investigation workspace, not a sidebar destination.
- **Search**: global header search with advanced filters available in the results view, not a peer workflow step.
- **Inference**: candidate checkpoint comparison in Compare; active registered serving in model details. Avoid forcing users to understand two meanings of “inference” on one page.

## Screen-by-screen redesign

### 1. Investigations

- Make “New investigation” a compact, focused action; keep name, objective, and hypothesis because they anchor the reasoning chain.
- Replace long repeated cards with a dense, scannable table/list: objective, status, runs, selected candidate, last activity.
- Open an investigation workspace with a clear progress summary and chronological approach timeline.
- Move archived/advanced metadata editing out of the main creation path.

### 2. Runs / Training

- Use a guided configuration form with basic controls visible first: dataset, architecture, epochs, batch size, optimizer, learning rate, seed.
- Put advanced controls (CustomCNN depth/width/dropout, scheduler, predecessor/checkpoint initialization, worker/device details) in clearly labeled expandable sections. Preserve the controls that affect scientific validity or model shape; do not remove them just to shorten the page.
- Explain choices inline in plain language and show the estimated run time/resource implications where reliable.
- Make execution status a live run detail view: dataset preparation, current epoch/batch, throughput, loss/accuracy, resource metrics, logs/events, and artifacts. The chart grid must stay within the content column.
- Keep “predecessor” only when it actually links to a prior approach; label it “Continue investigation from…” and clearly state what is inherited versus merely linked.

### 3. Compare

- Lead with a candidate table and selection controls; keep the default to comparable runs from the same dataset/split.
- Default comparison to validation metrics (accuracy/loss trajectories, best epoch, duration, model size, latency, resource use when available). Clearly label missing/unmeasured metrics rather than displaying blanks or implied zeros.
- Put advanced filters behind one “Filters” disclosure; keep commonly used dataset/architecture/status filters visible only when they help the current list.
- Place “Try an image on selected checkpoints” here as a candidate evaluation tool. If an expected label is provided, show per-model correctness; otherwise show prediction/confidence/latency.
- Provide an explicit next action: record the human decision after reviewing validation evidence.

### 4. Reproducibility (currently Audits)

- Make this an optional evidence panel/tab, not a mandatory lifecycle step.
- Explain Protocol A (repeat same configuration and seed) and Protocol B (vary seeds, hold the data split fixed) before showing seed inputs.
- Show queued/running/completed/failed state, member runs, statistics, and failures in one report with a rerun action.
- Avoid presenting holdout test metrics here before candidate selection.

### 5. Decisions

- Make the decision action part of the comparison flow and visibly connect each decision to its run and validation snapshot.
- Keep the rationale and limitations required for traceability. Collapse alternatives/trade-offs/next investigation into a clearly explained “Reasoning details” section, with concise prompts and examples; do not remove required evidence capture without changing the PRD.
- Present final holdout evaluation after selecting one candidate, with a clear irreversible/one-candidate explanation.
- Offer **Register as a model version** after successful final evaluation, as an optional release action. A user must still be able to inspect candidate checkpoints before this stage.

### 6. History / investigation timeline

- Remove the standalone sidebar entry.
- Show each approach chronologically with predecessor, motivation, run status, validation summary, decision, and rationale.
- Put full JSON/evidence behind “Details” and provide a readable report/export action.
- Keep unknown legacy fields marked unknown instead of filling in guessed values.

### 7. Models / Registry

- Rename the user-facing destination to **Models**; explain that a registered version is a frozen, named release and activation selects the version used by the stable serving endpoint.
- Keep registration validation inline and explain why a candidate is ineligible in one sentence.
- Use a model table with version, source run, dataset, decision, final evaluation, active state, and actions.
- Keep lineage available from each model version, but use a readable timeline/config summary before raw JSON.

### 8. Inference

- Separate candidate comparison from registered serving in both navigation and language.
- Candidate mode: select up to a few completed checkpoints, upload one image, optionally supply its known label, and compare predicted class, confidence, correctness when label is known, and latency.
- Serving mode: choose an activated model version, submit a sample, and show output plus immutable release/run provenance.
- Explain dataset preprocessing/image dimensions so predictions are not silently invalid due to normalization or shape mismatch.

### 9. Search and reports

- Move basic search into the global header; retain a full results page for advanced filters.
- Separate validation metrics from final holdout metrics in filters and exports.
- Ensure report downloads are discoverable from the investigation summary and model lineage.

## Visual system plan

1. Establish a small token set for typography, spacing, surfaces, border, elevation, focus, status, chart colors, and light/dark themes.
2. Choose one consistent visual language: restrained neutral surfaces, one brand accent, distinct semantic status colors, clear density, and purposeful whitespace. Avoid gradients, oversized decorative cards, and generic dashboard ornament unless they carry meaning.
3. Build a small set of task-specific primitives: page header, section header, metric tile, status badge, data table, chart card, empty/error/loading state, disclosure, confirmation/action bar, and accessible form field.
4. Consolidate the competing stylesheet layers; remove old overrides only after each component has moved to the token/component rules. Avoid another “last override” stylesheet.
5. Redesign charts as bounded, responsive visual components with plot padding, axis labels, compact legend chips, distinct line styles, keyboard/screen-reader summaries, and a full-screen/detail option only where it helps.
6. Define responsive behavior deliberately: desktop data density, tablet layout, narrow-screen stacked cards, and horizontally scrollable tables with sticky identifying columns.
7. Inspect all screens in both themes at desktop and mobile widths. Browser verification is currently unavailable in the inspection environment, so that must be retried during implementation before calling the visual pass complete.

## Detailed visual design blueprint

The values below are the implementation target, not a claim that the current UI already meets them. Colors and type sizes must be checked for contrast and actual rendering during browser review. Keep the TrainTrace brand identity and use MLflow as a reference for data density, navigation clarity, tables, and experiment charts; do not copy MLflow branding or imply TrainTrace has data/serving capabilities it does not implement.

### A. Design principles and tone

- **Feel:** a focused research workbench: precise, calm, technical, and trustworthy. Avoid a generic “AI dashboard” look (large gradient hero blocks, decorative blobs, excessive rounded cards, glowing accents, or repeated oversized headings).
- **Hierarchy:** answer “what is selected, what happened, what should I do next?” before exposing configuration detail.
- **Density:** fit meaningful run/metric information above the fold on desktop while keeping row height and labels readable. Use whitespace to separate sections, not to inflate every panel.
- **Evidence first:** show data source, split (train/validation/final holdout), unit, sampling interval, and missing-data reason near each metric visualization.
- **One primary action per view:** emphasize the action that advances the user’s current task; use secondary styling for export, refresh, branch, and advanced controls.

### B. Typography

| Role | Target | Usage |
| --- | --- | --- |
| UI sans | `Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif` | Navigation, labels, controls, body, tables |
| Numeric/data | `Inter` with `font-variant-numeric: tabular-nums` | Metrics, progress, table numbers, chart readouts |
| Code/IDs | `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace` | Run IDs, hashes, paths, code/config snippets |
| Page title | 26 px / 32 px, weight 620–680 | One per page; 22 px on narrow screens |
| Section title | 16–18 px / 24 px, weight 600 | Panel and major workflow section headings |
| Body | 14 px / 21 px, weight 400 | Explanations and main content |
| Compact metadata | 12 px / 17 px, weight 400–500 | Units, timestamps, helper copy, chart notes |
| Form label | 13 px / 18 px, weight 550–600 | Inputs, selects, toggles |

Use a small hierarchy rather than arbitrary per-component sizes. Do not set body copy below 13 px except dense metadata. IDs may be monospace but must not dominate the row; truncate visually and expose the complete value on copy/tooltip.

### C. Color and theme tokens

Initial token proposal (adjust only through centralized tokens after contrast review):

| Token | Light | Dark | Meaning |
| --- | --- | --- | --- |
| `canvas` | `#F5F7FA` | `#101720` | App background |
| `surface-1` | `#FFFFFF` | `#18222E` | Main content and cards |
| `surface-2` | `#F0F3F7` | `#1E2A38` | Subpanels, table header, selected rows |
| `surface-raised` | `#FFFFFF` | `#222F3F` | Menus, popovers, dialogs |
| `text-primary` | `#172333` | `#E8EEF6` | Main labels and values |
| `text-secondary` | `#4E5F73` | `#B5C1D0` | Body/supporting copy |
| `text-muted` | `#68788B` | `#91A0B2` | Metadata only; not critical instructions |
| `border` | `#D5DDE7` | `#344355` | Dividers, control outlines |
| `accent` | `#1769AA` | `#62A9F2` | Links, selected navigation, primary action |
| `focus` | `#1677C8` | `#80C7FF` | Visible keyboard focus ring |
| `success` | `#16794B` | `#58C58A` | Completed/healthy |
| `warning` | `#94600A` | `#E8B85B` | Queued, caution, approaching limit |
| `danger` | `#B42332` | `#FF737D` | Failed, destructive, invalid |
| `info` | `#3266A8` | `#81B5F0` | Explanatory status |

Rules:

- Keep the main canvas neutral; reserve brand blue for active/action states and links.
- Never rely on color alone for status. Pair color with text/icon and an accessible name.
- Every text/background pairing must meet WCAG AA contrast (4.5:1 normal text; 3:1 large text and meaningful UI graphics), verified in both themes.
- Use semantic tokens for states. Avoid individual hex colors inside screen components and chart definitions.
- Keep the sidebar dark in both themes as a stable navigation rail; theme-switch the content surfaces and ensure active item/focus contrast remains obvious.

### D. Spacing, geometry, and elevation

- Base spacing unit: 4 px; primary sequence: 4, 8, 12, 16, 20, 24, 32, 40, 48 px.
- Main sidebar: 248 px expanded, 68 px collapsed. Header: 64–72 px. Main content padding: 28 px desktop, 20 px tablet, 14 px mobile.
- Content maximum width: 1,520 px for tables/charts; reading-width explanations capped near 760 px.
- Control height: 38 px standard, 32 px compact table/filter control, 44 px touch-sized mobile control.
- Radius: 6 px controls, 8 px cards, 10 px dialogs, pill shape only for status/compact tags. Avoid using 16–24 px radii on every rectangle.
- Elevation: one subtle menu/dialog shadow; ordinary panels use border and surface contrast, not a shadow stack.
- Use a consistent 1 px divider; avoid nested boxes inside boxed cards unless the nested section has a clear separate interaction.

### E. Shell, navigation, and page header

- Keep a persistent sidebar with four primary destinations: **Investigations**, **Runs**, **Compare**, **Models**. Give each a simple 18 px line icon, 36–40 px item height, active left marker and tinted active surface.
- Sidebar bottom: compact backend/worker health indicator with explicit text (`API connected`, `Worker offline`) and queue count; do not let it compete with navigation.
- Put global search, theme switch, and refresh/update status in the top header. Refresh must visibly show last-updated time or loading and report failures; do not make it an unlabeled icon.
- Page header: breadcrumb/context on top when inside an investigation or run; title + one-line description; primary action aligned right. Keep global actions visually secondary.
- Show a compact investigation/run context bar only on workflow pages. Avoid repeating a large investigation summary card on every page.
- Workflow progress indicator should show the user’s current place and optional branches, not present every utility as a required step. Blocked states must state the exact reason and point to the relevant action.

### F. Component specifications

#### Buttons

- Primary: solid accent, white/high-contrast text, 38 px height; one per section/form. Use explicit verbs (“Queue training”, “Compare checkpoints”, “Select candidate”).
- Secondary: neutral surface + border; tertiary: text button; destructive: danger outline/filled only for irreversible deletion/stop operations.
- Hover, pressed, disabled, loading, and keyboard focus states are distinct. Disabled actions retain explanatory help text outside the button; tooltips alone are insufficient.
- Do not label data refresh as “Refresh” if its scope is unclear; show “Updated 10:42” and “Refresh data” with spinner/disabled state while loading.

#### Text fields and text areas

- Label always visible above the control; required indicator next to label, never placeholder-only labels.
- Helper text explains why the input exists and its units/format. Error text goes immediately below and says how to correct the value.
- Focus uses a 2 px visible ring plus a 1 px control border; a blue ring is expected only on keyboard/pointer focus, not permanently after blur.
- Text areas have a deliberate min-height, resize behavior, character guidance for long reasoning fields, and no browser-default resize grip if it conflicts with the design.

#### Selects, dropdowns, and multi-selects

- Use native `<select>` for short stable lists where native keyboard/accessibility behavior is adequate; style it consistently (38 px height, chevron, focus/error state).
- For searchable/long run and model lists, use an accessible combobox with search, clear selection, selected checkmark, status/architecture metadata, empty result, and keyboard navigation. Never render hundreds of options unfiltered.
- Group options by meaningful category (dataset, architecture, status) only when groups help scanning. Put the current/active choice first and make defaults visible.
- Multi-select candidate controls show selected count and concise chips with remove controls; selected candidates stay visible if filters change.
- Menus open aligned to the control, stay within viewport, scroll internally, close on Escape/outside click, and return focus to the opener.
- Dropdown items show label and secondary context; avoid long IDs as the primary title. Do not use a plain HTML list that clips behind a chart or modal.

#### Cards, sections, and disclosures

- A card is for a task or coherent evidence unit, not merely because content exists. Use header/title, optional concise description, body, and actions with consistent spacing.
- Prefer flat section divisions for sequential content; use bordered cards for independent modules (e.g. each chart, each candidate detail).
- Advanced settings use `<details>`/disclosure with “Advanced settings” and a short preview of hidden categories. Preserve the user’s expanded/collapsed preference only when useful.
- Empty/loading/error states have distinct layouts, a useful explanation, and a next action (e.g. select investigation, wait for first batch, retry after API recovery).

#### Tables

- Header 12 px uppercase or sentence case (choose one; preferred sentence case), sticky at the top of the table viewport. Row height 44–52 px; selected/hover/focus states visible.
- Right-align numeric values; align decimals with tabular numerals; display units in header or adjacent muted suffix.
- Keep identity columns (run name/status) sticky on wide comparisons; place optional columns behind a column selector.
- Avoid clipping key values. IDs use shortened display + copy button; full value available by tooltip/accessibility label.
- Provide sortable headers with direction indicator, empty-state explanation, row selection count, and accessible caption.
- Mobile uses labeled candidate cards for a small set; large tables use a clearly indicated horizontal scroll region.

#### Status badges and alerts

- Fixed mapping for `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `STOPPED`, `SELECTED`, `REJECTED`, and `SUPERSEDED` with text and icon; no ad hoc status colors.
- Alerts are for meaningful system/user outcomes; persistent blockers stay near the action they block. Toasts confirm completed actions, not replace error explanations.
- Status updates use semantic live regions without announcing every metric sample.

### G. Chart and visualization design

#### Chart catalog and data contract

Offer a chart builder over **metrics that are actually logged for the selected run**. The current Training screen defines: batch loss, running accuracy, throughput (`samples_per_sec`), device memory, worker CPU, peak worker RSS, epoch train/validation loss and accuracy, learning rate, and epoch duration. Display an unavailable state when a metric is null or unsupported on the active device; do not plot null as zero.

Do not label host RSS as GPU memory. `device_memory_mb` is device-allocated memory on CUDA/MPS where supported; CPU runs may have no device memory value. New metrics such as GPU utilization, disk/network I/O, temperature, or power require backend instrumentation and must not appear as if measured before that exists.

#### Chart card anatomy

Each chart has: concise title; metric/unit; latest value and direction/change where meaningful; plot with axis labels/ticks; compact legend; tooltip with exact timestamp/epoch/step; data source and sampling note; overflow-safe container; and accessible textual summary. Keep the legend outside the plot area and wrap it as chips when multiple series are present.

#### Chart rules

- Use line charts for trajectories. Bars are for discrete comparisons/distributions, not noisy per-batch series by default. Area is only appropriate for a justified cumulative/filled measure.
- Candidate colors use a color-blind-conscious palette: blue `#2878B5`, orange `#D17A22`, teal `#198A78`, purple `#8063B5`, red `#C6545D`, slate `#65758B`. Also distinguish series by dash pattern/marker, so color is not the only signal.
- Training/validation pair uses solid/dashed variants of a related hue (not two near-identical solid colors). Candidate identity remains consistent across all charts in one comparison.
- Plot padding must reserve label space; chart SVG/canvas width is responsive and constrained to its parent (`min-width: 0`, max-width 100%). Long run names belong in the legend area, shortened to approach + model/dataset; full value is in tooltip/details.
- Show honest x-axis semantics: epoch, global step, or elapsed time. Never use batch index as epoch or label sampled points as every batch.
- Axis domains: use meaningful zero baselines for accuracy/resource charts unless the user explicitly selects a zoomed range; loss may use a data-driven range with visible tick values. Log scale has a clear badge and must reject/handle zero and negative values.
- Smoothing is an optional display-only moving average; show raw data on hover or toggle. It must never alter saved values or exported data.
- Missing series, one point, all-equal values, very long series, interrupted runs, and failed runs get deliberate states; do not draw out-of-bounds points or a misleading flat line.
- Keep charts within cards. Plot, legend, and footnotes use separate layout regions; modal/fullscreen expands plot width but preserves the same axis and legend contract.

#### Run visualization layout

- Live run top row: status/progress, current epoch/batch, elapsed time/ETA only when estimate is reliable, throughput, device, and active memory metric.
- Primary 2×2 chart grid: train/validation loss, train/validation accuracy, throughput over steps, and device/worker memory. Hide a card when its data is unavailable; do not leave an empty hole or fabricate a substitute.
- “Add chart” opens a searchable metric picker; filters by batch/epoch/system category; lets user choose x-axis, smoothing, scale, and chart type only where the type makes sense. Layout controls (reorder/hide) are secondary and keyboard accessible.
- Saved runs keep the same chart definitions using persisted metric samples and expose CSV/JSON downloads with units and sample intervals.

#### Comparison visualizations

- Overlay only comparable runs (same dataset, split, metric definition); show a clear warning or require separate small multiples when dimensions differ.
- Use a persistent series-to-run color/style map across accuracy, loss, and resource charts. Comparison title states whether values are validation or final holdout.
- Default small multiples when overlay labels/curves become ambiguous. Keep a table for exact values; charts explain trajectories, not replace numeric results.
- Add metric selection and chart arrangement controls, but do not offer arbitrary transformations that the backend cannot calculate or the UI cannot label correctly.

### H. Page-by-page layout wireframes in words

#### Investigations landing/workspace

1. Header: “Investigations” + create button + global search.
2. Compact summary row: active investigation count, queued/running count, completed candidates needing a decision (only if computed from API data).
3. Investigation list/table with name/objective, status, run count, latest activity, selected model. Selecting a row opens the workspace.
4. Workspace body: objective/hypothesis summary; a horizontal/vertical approach timeline; latest evidence and clear actions (“Configure run”, “Compare candidates”, “Review report”).

#### Runs list and live run detail

1. Run list: searchable, filterable table with status, approach, dataset, architecture, epoch progress, validation score, duration.
2. Run detail header: run name/ID, status, investigation breadcrumb, stop/branch action where legal.
3. Progress/evidence strip followed by charts, collapsible logs/events, artifact downloads, and configuration snapshot.
4. Run configuration uses a sticky bottom action bar on long forms with “Save draft” only if draft persistence exists, otherwise “Queue run” and cancellation/back.

#### Compare workspace

1. Header/context and candidate picker (up to supported number); visible comparability grouping.
2. Candidate matrix first: validation accuracy/loss, best epoch, duration, throughput, checkpoint size, architecture and key config.
3. Trajectory chart panel with metric tabs or selector and shared run legend.
4. Resource/trade-off panel only for metrics measured for each candidate.
5. Candidate checkpoint image comparison drawer/panel.
6. Sticky decision action: select current candidate, reject/supersede with rationale, or investigate successor. No final-test data shown before selection.

#### Decision and final-evaluation state

1. Candidate identity + validation evidence summary.
2. Decision status control with concise rationale field.
3. Optional/advanced reasoning details (limitations, alternative considered, why not, next investigation) with prompts.
4. After `SELECTED`, show final test reservation explanation, one-run scope, and one explicit “Run final holdout evaluation” action.
5. After evaluation completes, show immutable report and optional “Register this release” action.

#### Models and serving

1. Registered model table/list with active badge, version, source run, dataset, final metric, and lineage action.
2. Model detail: summary, immutable manifest/provenance, lineage visualization, activation/rollback controls (only if rollback semantics are supported), and serving inference panel.
3. Candidate checkpoint comparison remains under Compare; never make the Models page a gate for trying a run artifact.

### I. Responsive behavior

- **≥1280 px:** expanded sidebar, two-column compare details, 2×2 charts, full comparison table.
- **768–1279 px:** collapsible sidebar, one-column charts or 2×1 where space permits, hide low-priority table columns.
- **<768 px:** drawer navigation, stacked cards, single-column forms/charts, 44 px controls, no fixed-width panels, sticky bottom action only if it does not obscure content.
- Breakpoints should be content-driven; test long investigation/run names, 6 candidate selections, large legends, validation errors, and open dropdowns at every width.
- Tables must remain operable with keyboard and touch; horizontal scrolling must not trap vertical scrolling.

### J. Accessibility and interaction states

- Keyboard order follows visual order; every menu/dialog returns focus; focus ring visible in both themes.
- Labels/description/error IDs are linked to controls; chart summaries are available to assistive technology; color is never the sole series identifier.
- Respect reduced-motion; data polling should not animate the entire chart or flash the page.
- Distinguish loading skeleton, no data yet, unsupported metric, no results, API error, and permission/validation error.
- Confirmation is required only before irreversible operations (final holdout reservation, destructive artifact/model removal if supported), with clear consequence text.

### K. Inspiration and implementation boundary

- Borrow from MLflow’s strong patterns: compact experiment/run navigation, dense filterable run tables, clear run detail metrics, metric search/selection, chart configuration, and experiment-level context.
- Borrow from polished developer tools: readable typography, a restrained token system, compact code/ID treatments, clear empty states, and fast contextual actions.
- Keep TrainTrace’s distinctive content: human decision rationale, controlled seed protocols, investigation branching, and traceable evidence.
- Do not copy components or source code wholesale. Recreate appropriate patterns in TrainTrace’s own React/CSS components and keep project-specific behavior as the source of truth.

### L. Design review artifacts before coding each phase

For the next implementation pass, prepare and review these in order:

1. Final workflow map and names (this plan’s proposed IA).
2. Desktop and mobile page wireframes for Investigations, Runs, Compare/Decision, and Models.
3. Light and dark token swatches and typography scale.
4. Component state sheet: buttons, text input, select/combobox, badges, table, chart card, alerts, dialogs, empty/loading/error states.
5. Chart examples using real TrainTrace data: batch metric, epoch metric, two-run overlay, unavailable system metric, one-point/flat series, failed/interrupted run.
6. Browser review checklist tied to the acceptance criteria below.

Implementation should proceed by coherent vertical slice: each slice updates navigation, screen, component styles, data states, and user-facing copy together. Avoid broad restyling via a final global override file.

## Implementation phases

### Phase 1 — Resolve product flow and terminology

- Update the PRD/addendum to distinguish checkpoint testing, final holdout evaluation, model registration, and serving.
- Agree on primary navigation and move optional/history/search functions to contextual locations.
- Confirm the one-final-evaluation-per-investigation policy is intentional and visible.

### Phase 2 — Repair workflow coherence

- Remove registry as a prerequisite for candidate checkpoint inference.
- Put candidate checkpoint testing in Compare and registered serving in Model details.
- Rework Decisions → final holdout → optional registration actions and correct blocked states.
- Rename/reposition Audits and merge History into the investigation timeline.
- Remove redundant page-level fields/actions after tracing their API and PRD contracts.

### Phase 3 — Rebuild UI foundations and screen hierarchy

- Consolidate theme tokens and component primitives.
- Redesign the sidebar, investigation workspace, run detail, candidate table, decision capture, and model table.
- Refactor oversized screen components into focused sections while preserving existing backend behavior unless a confirmed workflow defect requires an API change.

### Phase 4 — Charts, responsive behavior, accessibility

- Fix chart containment, axis/legend layout, labels, tooltips, and series distinction.
- Finish responsive and light/dark states, focus behavior, empty/error/loading states, and chart descriptions.

### Phase 5 — Verify the actual user journey

- Exercise: create investigation → configure run → observe progress → compare candidates → try an image before registration → record decision → final holdout evaluation → optionally register/activate → serve prediction → review history/report.
- Verify one failed/blocked path for each gate and one repeatability workflow.
- Check at least the relevant CIFAR-10 and CIFAR-100 model paths plus the notebook’s run-reporting role.
- Use browser screenshots and real workspace data to verify every primary screen in both themes and common viewport sizes. Report exactly what was and was not exercised.

## Acceptance criteria for calling the redesign complete

- A user can compare two completed candidate checkpoints on one image without registering either model.
- The UI never calls a single-image prediction “accuracy” unless the expected label is known.
- The final holdout set remains sealed until selection and only the selected candidate can consume the investigation’s final evaluation reservation.
- Registration is explained as immutable release/versioning; it is optional for candidate testing and required only for the stable active-model serving flow.
- Reproducibility is understandable and optional; History is no longer a primary navigation item.
- Every visible field has a documented reason, a real backend effect, and an appropriate default/advanced placement; dead or redundant fields are removed.
- Charts remain inside their cards, retain readable legends and axes, and distinguish runs clearly.
- The redesigned screens are visually consistent across themes and responsive widths, with implementation verified in a browser.
- Training, comparison, decisions, registration, inference, reports, and notebook outputs continue to refer to the same persisted run/evidence records.

## Implementation record — 2026-11-19

This plan remains the acceptance target. The code changes below are present in the current workspace; the remaining list is explicit so a build or unit test is never mistaken for full product verification. Existing unrelated worktree edits were preserved.

| Phase | Current state | Evidence |
| --- | --- | --- |
| 1. Product flow and terminology | Implemented | PRD workflow clarification, primary navigation, optional registration and reproducibility wording. |
| 2. Workflow coherence | Implemented in code | Candidate checkpoint testing in Compare, registered serving in Models, selected-run final evaluation gate, contextual Back/Next/iterate actions. |
| 3. UI foundations and hierarchy | Partially implemented | Screen sections, run list, configuration component, status tokens, saved investigation cards, sortable run/candidate tables. Legacy broad CSS layers still overlap. |
| 4. Charts, responsive behavior, accessibility | Partially implemented | Missing-value-aware charts, chart picker, CSV export, theme and mobile browser checks, validation and blocked-state guidance. The complete state/viewport matrix remains open. |
| 5. Actual user journey | Partially verified | Forty backend lifecycle/engine tests pass; existing-data browser navigation and selected-run paths were exercised. A new create-to-serving browser journey has not been completed. |

### Changes implemented in this pass

- Investigations: removed the decorative hero so saved records appear sooner; rendered saved records as readable cards on narrow screens; removed full IDs from the list while keeping ID search and the active record ID.
- Runs: added a searchable, status-filtered, sortable run list; extracted the long configuration form into a focused component; corrected the accumulated epoch-time label; removed the duplicate training progress bar; added a run-linked notebook guide.
- Compare: grouped filters in a disclosure; added removable selected-run chips and sortable evidence columns; preserved unknown dataset names instead of assuming CIFAR-10; kept validation trajectories separate for incomparable datasets or split seeds.
- Charts: omitted absent samples instead of plotting zero; broke lines across gaps; added exact point details, axis/scale notes, a metric picker, and bounded card rendering. Device memory remains absent when unmeasured.
- Decisions and next steps: summarized the selected run's validation evidence, clarified frozen/reserved states, pointed users to the selected or completed run when blocked, and removed duplicate register/iterate actions.
- Models: put immutable releases before registration; replaced oversized lineage diagrams with a compact sequence; made the release table scroll on mobile; sourced release identity from the frozen registration manifest in the backend.
- Reporting and notebook: withheld historical preselection holdout values in Markdown, CSV, CLI, and notebook views; notebook reads current `final_evaluation_json` and the same persisted run records as the app.
- Code organization: added focused components and CSS modules for the run list, notebook guide, status badge, investigation timeline, chart, and difference view; moved investigation table styles out of a broad theme override file.

### Verification performed

- `npm run build` passed after the chart, run-list, comparison, and component changes; repeat once after the final navigation and investigation edits.
- `pytest -q backend/tests/test_lifecycle.py backend/tests/test_engine.py`: **40 passed, 1 dependency deprecation warning**. This includes CIFAR-10/CIFAR-100 model paths, candidate checkpoint comparison, stop/recovery, decision/final evaluation/registration/serving, frozen lineage, and historical holdout report exclusion.
- Browser review used existing workspace data: desktop dark Runs, Compare, Decisions, Models; narrow light Investigations, Compare, Decisions, Models; optional Reproducibility navigation; Compare sorting; selected-run decision path. The browser's running backend had not reloaded the new release-list response, so its new source fields were verified through backend tests, not that live page.
- Notebook code cells parsed. Full execution was not performed because this environment lacks optional Jupyter/IPython, pandas, and matplotlib packages.

### Remaining work before calling the redesign complete

1. **CSS consolidation:** remove competing rules in `foundation.css`, `workspace-refresh.css`, `shell-components.css`, `application-components.css`, `theme-overrides.css`, `shape-system.css`, and `mlflow-design.css` by migrating each affected component to tokens or local styles. Check both themes after each removal. Acceptance: no screen depends on a last-file override to correct a broken earlier rule.
2. **Complete visual state matrix:** review Investigations, Runs, Compare, Decisions, Models, Search, and Reproducibility at desktop, tablet, and narrow widths in both themes, including long names, empty/loading/error/disabled states and open disclosures. Acceptance: controls, charts, and tables stay legible without page-wide horizontal overflow.
3. **Run a fresh browser journey:** create an investigation and run, observe live progress and stop a disposable run, compare two completed checkpoints on one image, record a decision, run the one final holdout, register/activate a version, serve a prediction, inspect the timeline/report. Use a dedicated test investigation to avoid consuming an existing one-time final evaluation. Acceptance: each step advances with a clear next action and persisted evidence agrees across pages.
4. **Verify the running backend after restart:** confirm the Models release list displays source approach, dataset, and frozen decision from the registration manifest in the actual browser. Acceptance: browser response and table match the backend fixture assertions.
5. **Run the notebook with optional analysis dependencies:** open it against the same storage directory and a real completed run; verify epoch table, configuration, checkpoint inspection, and final-evidence eligibility match the UI/report. Acceptance: no stale field names or exposed preselection holdout values.
6. **Finish keyboard and chart review:** inspect focus order/return from expanded chart and menus; verify every chart's point details and axis labels for one-point, flat, interrupted, and long series. Acceptance: no clipped plot or misleading missing-data line.

The redesign should be marked complete only when the acceptance criteria above and the dedicated journey all pass. The current passing build and backend tests do not establish that full result.
