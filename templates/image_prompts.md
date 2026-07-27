# Image Generation Prompts

This document describes how the image generator builds a **consistent** 30-image
photo package for a property using the Krea 2 Large model on Replicate.

Prompts are **not** hand-authored from this file — they are generated at runtime
in [`lambdas/image_generator/handler.py`](../lambdas/image_generator/handler.py).
This document is the reference for the shot list and the prompt structure.

## Pipeline

1. **Architectural concept (Haiku)** — a single pass establishes one concrete
   visual identity for the property so all 30 images depict the *same* building.
   The concept is a JSON object with these keys:

   - `architectural_style` — short style label (e.g. "contemporary garden-style craftsman")
   - `exterior_materials` — consistent siding/brick/stone/trim materials and colors
   - `roofline` — consistent roof type/pitch (garden-style) or parapet/roofline (high-rise)
   - `window_style` — consistent window/balcony style
   - `color_palette` — 2–4 consistent exterior colors
   - `landscaping_theme` — consistent plantings, hardscape, terrain
   - `site_features` — recurring site details (lighting, signage style, walkway paving)

2. **Structured prompts (Sonnet)** — all 30 prompts are generated in a single
   call, each threaded through the shared concept above, using the exact
   structure below.

3. **Rendering (Krea 2 Large)** — each assembled prompt is sent to
   `krea/krea-2-large` at `creativity: "low"` to minimize drift and keep the
   package internally consistent.

## Prompt structure

Every prompt uses these seven section headers, in this exact order:

```
Subject: [one line — the primary subject and setting type]

Architecture details: [comma-separated structural/material features — building materials, window types, rooflines, structural elements]

Landscaping: [comma-separated — vegetation, hardscape, terrain, foreground elements]

Lighting/atmosphere: [comma-separated — time of day, sky condition, light quality, season indicators]

Camera: [comma-separated — angle, height, lens characteristics, composition notes]

Style tags: [comma-separated — 4-6 short descriptive tags for overall photographic/artistic style]

Negative prompt suggestions: [comma-separated — 4-6 things to avoid: common generation artifacts, distortions, or unwanted elements specific to this image]
```

### Structuring rules

- Reuse the **same** architectural materials, colors, rooflines, and landscaping
  theme from the shared concept in every prompt.
- Never transcribe legible text, signage, logos, or heraldry — describe them
  generically (e.g. "carved wooden sign", not the words on it).
- Do not identify or name real people — describe figures only by pose, clothing,
  and position.
- Do not guess at real-world proper nouns; describe building types generically.
- Keep every section to visual, physically observable detail only.
- Every section must be present, even if brief.

> **Note on negative prompts:** Krea 2 Large has no separate `negative_prompt`
> API field. The "Negative prompt suggestions" section is kept inline as part of
> the single assembled prompt string.

## Shot list (30 images)

Each shot below is generated as its own structured prompt. The generator returns
one object per shot with `filename`, `description`, the seven structured section
fields, and an assembled `prompt` string.

### Exterior Views (6 images)

1. **aerial_view.jpg** — Aerial view of the community: buildings, landscaped grounds, parking areas.
2. **front_entrance.jpg** — Main entrance and leasing office with generic signage and landscaping.
3. **building_exterior_1.jpg** — Building exterior showing siding, roofing, balconies, walkways.
4. **building_exterior_2.jpg** — Alternate building angle showing covered parking and breezeway.
5. **parking_area.jpg** — Parking area with striped asphalt and covered/uncovered spaces.
6. **site_overview.jpg** — Wide-angle overview of multiple buildings around courtyards.

### Amenity Views (6 images)

7. **pool_area.jpg** — Resort-style swimming pool with lounge chairs and deck.
8. **fitness_center.jpg** — Modern fitness center with cardio and weight equipment.
9. **clubhouse_exterior.jpg** — Clubhouse exterior with covered patio and landscaping.
10. **clubhouse_interior.jpg** — Clubhouse lounge with modern furniture and kitchen area.
11. **dog_park.jpg** — Fenced dog park with agility equipment and benches.
12. **business_center.jpg** — Business center with workstations and conference table.

### Unit Interior Views (12 images)

13. **studio_living.jpg** — Studio apartment, open floor plan, modern finishes.
14. **1br_living.jpg** — One-bedroom living room, open to kitchen, large windows.
15. **1br_kitchen.jpg** — One-bedroom kitchen with stone counters and stainless appliances.
16. **1br_bedroom.jpg** — One-bedroom bedroom with large window and closet.
17. **2br_living.jpg** — Two-bedroom living room, open concept with dining area.
18. **2br_kitchen.jpg** — Two-bedroom kitchen with island and modern cabinetry.
19. **2br_master_bedroom.jpg** — Two-bedroom master bedroom with en-suite entrance.
20. **2br_bathroom.jpg** — Modern bathroom with double vanity and tiled shower.
21. **3br_living.jpg** — Spacious three-bedroom living room with premium finishes.
22. **3br_kitchen.jpg** — Three-bedroom kitchen with large island and premium appliances.
23. **3br_master_suite.jpg** — Three-bedroom master suite with sitting area and en-suite.
24. **3br_secondary_bedroom.jpg** — Secondary bedroom with closet and natural light.

### Site and Surroundings (6 images)

25. **street_view.jpg** — Street-level view of the community entrance and access.
26. **landscaping_detail.jpg** — Landscaping detail: mature trees, flower beds, walking paths.
27. **courtyard.jpg** — Interior courtyard with seating and walkways between buildings.
28. **mail_area.jpg** — Centralized mail kiosk with package lockers, covered and well-lit.
29. **laundry_facility.jpg** — Community laundry facility with commercial machines and folding tables.
30. **maintenance_building.jpg** — Maintenance and storage area, clean and well-organized.
