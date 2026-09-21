import { openDB, type IDBPDatabase } from "idb";

const DB_NAME = "truvanta-offline";
const DB_VERSION = 3;

export interface QueuedSale {
  clientReference: string;
  payload: unknown;
  queuedAt: string;
  lastError?: string;
}

export interface QueuedStockMovement {
  clientReference: string;
  payload: unknown;
  queuedAt: string;
  lastError?: string;
}

export interface QueuedGenericRequest {
  clientReference: string;
  endpoint: string;
  payload: unknown;
  queuedAt: string;
  lastError?: string;
}

let dbPromise: Promise<IDBPDatabase> | null = null;

function getDb(): Promise<IDBPDatabase> {
  if (!dbPromise) {
    dbPromise = openDB(DB_NAME, DB_VERSION, {
      upgrade(db) {
        if (!db.objectStoreNames.contains("outbox_sales")) {
          db.createObjectStore("outbox_sales", { keyPath: "clientReference" });
        }
        if (!db.objectStoreNames.contains("outbox_stock_movements")) {
          db.createObjectStore("outbox_stock_movements", { keyPath: "clientReference" });
        }
        if (!db.objectStoreNames.contains("outbox_generic")) {
          db.createObjectStore("outbox_generic", { keyPath: "clientReference" });
        }
        if (!db.objectStoreNames.contains("cache")) {
          db.createObjectStore("cache");
        }
      },
    });
  }
  return dbPromise;
}

// --- Outbox: sales made while offline, waiting to sync ---

export async function queueSale(sale: QueuedSale): Promise<void> {
  const db = await getDb();
  await db.put("outbox_sales", sale);
}

export async function getQueuedSales(): Promise<QueuedSale[]> {
  const db = await getDb();
  return db.getAll("outbox_sales");
}

export async function removeQueuedSale(clientReference: string): Promise<void> {
  const db = await getDb();
  await db.delete("outbox_sales", clientReference);
}

export async function updateQueuedSaleError(clientReference: string, error: string): Promise<void> {
  const db = await getDb();
  const existing = await db.get("outbox_sales", clientReference);
  if (existing) await db.put("outbox_sales", { ...existing, lastError: error });
}

// --- Outbox: stock adjustments made while offline ---

export async function queueStockMovement(movement: QueuedStockMovement): Promise<void> {
  const db = await getDb();
  await db.put("outbox_stock_movements", movement);
}

export async function getQueuedStockMovements(): Promise<QueuedStockMovement[]> {
  const db = await getDb();
  return db.getAll("outbox_stock_movements");
}

export async function removeQueuedStockMovement(clientReference: string): Promise<void> {
  const db = await getDb();
  await db.delete("outbox_stock_movements", clientReference);
}

export async function updateQueuedStockMovementError(clientReference: string, error: string): Promise<void> {
  const db = await getDb();
  const existing = await db.get("outbox_stock_movements", clientReference);
  if (existing) await db.put("outbox_stock_movements", { ...existing, lastError: error });
}

// --- Reference-data cache: products/customers/units for offline POS use ---

export async function cacheSet<T>(key: string, value: T): Promise<void> {
  const db = await getDb();
  await db.put("cache", value, key);
}

export async function cacheGet<T>(key: string): Promise<T | undefined> {
  const db = await getDb();
  return db.get("cache", key);
}

// --- Generic outbox: any other write (expenses, customer payments) made while offline ---

export async function queueGenericRequest(req: QueuedGenericRequest): Promise<void> {
  const db = await getDb();
  await db.put("outbox_generic", req);
}

export async function getQueuedGenericRequests(): Promise<QueuedGenericRequest[]> {
  const db = await getDb();
  return db.getAll("outbox_generic");
}

export async function removeQueuedGenericRequest(clientReference: string): Promise<void> {
  const db = await getDb();
  await db.delete("outbox_generic", clientReference);
}

export async function updateQueuedGenericRequestError(clientReference: string, error: string): Promise<void> {
  const db = await getDb();
  const existing = await db.get("outbox_generic", clientReference);
  if (existing) await db.put("outbox_generic", { ...existing, lastError: error });
}
