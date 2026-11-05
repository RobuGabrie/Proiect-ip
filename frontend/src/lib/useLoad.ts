"use client";

import { useCallback, useEffect, useState } from "react";
import { errorMessage } from "./api";

export type Loaded<T> = {
  data: T | null;
  error: string;
  loading: boolean;
  reload: () => void;
};

/** Încarcă date de la API; `key` reia încărcarea când se schimbă filtrele. */
export function useLoad<T>(load: () => Promise<T>, key: string): Loaded<T> {
  const [state, setState] = useState<{ data: T | null; error: string; loadedKey: string | null }>({
    data: null,
    error: "",
    loadedKey: null,
  });
  const [attempt, setAttempt] = useState(0);
  const requestKey = `${key}#${attempt}`;

  useEffect(() => {
    let active = true;
    load()
      .then((data) => {
        if (active) setState({ data, error: "", loadedKey: requestKey });
      })
      .catch((error) => {
        if (active) setState((previous) => ({ ...previous, error: errorMessage(error), loadedKey: requestKey }));
      });
    return () => {
      active = false;
    };
    // `load` se schimbă la fiecare randare; `requestKey` decide când se reîncarcă.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestKey]);

  const reload = useCallback(() => setAttempt((value) => value + 1), []);

  return { data: state.data, error: state.error, loading: state.loadedKey !== requestKey, reload };
}
