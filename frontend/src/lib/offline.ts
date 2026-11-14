/** Minimal IndexedDB queue for field reports captured without connectivity. */

const DB_NAME = "bhushakti-field";
const STORE = "report-queue";
const DB_VERSION = 1;

export interface QueuedReport {
  client_uuid: string;
  created_at: string;
  synced: boolean;
  server_id: number | null;
  error: string | null;
  payload: Record<string, unknown>;
}

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE, { keyPath: "client_uuid" });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function withStore<T>(mode: IDBTransactionMode, work: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  const db = await openDatabase();
  return new Promise<T>((resolve, reject) => {
    const tx = db.transaction(STORE, mode);
    const request = work(tx.objectStore(STORE));
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
    tx.oncomplete = () => db.close();
  });
}

export async function enqueueReport(payload: Record<string, unknown>): Promise<QueuedReport> {
  const entry: QueuedReport = {
    client_uuid: String(payload.client_uuid ?? crypto.randomUUID()),
    created_at: new Date().toISOString(),
    synced: false,
    server_id: null,
    error: null,
    payload,
  };
  await withStore("readwrite", (store) => store.put(entry));
  return entry;
}

export async function listQueuedReports(): Promise<QueuedReport[]> {
  const rows = await withStore<QueuedReport[]>("readonly", (store) => store.getAll() as IDBRequest<QueuedReport[]>);
  return rows.sort((a, b) => a.created_at.localeCompare(b.created_at));
}

export async function markReport(entry: QueuedReport): Promise<void> {
  await withStore("readwrite", (store) => store.put(entry));
}

export async function getMeta(): Promise<{ last_synced: string | null; device_id: string }> {
  const stored = localStorage.getItem("bhushakti-field-meta");
  if (stored) {
    try {
      return JSON.parse(stored);
    } catch {
      /* fall through */
    }
  }
  const meta = { last_synced: null, device_id: `field-${crypto.randomUUID().slice(0, 8)}` };
  localStorage.setItem("bhushakti-field-meta", JSON.stringify(meta));
  return meta;
}

export async function setLastSynced(): Promise<void> {
  const meta = await getMeta();
  localStorage.setItem("bhushakti-field-meta", JSON.stringify({ ...meta, last_synced: new Date().toISOString() }));
}
