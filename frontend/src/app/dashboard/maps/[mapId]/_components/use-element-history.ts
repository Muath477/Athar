"use client";

import { useCallback, useState } from "react";
import { NO_PENDING, type Pending } from "@/lib/elements";

type History = { past: Pending[]; present: Pending; future: Pending[] };

const FRESH: History = { past: [], present: NO_PENDING, future: [] };

export function useElementHistory() {
  const [history, setHistory] = useState<History>(FRESH);

  const change = useCallback((update: (current: Pending) => Pending) => {
    setHistory((current) => {
      const next = update(current.present);
      if (next === current.present) return current;
      return { past: [...current.past, current.present], present: next, future: [] };
    });
  }, []);

  const undo = useCallback(() => {
    setHistory((current) => {
      if (current.past.length === 0) return current;
      return {
        past: current.past.slice(0, -1),
        present: current.past[current.past.length - 1],
        future: [...current.future, current.present],
      };
    });
  }, []);

  const redo = useCallback(() => {
    setHistory((current) => {
      if (current.future.length === 0) return current;
      return {
        past: [...current.past, current.present],
        present: current.future[current.future.length - 1],
        future: current.future.slice(0, -1),
      };
    });
  }, []);

  const reset = useCallback(() => setHistory(FRESH), []);

  return {
    pending: history.present,
    canUndo: history.past.length > 0,
    canRedo: history.future.length > 0,
    change,
    undo,
    redo,
    reset,
  };
}
