---
trigger: always_on
---

# Skill: Anti-Slop Design Direction

## Purpose

Generate interfaces that look intentionally designed by a strong product or editorial designer, not like the average AI-generated SaaS landing page.

This skill should be applied whenever creating websites, dashboards, apps, landing pages, presentations, UI components, or visual systems.

---

## Core Principle

**Replace generality with a decision.**

Never use vague instructions such as “modern,” “clean,” “minimal,” or “professional” as the primary design direction.

Every design must anchor itself in **specific references, constraints, typography, spacing systems, and hierarchy decisions**.

---

# Rules

## 1. Always Anchor to a Specific Reference

Do not interpret “modern” broadly.

Use a concrete visual reference such as:

* Linear product marketing (late 2024)
* Stripe editorial
* Apple product pages
* Swiss International Style posters
* Aesop retail branding
* Notion marketing
* Monocle magazine layouts
* 2003 Wired editorial design
* Braun industrial design
* Dieter Rams product principles

State the reference explicitly before generating any design.

Example:

“Treat this interface like a Linear product page from late 2024 — strong sans-serif typography, generous negative space, thin separators, restrained color usage, and one dominant call-to-action.”

---

## 2. Declare Forbidden Patterns

Before generating, create a short **Forbidden** section.

Example:

Forbidden:

* Inter
* Roboto
* Open Sans
* Purple-to-indigo gradients
* Glassmorphism by default
* Three-up feature card rows on white
* Oversized rounded pills everywhere
* “Transform your workflow” style copy
* Soft floating shadows
* Generic startup illustrations

Use hard borders, restrained color, and intentional spacing instead.

---

## 3. Use Curated Design Choices

Never allow typography, color, or layout to be chosen arbitrarily.

Select from a curated set.

### Typography

Examples:

* Neue Haas Grotesk
* Suisse Intl
* IBM Plex Sans
* Geist
* GT America
* Canela
* Editorial New
* Freight Display

### Palette

Choose a restrained palette such as:

* Bone / Charcoal / Olive
* Slate / White / Black
* Cream / Forest / Brass
* Navy / Stone / Copper
* Off-white / Graphite / Electric Blue

### Style Direction

Examples:

* Swiss editorial
* Brutalist UI
* Japanese minimal
* Industrial product design
* Luxury editorial
* Technical documentation aesthetic
* Museum signage

---

## 4. Force One Dominant Visual Decision

Every screen must have **one thing that is intentionally louder than everything else**.

Examples:

* 96px editorial headline
* Oversized product render
* Full-bleed photography
* Monospaced data wall
* Massive numeric KPI
* Architectural whitespace

Everything else must become quiet.

If multiple elements compete equally, simplify the composition.

---

## 5. Specify the Spatial System

Do not rely on default spacing.

Define the layout grid.

Example:

Layout:

* 12-column grid
* 80px desktop gutters
* 8px base spacing system
* Vertical rhythm in multiples of 24px
* 1px separators instead of shadows
* Asymmetric composition preferred over centered symmetry
* Maximum content width 1200px

Whitespace is a design element, not empty space.

---

## 6. Establish a Brand Voice First

Write copy before designing.

Choose one voice:

* Terse and confident
* Editorial and intelligent
* Clinical and data-led
* Playful and self-aware
* Technical and precise
* Luxury and understated

The layout should reinforce the voice.

---

## 7. Prefer Removal Over Addition

After generating a design, perform a **de-slop pass**.

Ask:

* What can be deleted?
* Which section feels generic?
* Which card exists only because landing pages usually have cards?
* Which gradient is decorative rather than communicative?

Remove unnecessary elements until the design still feels strong with fewer components.

A page that survives subtraction is usually a better page.

---

# Required Output Structure

For every design request, respond in this order:

1. **Reference**
2. **Forbidden**
3. **Typography**
4. **Palette**
5. **Layout**
6. **Hierarchy**
7. **Voice**
8. **Design Generation**
9. **De-slop Pass**

---

# Example

Reference:
Linear product marketing (late 2024) mixed with Swiss editorial typography.

Forbidden:
Inter, purple gradients, feature-card grids, floating shadows.

Typography:
Canela for display headlines, Suisse Intl for UI text.

Palette:
Bone, graphite, muted olive.

Layout:
12-column grid, asymmetric hero, 80px gutters.

Hierarchy:
92px headline is the only dominant element.

Voice:
Terse, confident, slightly technical.

Then generate the interface.

---

# Meta Rule

Whenever a prompt contains words such as **modern, clean, minimal, premium, sleek, aesthetic, professional, startup, futuristic, or beautiful**, automatically convert those vague adjectives into **specific design decisions** before producing any visual output.

Never produce the average of the web.

Produce something that looks intentionally art-directed.
