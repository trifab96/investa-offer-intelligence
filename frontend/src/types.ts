export interface OfferSummary {
  id: string;
  subject: string | null;
  sender: string | null;
  status: string;
  score: number | null;
  band: string | null;
  is_known: boolean;
  objektart: string | null;
  ort: string | null;
  created_at: string;
}

export interface SubScore {
  name: string;
  value: number;
  weight: number;
  kind: "heuristic" | "llm";
  rationale: string | null;
  inputs: Record<string, unknown> | null;
}

export interface Driver {
  name: string;
  direction: "positive" | "negative";
  impact: number;
  detail: string | null;
}

export interface Scoring {
  score: number;
  band: string;
  asset_class: string | null;
  asset_class_label: string | null;
  subscores: SubScore[];
  top_drivers: Driver[];
  risk_penalty: number;
  rationale: string | null;
  risks: string[];
  opportunities: string[];
  metrics?: Record<string, unknown>;
  match?: Record<string, unknown>;
}

export interface PromptTrace {
  purpose: string;
  model: string;
  system: string;
  user: string;
  params: Record<string, unknown>;
  raw_response: string | null;
}

export interface DocumentOut {
  id: string;
  filename: string | null;
  doc_type: string;
  extracted_text: string | null;
  char_count: number;
}

export interface ReplyOut {
  id: string;
  language: string;
  subject: string | null;
  body: string | null;
  reason: string | null;
}

export interface OfferDetail {
  id: string;
  subject: string | null;
  sender: string | null;
  status: string;
  error: string | null;
  is_known: boolean;
  documents: DocumentOut[];
  extraction: Record<string, any> | null;
  enrichment: Record<string, any> | null;
  scoring: Scoring | null;
  score: number | null;
  band: string | null;
  prompt_trace: PromptTrace[] | null;
  replies: ReplyOut[];
  created_at: string;
}

export interface PreviewPage {
  filename: string;
  doc_type: string;
  page: number;
  image: string;
}

export interface PreviewOut {
  pages: PreviewPage[];
  note: string | null;
}

export interface PortfolioStats {
  total: number;
  done: number;
  processing: number;
  failed: number;
  known_duplicates: number;
  scored: number;
  avg_score: number | null;
  band_counts: Record<string, number>;
  score_histogram: number[];
  top_offers: OfferSummary[];
}
