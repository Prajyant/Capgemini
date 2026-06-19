/**
 * Demo recipient override.
 *
 * Lets the presenter route every outgoing email (Compose Email, Approve,
 * Sequence step send) to their own inbox during a live pitch, without
 * editing each modal individually.
 *
 * The value is persisted in localStorage so it survives reloads. A simple
 * window event lets components observe changes without prop drilling.
 */
const KEY = "demo:recipient_override";
const EVENT = "demo:recipient_override:changed";

export function getDemoRecipient(): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(KEY) || "";
}

export function setDemoRecipient(value: string): void {
  if (typeof window === "undefined") return;
  const trimmed = value.trim();
  if (trimmed) {
    window.localStorage.setItem(KEY, trimmed);
  } else {
    window.localStorage.removeItem(KEY);
  }
  window.dispatchEvent(new CustomEvent(EVENT));
}

export function onDemoRecipientChange(handler: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  window.addEventListener(EVENT, handler);
  // Cross-tab updates fire `storage`.
  const storageHandler = (e: StorageEvent) => {
    if (e.key === KEY) handler();
  };
  window.addEventListener("storage", storageHandler);
  return () => {
    window.removeEventListener(EVENT, handler);
    window.removeEventListener("storage", storageHandler);
  };
}
