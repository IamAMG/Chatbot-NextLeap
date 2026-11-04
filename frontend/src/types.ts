export type PipelineRow = {
  document_id?: number;
  source: string;
  content: string;
  content_hash?: string;
  title?: string | null;
  author?: string | null;
  date?: string;
  votes?: number;
  url?: string | null;
  cleaning_status: string;
  removal_reason?: string | null;
  processed_by_llm?: number;
  behavioral_trigger?: string | null;
  sentiment_polarity?: number | null;
  sentiment_label?: string | null;
  emotional_intensity?: number | null;
  segment_proxy_ticket?: string | null;
  segment_proxy_tenure?: string | null;
  retention_dropoff_bucket?: string | null;
  opportunity_score?: number | null;
  created_at?: string;
  synced_to_supabase?: number;
  link_status?: string | null;
  link_checked_at?: string | null;
};

export type Cluster = {
  trigger: string;
  display: string;
  share_pct: number;
  row_count: number;
  avg_sentiment_polarity: number;
  avg_emotional_intensity: number;
  dominant_ticket: string;
  dominant_tenure: string;
  months_1_to_3_pct: number;
  months_6_to_8_pct: number;
  months_10_to_12_pct: number;
  opportunity_score: number;
  recommended_intervention: string;
  quotes: Array<{ text: string; source: string; dropoff_window: string }>;
};

export type OpportunityData = {
  total_tagged_rows: number;
  clusters: Cluster[];
  top_cluster: Cluster | null;
};

export type SyncBanner = {
  rows_scanned?: number;
  rows_inserted?: number;
  provider?: string;
  supabase?: string;
  message?: string;
};

export type View = "sheet" | "dashboard" | "evidence";

export type GoldenRow = {
  id: string;
  source: string;
  content: string;
  title?: string | null;
  author?: string | null;
  date?: string | null;
  votes?: number;
  url?: string | null;
  expected_behavioral_trigger?: string | null;
  expected_sentiment_label?: string | null;
  expected_segment_proxy_ticket?: string | null;
  expected_retention_dropoff_bucket?: string | null;
  expected_opportunity_min?: number;
  expected_opportunity_max?: number;
  evidence_category?: string;
  is_noise?: boolean;
};

export type EvidenceQuestion = {
  id: string;
  category: string;
  area: string;
  question: string;
  expected: string;
  test: string;
};

export type EvidenceCategory = {
  id: string;
  name: string;
  description: string;
};

export type EvidenceTestResult = {
  id: string;
  source: string;
  content: string;
  category: string;
  expected_trigger?: string | null;
  actual_trigger?: string | null;
  expected_sentiment?: string | null;
  actual_sentiment?: string | null;
  trigger_match?: boolean;
  sentiment_match?: boolean;
  passed: boolean;
  is_noise: boolean;
  reason?: string | null;
};

export type EvidenceCategorySummary = {
  category_id: string;
  category_name: string;
  pass: number;
  fail: number;
  total: number;
  pass_rate: number;
};

export type EvidenceLogData = {
  categories: EvidenceCategory[];
  golden_rows: GoldenRow[];
  questions: EvidenceQuestion[];
};

export type GoldenTestResponse = {
  status: string;
  total_rows: number;
  pass_count: number;
  fail_count: number;
  pass_rate: number;
  threshold: number;
  overall_pass: boolean;
  results: EvidenceTestResult[];
  category_summary: EvidenceCategorySummary[];
};

export type SourceFilter = "All Sources" | "Reddit" | "Google Play" | "App Store" | "YouTube" | "TradingQ&A" | "X" | "ChatGPT" | "Gemini";

export type StatusFilter = "clean" | "noise" | "all";
