# Cadence Design System & Visual Guidelines

This document details the visual identity, branding patterns, color system, and responsive layout guidelines for Cadence's developer portals, merchant dashboards, and customer portals.

---

## 1. Design Aesthetics & Visual Identity

Cadence uses a **premium, content-first minimalist dark design language** constructed purely with semantic HTML5 and vanilla CSS. Moving background animations, glowing neon radial gradients, and decorative emojis have been intentionally omitted in favor of clean spacing, sharp contrast margins, and readable geometric typography.

---

## 2. Palette & Color System

The palette relies on a high-contrast dark scheme with semantic accents.

```css
:root {
    --bg-dark:            #0a0b0d;   /* Core page background */
    --bg-card:            rgba(18, 20, 26, 0.95); /* Surfaces, dashboard cards */
    --border-color:       rgba(255, 255, 255, 0.06); /* Subtle separators and card bounds */
    
    --text-primary:       #F3F4F6;   /* Body text, main headers */
    --text-secondary:     #9CA3AF;   /* Muted labels, secondary descriptions */
    
    --primary:            #FF6B00;   /* Brand highlight. Prominent CTA buttons */
    --primary-hover:      #FF8533;   /* Accent hover state */
    
    --success:            #10B981;   /* Active subscriptions, successful payments */
    --warning:            #F59E0B;   /* Past due invoices, card token warnings */
    --danger:             #EF4444;   /* Revoked tokens, cancelled subscriptions, errors */
}
```

### Contrast Compliance
*   **WCAG AA Compliance:** Text-to-background contrast ratios are kept at `4.5:1` or higher.
*   **Status Badges:** Muted color overlays are styled as low-opacity fills paired with high-saturation text (e.g., `rgba(16, 185, 129, 0.1)` background with `#34D399` text) to stand out without causing visual fatigue.

---

## 3. Typography & Font Pairing

A dual font system is implemented to separate brand actions from content reading:

*   **Headings & Action Items:** **Outfit** (variable weights 400 to 800) is locked for prominent headers, modal titles, sidebar navigation elements, and button text, providing a clean tech-forward look.
*   **Body Content & Metadata:** **Sora** (weights 300 to 700) is paired for standard descriptions, paragraphs, form labels, card contents, and table cell text.
*   **Monospace Columns:** Fixed-width browser fonts are enforced for developer credentials, prefix keys, timestamp strings, and currency values to maintain alignment and prevent layout shifts.

---

## 4. Responsive Layouts & Horizontal Scroll Prevention

To prevent horizontal scrolls across desktop, tablet, and mobile displays, layouts automatically reflow and hide secondary metadata:

### Auto-Fit Metric Grids
Dashboard overview cards automatically wrap between 1, 2, and 4 columns depending on the viewport width using a fluid container definition:
```css
.metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
    gap: 1.5rem;
}
```

### Table Column Hiding
Table lists are kept concise by dropping less critical developer metadata columns using media breakpoints.

1.  **Mobile Hiding (`.hide-mobile` < 768px):** Hides timestamps, secondary actions, and transaction reference fields.
2.  **Tablet Hiding (`.hide-tablet` < 1100px):** Hides API key labels, limit metrics, and auxiliary billing data.

```css
@media (max-width: 768px) {
    .hide-mobile {
        display: none !important;
    }
}
@media (max-width: 1100px) {
    .hide-tablet {
        display: none !important;
    }
}
```

### Sidebar Transition
*   **Desktop:** Positioned as a sticky left-rail panel (`width: 250px; position: sticky; top: 100px;`).
*   **Mobile (< 900px):** Transitions to a horizontal scrolling navigation bar at the top of the main layout container.

---

## 5. Self-Service Customer Portal

The subscriber-facing portal page is styled as a standalone interface:
*   Extends zero shared base dashboard templates to remove merchant headers, navigation sidebars, and footers.
*   Uses a single central card container centered on a solid `#0a0b0d` background.
*   Presents a physical card mockup representation indicating tokenized credit card states.
