---
version: 1
slug: "frontend-src-routes-page-svelte"
primary_target: "frontend/src/routes/+page.svelte"
related_targets: []
---

# Surface brief: whole app (landing, chat, repository)

Mode: Operate. Visitor: plant engineer verifying a spec, setpoint or failure history before acting.

## Direction contract

THESIS: Every answer is a controlled safety document. A signal-word bar states how far to trust it, claims carry coded reference chips, and a ruled source table closes it. It refuses the SaaS default of tinted rounded cards, soft shadows, gradient hero, pill badges and chat avatars.

OWN-WORLD: Cool document-white ground (#F1F3F1) with white panels and 1px rules (#C4CCC7), square corners (2px), no shadows. Deep safety-green shell (#12332A) for the rail and the verified signal bar. ISO 3864 state colours with real jobs: green = verified/approved, caution amber (#D9A400, text #6F5300 on light) = conflict, partial or not-final, red (#C8322B) = unverified/error only. A GHS-style diamond marks every non-green signal. Public Sans only, on a strict scale, caps labels at 12px tracked; JetBrains Mono tabular for tags, document numbers, revisions, pages and reference codes. Reference chips are ink squares with a type code + number (IL1, DS1, PM2).

STORY: The engineer reads the signal word first, then the claims with their codes inline, and verifies any claim in one click against the numbered Sumber table (code, document, revision, status, page).

FIRST VIEWPORT: Landing: left-aligned 40px heading "Selamat Datang di Chandra Asri Knowledge Hub"; two flat ruled panels (Chatbot, Repositori Pengetahuan) each with a 72px line icon, caps subtitle, description, inverting to shell green on hover; a one-line strip of live totals (dokumen, final, belum final, peralatan). Chat: green rail with + Tambah Dokumen, folder link, chat list, Chat baru; canvas shows the question as a dark block and the answer as a document: signal bar, header fields (peralatan, intent, keyakinan), summary, ruled claim rows with chips, recommendations, Sumber table. Repository: green rail tree, Tipe/Plant switch, ruled cell grid, status-ranked document table.

FORM: Safety Data Sheet (assigned direction, seed key dca50ebf). Raises: one alert colour strictly for change/conflict (Gate Board), visible ruled-cell armature (Construction Grid), tabular mono data (Datamatics), nothing labelled twice (Catalog Sleeve), one type family on a strict scale (Bitmap Specimen).

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
