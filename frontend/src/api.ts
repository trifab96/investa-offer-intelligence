import type { OfferDetail, OfferSummary } from "./types";
import type { PortfolioStats, PreviewOut } from "./types";

const BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export async function listOffers(): Promise<OfferSummary[]> {
  return json(await fetch(`${BASE}/offers`));
}

export async function getOffer(id: string): Promise<OfferDetail> {
  return json(await fetch(`${BASE}/offers/${id}`));
}

export async function getStatus(
  id: string,
): Promise<{ id: string; status: string; error: string | null }> {
  return json(await fetch(`${BASE}/offers/${id}/status`));
}

export async function uploadOffer(files: FileList): Promise<{ offer_id: string }> {
  const form = new FormData();
  Array.from(files).forEach((f) => form.append("files", f));
  return json(await fetch(`${BASE}/offers`, { method: "POST", body: form }));
}

export async function compareOffers(ids: string[]): Promise<any[]> {
  return json(await fetch(`${BASE}/compare?ids=${ids.join(",")}`));
}

export async function getPreview(id: string): Promise<PreviewOut> {
  return json(await fetch(`${BASE}/offers/${id}/preview`));
}

export async function getStats(): Promise<PortfolioStats> {
  return json(await fetch(`${BASE}/stats`));
}
