// src/utils/storage.js
import { INITIAL_STATE } from '../constants.js';

const STORAGE_KEY = 'WEALTH_PLANNING_LOCAL_STORAGE_V1';

export function loadStateFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return INITIAL_STATE;
    }
    const parsed = JSON.parse(raw);
    return {
      board: { ...INITIAL_STATE.board, ...(parsed.board || {}) },
      health: { ...INITIAL_STATE.health, ...(parsed.health || {}) },
      insurance: { ...INITIAL_STATE.insurance, ...(parsed.insurance || {}) },
      debt: { ...INITIAL_STATE.debt, ...(parsed.debt || {}) },
      pension: { ...INITIAL_STATE.pension, ...(parsed.pension || {}) },
      property: { ...INITIAL_STATE.property, ...(parsed.property || {}) },
      stress: { ...INITIAL_STATE.stress, ...(parsed.stress || {}) },
      behavior: { ...INITIAL_STATE.behavior, ...(parsed.behavior || {}) },
      thermometer: { ...INITIAL_STATE.thermometer, ...(parsed.thermometer || {}) },
      goals: Array.isArray(parsed.goals) ? parsed.goals : INITIAL_STATE.goals
    };
  } catch (err) {
    console.error('Failed to load state from localStorage:', err);
    return INITIAL_STATE;
  }
}

export function saveStateToStorage(state) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch (err) {
    console.error('Failed to save state to localStorage:', err);
  }
}

export function resetStorageToDefault() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (err) {
    console.error('Failed to reset localStorage:', err);
  }
  return INITIAL_STATE;
}
