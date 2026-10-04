---
name: Chandra Asri Knowledge Hub
description: Every answer is a controlled safety document; signal bar first, coded claims, ruled source table.
colors:
  shell-green: "#12332a"
  shell-green-raised: "#1b4538"
  shell-text: "#b9ccc4"
  document-ground: "#f1f3f1"
  panel-white: "#ffffff"
  ink: "#17201d"
  muted-ink: "#4b5852"
  rule: "#c4ccc7"
  verified-green: "#1e7a49"
  caution-amber: "#d9a400"
  caution-ink: "#6f5300"
  alarm-red: "#c8322b"
  alarm-red-ink: "#a3241e"
  caution-wash: "#fbf3d8"
  alarm-wash: "#fbeceb"
  shell-wash: "#cfe3d8"
  muted-soft: "#7d8a84"
typography:
  display:
    fontFamily: "Public Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "44px"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.025em"
  headline:
    fontFamily: "Public Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "32px"
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "-0.025em"
  title:
    fontFamily: "Public Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 500
    lineHeight: 1.375
  body:
    fontFamily: "Public Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Public Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "0.08em"
  code:
    fontFamily: "JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, monospace"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "-0.01em"
rounded:
  xs: "2px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "28px"
components:
  signal-bar-verified:
    backgroundColor: "{colors.shell-green}"
    textColor: "{colors.panel-white}"
    padding: "10px 16px"
  signal-bar-caution:
    backgroundColor: "{colors.caution-amber}"
    textColor: "{colors.ink}"
    padding: "10px 16px"
  signal-bar-unverified:
    backgroundColor: "{colors.alarm-red}"
    textColor: "{colors.panel-white}"
    padding: "10px 16px"
  reference-chip:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.panel-white}"
    typography: "{typography.code}"
    rounded: "{rounded.xs}"
    height: "18px"
    padding: "0 4px"
  button-primary:
    backgroundColor: "{colors.shell-green}"
    textColor: "{colors.panel-white}"
    rounded: "{rounded.xs}"
    height: "40px"
    padding: "0 16px"
  button-primary-hover:
    backgroundColor: "{colors.shell-green-raised}"
  button-rail:
    backgroundColor: "{colors.shell-green}"
    textColor: "{colors.panel-white}"
    padding: "10px 12px"
  button-rail-hover:
    backgroundColor: "{colors.shell-green-raised}"
  panel-cell:
    backgroundColor: "{colors.panel-white}"
    textColor: "{colors.ink}"
    padding: "28px"
  panel-cell-hover:
    backgroundColor: "{colors.shell-green}"
    textColor: "{colors.panel-white}"
---

# Design System: Chandra Asri Knowledge Hub

## Overview

**Creative North Star: "The Safety Data Sheet"**

Every answer is a controlled document. A signal-word bar states how far to trust it before anything else is read, claims carry coded reference chips inline, and a ruled Sources table closes it so any claim is verified in one click. The visitor is a plant engineer confirming a spec, setpoint or failure history before acting, so the system is built for scanning and verification rather than persuasion.

The material is a cool document-white ground with white panels divided by 1px rules, square 2px corners, and no shadows. Structure is the visible ruled-cell armature itself. A deep safety-green shell carries the rail and the verified signal bar. State colours follow ISO 3864 logic and each has one job.

**Key Characteristics:**
- Signal word first, claims with codes second, source table last.
- Flat, ruled, square: depth comes from rules and tone, never shadow.
- One type family (Public Sans) on a strict scale; mono for every code, tag, revision and page.
- Colour is status, not decoration; amber means change or conflict, red means unverified or error.
- Hover inverts a ruled panel to shell green.

## Colors

A restrained safety-green and document-white palette; the only saturated hues are status signals.

### Primary
- **Shell Green** (`shell-green`): the rail, the verified signal bar, primary buttons, active toggle, hover-inversion of panels, icon strokes, and the Sources table header. Raised variant `shell-green-raised` is the hover/pressed tone on shell.
- **Shell Text** (`shell-text`): secondary text on the green shell and on inverted panels.

### Neutral
- **Document Ground** (`document-ground`): page canvas, table header strips and quiet fills.
- **Panel White** (`panel-white`): every panel, row and field.
- **Ink** (`ink`): body text, reference chips, strong borders on landing cells and controls, focus outline.
- **Muted Ink** (`muted-ink`): captions, labels, placeholders, secondary data.
- **Rule** (`rule`): every 1px divider and panel border.

### Status
- **Verified Green** (`verified-green`): approved or issued-for-operation marks only.
- **Caution Amber** (`caution-amber`): conflict, partial, or not-final: caution signal bar, diamond markers, not-final status. Text on light surfaces uses `caution-ink`.
- **Alarm Red** (`alarm-red`): unverified answers and errors only. Text on light uses `alarm-red-ink`.
- **Washes** (`caution-wash`, `alarm-wash`): pale fills behind caution/error notes and the active source row. `shell-wash` is the text-selection tint. `muted-soft` is for disabled/empty-state graphics only, never text.

### Named Rules
**The One Alert Rule.** Amber is reserved for conflict, partial, and not-final. Red is reserved for unverified and error. Neither is ever used for emphasis, branding or decoration.
**The Diamond Rule.** Every non-green state is marked with a rotated-square (GHS-style) diamond; green states use a plain filled diamond. Colour never carries status alone.

## Typography

**Display Font:** Public Sans (with ui-sans-serif, system-ui)
**Body Font:** Public Sans
**Label/Mono Font:** JetBrains Mono (with ui-monospace, Menlo)

**Character:** One grotesque family on a strict scale; hierarchy comes from size and weight, with 12px tracked caps for field labels and mono for anything an engineer might copy or cross-check.

### Hierarchy
- **Display** (700, 44px desktop / 32px mobile, 1.1): landing heading only.
- **Headline** (700, 32px, tight): page titles in the repository. Landing panel titles step to 26px bold.
- **Title** (500, 17px, snug): answer summary and landing subtitles.
- **Body** (400, 15px, 1.5): claims, table rows, descriptions; 14px (`text-sm`) for field values and controls; 13px for captions and excerpts.
- **Label** (600, 12px, 0.08em, uppercase): field names, table column heads, section strips, toggles. The signal word uses the same label style at 13px.
- **Code** (mono, 13px, -0.01em; 11px inside chips): tags, document numbers, revisions, pages, query ids, totals (22px, medium).

### Named Rules
**The Mono Means Reference Rule.** Mono is for identifiers and measured data only; running prose never uses it.
**The One Family Rule.** No second sans or serif. Add hierarchy through the scale above, not a new face.

## Layout

A ruled-cell grid: panels sit edge to edge, sharing 1px borders (top and left on the grid, right and bottom per cell) rather than floating with gaps. Landing is a max-width 5xl (1024px) column with left-aligned heading, a two-column panel grid from md, and a four-cell totals strip. Repository grids run 1, 2, then 3 columns at sm and lg. The answer document is a stack of full-width bands (signal bar, four-cell header dl, summary, claim rows, recommendations, Sources table) separated by rules; the Sources table collapses to a three-column row with a mono summary line below sm.

The app is a rail plus canvas: a 288px (w-72) green rail from lg (1024px) that collapses to a 48px strip and remembers the choice; below lg it becomes a slide-in drawer under a dark scrim with a green top bar. Card grids and tables respond to the width of their own container (container queries), so they adapt to the rail being open or closed. Spacing rhythm: row padding 10px 16px, panel padding 20-28px, 8px gaps in clusters, 32px above the main grid in the repository.

## Elevation & Depth

No shadows anywhere. Depth is conveyed by rules, tonal bands (ground strips over white panels), and the green shell against the light canvas. The only overlay treatment is the dark scrim behind the mobile drawer. State is shown by tone inversion and rings, never by lift.

### Named Rules
**The Flat Sheet Rule.** Surfaces are flat at rest and flat on hover. State changes swap fill (to shell green, ground, or pale amber), they never add shadow.

## Shapes

Square. The only radius is 2px (`rounded.xs`), used on reference chips and buttons. Panels, rows, inputs and bars are 0 radius with 1px borders in `rule` (or `ink` for controls and landing cells). The recurring silhouette is the 45-degree-rotated square diamond for status. No pills, no circles, no avatars.

## Components

### Signal Bar
Full-width band at the top of every answer: verified is shell green with white text, caution is amber with ink text and a bordered diamond containing "!", unverified is red with white text and the same diamond. Left: signal word in label style. Right: mono source count. Tone is derived from confidence and clarification state.

### Reference Chip
Ink square (18px tall, 2px radius) with white 11px mono: type code plus number (IL1, DS1, PM2). Inline after the claim's last word, kept on one line with it. Hover turns shell green; active chip is shell green with an ink ring. Clicking scrolls to and expands the matching Sumber row.

### Buttons
- **Primary:** shell-green fill, white 14px semibold, 40px tall, 2px radius; hover shell-green-raised; disabled becomes ground fill with a rule border and muted text.
- **Rail action:** transparent on shell with a 25% white border, white semibold text; hover raises to shell-green-raised.
- **Segmented toggle (Type/Plant):** 1px ink border group of label-style buttons; pressed is shell green with white text, idle is white with ground hover.

### Panels / Ruled Cells
White cells with 1px borders (ink on landing, rule in repository), square, padded 20-28px, with a 44-72px line icon (thin stroke, shell green). Hover inverts the whole cell to shell green with white text and shell-text descriptions.

### Inputs / Fields
White fill, 1px ink border, 14px text, leading line icon in muted ink. Focus is a 2px ink outline with 2px offset on the wrapper. Placeholder is muted ink.

### Header Fields (dl)
Four ruled cells (Equipment, Intent, Confidence, Query ID): label-style term over a 14px value; tags and ids in mono.

### Sources Table
Shell-green header strip in white label type, then a ground column-head row (Kode, Dokumen, Rev, Status, Hal) and ruled rows. Code is an ink chip, document id a mono underlined link, revision and page mono muted, status a diamond StatusMark. Rows with excerpts expand to a ground-filled quoted line.

### Status Mark
13px medium text with a 10px rotated-square: green diamond for Issued for Operation or Approved; amber diamond with caution-ink text for any other status.

### Navigation
Green rail with a 3px white rule over caps brand label, rail action, folder link, chat list (row actions revealed on hover or focus, always visible on touch), and New chat. Focus rings on shell are white.

## Do's and Don'ts

### Do:
- **Do** state the signal word before any answer content, and mark every non-green state with a diamond.
- **Do** give every claim an ink reference chip (type code + number) that resolves to a row in the Sources table.
- **Do** set tags, document numbers, revisions, pages and codes in JetBrains Mono.
- **Do** separate content with 1px `rule` borders and square corners (2px max).
- **Do** keep amber for conflict, partial and not-final, and red for unverified and error only.
- **Do** use Public Sans at the scale above; labels are 12px, 600, 0.08em, uppercase.
- **Do** keep focus visible: 2px ink outline, white on the shell.

### Don't:
- **Don't** use shadows, gradients, tinted rounded cards, pill badges or chat avatars.
- **Don't** use amber or red for decoration, hover, or branding.
- **Don't** convey status by colour alone; the diamond and the word must be present.
- **Don't** introduce a second typeface or set prose in mono.
- **Don't** label the same fact twice (a heading and a caption that repeat each other) except where a surface brief explicitly requires it.

## Drawn Symbols & Domain Views

**Symbol set** (`frontend/src/lib/symbols.ts`, rendered by `Symbol.svelte`): authored P&ID / ISA 5.1-style line symbols on a 48x48 grid, `currentColor`, 1.1-1.5 stroke, mitred joins, square caps. They replace stock icons for document types, equipment and the two landing entries (instrument bubble Q over A for Chatbot; stacked sheets with revision triangle for Repositori). Equipment symbols: pump, compressor, dryer, reactor, exchanger, control valve, valve, cooling tower, column, vessel. Chrome icons (menu, search, chevrons) remain a plain UI icon set. New symbols must be drawn in the same grid and weight, never imported.

**Instrument bubbles** follow ISA 5.1: function letters over loop number, mono, inside a ruled circle with a horizontal split line (`ProtectionDiagram`, `PidRegisterView`).

**Equipment page**: a nameplate (`EquipmentPlate`: symbol plate in shell green, large mono tag, ruled field cells) over the protection diagram, then instruments, components, and the document table. Without extracted interlock data the page shows an honest empty panel instead of a diagram.

**Protection diagram** (`ProtectionDiagram`): trip initiators as bubbles with real setpoint and voting, an OR logic block, and the effects (valves, pumps, DCS) as symbols; start permissives feed an AND block into the equipment. Selecting or hovering a trip dims everything that is not its path. SVG scales and pans horizontally below the container width where it stays legible.

**Per-type document views** (`views/`): Datasheet = ruled field sheet grouped by category; Interlock = cause-effect matrix (diamond marks) plus permissive table; P&ID = instrument register with bubbles; Maintenance = summary strip plus event list with a failures filter; OPL = ruled sections; Plot plan = field sheet. The extracted text always remains available under "Teks sumber" because citations point into it.

**Failure Memory** (`/failure-memory`): equipment select and symptom search in one ruled form, a standing "Historical evidence is not a diagnosis" notice (ink border, not amber, to keep the One Alert Rule), similar incidents as ruled rows with a labelled text-match meter, root-cause and fix lists, and a failure profile with a single-series bar list (shell green, direct count labels, no legend). Duplicate records of one incident are merged for display with every ID kept visible. Only equipment with maintenance records is selectable.

