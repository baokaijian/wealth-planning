---
version: alpha
name: Google Wealth Workspace
description: A Google Workspace inspired design system for a local wealth-planning dashboard.
colors:
  primary: "#1A73E8"
  primary-strong: "#174EA6"
  primary-container: "#E8F0FE"
  secondary: "#5F6368"
  tertiary: "#188038"
  neutral: "#F8FAFD"
  surface: "#FFFFFF"
  surface-variant: "#F1F3F4"
  on-surface: "#202124"
  outline: "#DADCE0"
  warning: "#F9AB00"
  error: "#D93025"
  purple: "#A142F4"
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: 0px
  headline-md:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: 700
    lineHeight: 1.35
    letterSpacing: 0px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: 0px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: 600
    lineHeight: 1.35
    letterSpacing: 0px
rounded:
  none: 0px
  sm: 4px
  md: 6px
  lg: 8px
  full: 999px
spacing:
  xs: 4px
  sm: 8px
  md: 12px
  lg: 16px
  xl: 24px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.surface}"
    rounded: "{rounded.md}"
    padding: 10px
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.primary}"
    rounded: "{rounded.md}"
    padding: 10px
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.lg}"
    padding: 18px
  nav-active:
    backgroundColor: "{colors.primary-container}"
    textColor: "{colors.primary-strong}"
    rounded: "{rounded.full}"
    padding: 10px
  app-background:
    backgroundColor: "{colors.neutral}"
    textColor: "{colors.on-surface}"
  alert-warning:
    backgroundColor: "{colors.warning}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.lg}"
    padding: 12px
  action-purple:
    backgroundColor: "{colors.purple}"
    textColor: "{colors.surface}"
    rounded: "{rounded.md}"
    padding: 10px
---

## Overview

Google Workspace clarity for a local wealth-planning tool: quiet surfaces, precise data hierarchy, and restrained financial state colors.

## Colors

Use blue for primary navigation and actions, green for cashflow or healthy states, yellow for valuation or caution, and red for risk or loss. Large surfaces stay neutral and bright.

## Typography

Use Inter with system fallbacks. Keep headings compact, preserve Chinese labels, and use tabular numbers for financial metrics.

## Layout

Prefer a fixed left navigation, sticky contextual header, dense form grids, and lightweight right-side analysis panels. Maintain responsive single-column behavior on small screens.

## Elevation & Depth

Use borders as the default separator. Elevation is subtle and reserved for sticky surfaces or focused interactive areas.

## Shapes

Cards use 8px radius, controls use 6px radius, and status badges use fully rounded pills.

## Components

Buttons, inputs, cards, tables, metric tiles, status badges, and Plotly charts should derive colors and spacing from the token set above.

## Do's and Don'ts

Do preserve IDs, events, calculation behavior, and local-only privacy messaging. Do not introduce decorative gradients, large shadows, marketing hero layouts, or business-logic changes.
