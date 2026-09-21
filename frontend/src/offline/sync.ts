import client from "../api/client";
import { getProducts, getCustomers, getUnits } from "../api/resources";
import {
  getQueuedSales, removeQueuedSale, updateQueuedSaleError,
  getQueuedStockMovements, removeQueuedStockMovement, updateQueuedStockMovementError,
  queueStockMovement as dbQueueStockMovement,
  getQueuedGenericRequests, removeQueuedGenericRequest, updateQueuedGenericRequestError,
  queueGenericRequest,
  cacheSet, cacheGet, type QueuedSale, type QueuedStockMovement, type QueuedGenericRequest,
} from "./db";
import type { Product, Customer, UnitOfMeasure } from "../api/types";

export type SyncStatus = "online" | "offline" | "syncing";

type Listener = (status: SyncStatus, pendingCount: number, lastSyncAt: string | null) => void;

// Manual override — lets someone deliberately work offline even with a
// real connection (e.g. a flaky connection they don't trust, or just
// wanting full control over when the app talks to the server), or force
// a reconnect attempt. Every real-connectivity check in this file and
// across the app should go through isOnline(), not navigator.onLine
// directly, so this override is respected everywhere consistently.
let manualOfflineMode = localStorage.getItem("sbos_manual_offline") === "true";

export function isOnline(): boolean {
  return navigator.onLine && !manualOfflineMode;
}

export function getManualOfflineMode(): boolean {
  return manualOfflineMode;
}

export function setManualOfflineMode(value: boolean): void {
  manualOfflineMode = value;
  localStorage.setItem("sbos_manual_offline", String(value));
  currentStatus = isOnline() ? "online" : "offline";
  emit();
  if (isOnline()) {
    refreshOfflineCache();
    processOutbox();
  }
}

let currentStatus: SyncStatus = isOnline() ? "online" : "offline";
let lastSyncAt: string | null = localStorage.getItem("sbos_last_sync") || null;
const listeners = new Set<Listener>();

function emit() {
  Promise.all([getQueuedSales(), getQueuedStockMovements(), getQueuedGenericRequests()]).then(([sales, movements, generic]) => {
    for (const l of listeners) l(currentStatus, sales.length + movements.length + generic.length, lastSyncAt);
  });
}

export function subscribeSyncStatus(listener: Listener): () => void {
  listeners.add(listener);
  emit();
  return () => listeners.delete(listener);
}

export function generateClientReference(): string {
  return `offline-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

/** Queues a stock movement (adjustment/opening-stock/damage/etc.) made
 * while offline. Called by the Inventory page when a submit fails due
 * to no connectivity — mirrors queueSale's contract exactly. */
export async function queueStockMovementOffline(payload: unknown): Promise<void> {
  const clientReference = generateClientReference();
  await dbQueueStockMovement({ clientReference, payload: { ...(payload as object), client_reference: clientReference }, queuedAt: new Date().toISOString() });
}

/** Queues any other write (expense, customer payment) made while
 * offline against a given API endpoint. Used by pages that don't
 * warrant their own dedicated outbox store — the endpoint must accept
 * a `client_reference` field for idempotent replay. */
export async function queueGenericOffline(endpoint: string, payload: unknown): Promise<void> {
  const clientReference = generateClientReference();
  await queueGenericRequest({
    clientReference, endpoint,
    payload: { ...(payload as object), client_reference: clientReference },
    queuedAt: new Date().toISOString(),
  });
}

/** Caches products/customers/units for offline POS use. Call this
 * whenever online (app load, after login, after reconnecting) — POS
 * reads from this cache automatically when a live fetch fails. */
export async function refreshOfflineCache(): Promise<void> {
  if (!isOnline()) return;
  try {
    const [products, customers, units] = await Promise.all([
      getProducts({ is_active: "true" }),
      getCustomers({ is_active: "true" }),
      getUnits(),
    ]);
    await cacheSet<Product[]>("products", products);
    await cacheSet<Customer[]>("customers", customers);
    await cacheSet<UnitOfMeasure[]>("units", units);
  } catch {
    // Best-effort — if this fails we just fall back to whatever was cached before.
  }
}

export const getCachedProducts = () => cacheGet<Product[]>("products");
export const getCachedCustomers = () => cacheGet<Customer[]>("customers");
export const getCachedUnits = () => cacheGet<UnitOfMeasure[]>("units");

/** Sends every queued offline sale and stock movement to the server.
 * Each carries its own client_reference, so a retried, interrupted
 * sync never posts the same thing twice (see backend
 * Sale.client_reference / StockMovement.client_reference). */
export async function processOutbox(): Promise<void> {
  if (!isOnline()) return;
  const [queuedSales, queuedMovements, queuedGeneric] = await Promise.all([
    getQueuedSales(), getQueuedStockMovements(), getQueuedGenericRequests(),
  ]);
  if (queuedSales.length === 0 && queuedMovements.length === 0 && queuedGeneric.length === 0) return;

  currentStatus = "syncing";
  emit();

  for (const item of queuedSales as QueuedSale[]) {
    try {
      await client.post("/sales/", item.payload);
      await removeQueuedSale(item.clientReference);
    } catch (err: any) {
      await updateQueuedSaleError(item.clientReference, err?.response?.data ? JSON.stringify(err.response.data) : String(err));
    }
  }

  for (const item of queuedMovements as QueuedStockMovement[]) {
    try {
      await client.post("/stock-movements/", item.payload);
      await removeQueuedStockMovement(item.clientReference);
    } catch (err: any) {
      await updateQueuedStockMovementError(item.clientReference, err?.response?.data ? JSON.stringify(err.response.data) : String(err));
    }
  }

  for (const item of queuedGeneric as QueuedGenericRequest[]) {
    try {
      await client.post(item.endpoint, item.payload);
      await removeQueuedGenericRequest(item.clientReference);
    } catch (err: any) {
      await updateQueuedGenericRequestError(item.clientReference, err?.response?.data ? JSON.stringify(err.response.data) : String(err));
    }
  }

  lastSyncAt = new Date().toISOString();
  localStorage.setItem("sbos_last_sync", lastSyncAt);
  currentStatus = isOnline() ? "online" : "offline";
  emit();
}

let initialized = false;
export function initSyncManager() {
  if (initialized) return;
  initialized = true;

  window.addEventListener("online", () => {
    currentStatus = isOnline() ? "online" : "offline";
    emit();
    if (isOnline()) {
      refreshOfflineCache();
      processOutbox();
    }
  });
  window.addEventListener("offline", () => {
    currentStatus = "offline";
    emit();
  });

  if (isOnline()) {
    refreshOfflineCache();
    processOutbox();
  }
}
