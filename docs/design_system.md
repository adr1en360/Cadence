# Cadence Design System & Theme Colors

This document defines the branding guidelines, visual identity, and color system for Cadence's developer portal and merchant dashboard.

---

## Brand Colors

Cadence's theme is inspired by Nomba's warm financial yellow (`#F5A623`) but is shifted to a darker, warmer orange palette to create a distinct identity.

```css
:root {
    --cadence-orange:     #F26419;   /* Primary accent. Warm, energetic, action */
    --cadence-orange-dim: #C94E0F;   /* Hover states, active sidebar items */
    --cadence-black:      #0D0D0D;   /* Dark backgrounds, sidebar panel */
    --cadence-surface:    #1A1A1A;   /* Cards, code block containers */
    --cadence-white:      #F7F7F5;   /* Body text on dark, page bg on light */
    --cadence-muted:      #6B6B6B;   /* Secondary text, inactive nav items */
}
```

---

## Typography

- **Headings & Logo**: `Outfit` (sans-serif)
- **Body copy**: `Plus Jakarta Sans` or `Inter` (sans-serif)
- **Monospace Code blocks**: `Fira Code` or `SF Mono`

---

## Page Layout & Shell

Every developer portal page follows a clean three-column structure:

1. **Left Sidebar (Navigation)**:
   - Fixed, scrollable independently.
   - Background: `--cadence-black` (`#0D0D0D`).
   - Displays all page links. The active page is highlighted using `--cadence-orange` (`#F26419`).

2. **Center Panel (Content Area)**:
   - Background: `--cadence-white` (`#F7F7F5`).
   - Left border/pushed offset: `256px` (spacing out from the fixed sidebar).
   - Serves the core markdown/documentation content.

3. **Right Panel (Table of Contents)**:
   - Dynamic anchor-based outline to jump between sections on the page.
   - Hidden on smaller screens.
