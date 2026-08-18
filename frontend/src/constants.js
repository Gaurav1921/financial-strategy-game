/**
 * Frontend-side copies of fixed game constants that the backend also
 * defines (`backend/app/core/constants.py`). Kept here because a single
 * two-service project isn't worth a shared-package build step for a
 * handful of literals; if these ever drift, the backend is the source of
 * truth (see `docs/GAMEPLAY.md`).
 */

export const INDUSTRIES = [
  'Healthcare',
  'Technology',
  'Pharma',
  'Energy',
  'Financial Services',
  'Consumer Retail',
  'Agriculture',
  'Manufacturing',
  'Media & Entertainment',
  'Property',
]

export const MIN_PLAYERS = 3
export const MAX_PLAYERS = 10

export const REAL_ESTATE_PURCHASE_COST = 0.97
export const REAL_ESTATE_LIQUIDATION_HAIRCUT = 0.85
export const GOLD_LIQUIDATION_HAIRCUT = 0.95

export const COMPANY_COLORS = [
  '#c0392b',
  '#d68910',
  '#b7950b',
  '#1e8449',
  '#148f77',
  '#2874a6',
  '#5b2c6f',
  '#922b6f',
]

export const SESSION_STORAGE_KEY = 'hostileLedger.session'
