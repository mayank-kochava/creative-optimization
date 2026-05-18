import axios from 'axios';

const client = axios.create({ baseURL: '/api' });

// --- Types ---

export interface Campaign {
  id: number;
  name: string;
  platform_tags: string[];
  creative_count: number;
  fatiguing_count: number;
  created_at: string;
  updated_at: string;
}

export interface AnalysisScores {
  hook_strength: number;
  cta_clarity: number;
  visual_quality: number;
  message_clarity: number;
  emotional_resonance: number;
  social_proof: number;
  brand_consistency: number;
}

export interface Analysis {
  scores: AnalysisScores;
  overall_score: number;
  persuasion_strategy: string;
  dominant_emotion: string;
  strengths: string[];
  weaknesses: string[];
  recommendations: string[];
  explanation: string;
  benchmark_percentile: number | null;
  status: 'complete' | 'degraded';
}

export interface Annotation {
  annotation_type: 'face' | 'text' | 'cta';
  bbox: { x: number; y: number; w: number; h: number };
  label: string | null;
  confidence: number;
}

export interface KPISummary {
  total_impressions: number;
  total_clicks: number;
  total_installs: number;
  total_spend: number;
  total_revenue: number;
  ctr: number | null;
  cvr: number | null;
  cpi: number | null;
  roas: number | null;
}

export interface Creative {
  id: number;
  campaign_id: number;
  filename: string;
  storage_path: string;
  format: string;
  width: number | null;
  height: number | null;
  duration_seconds: number | null;
  file_size_bytes: number;
  fatigue_status: 'healthy' | 'fatiguing' | 'insufficient_data';
  analysis: Analysis | null;
  annotations: Annotation[];
  kpi: KPISummary | null;
  created_at: string;
  updated_at: string;
}

export interface CreativeSummary {
  id: number;
  filename: string;
  format: string;
  width: number | null;
  height: number | null;
  fatigue_status: 'healthy' | 'fatiguing' | 'insufficient_data';
  overall_score: number | null;
  has_duplicate: boolean;
  created_at: string;
}

export interface UploadResponse {
  creative_id: number;
  duplicate_detected: boolean;
  duplicate_id: number | null;
  duplicate_type: string | null;
  hamming_distance: number | null;
  analysis_status: string;
}

export interface FatigueResponse {
  status: 'healthy' | 'fatiguing' | 'insufficient_data';
  daily_ctr: Array<{ date: string; ctr: number | null }>;
  threshold: number;
}

export interface DuplicatePair {
  id: number;
  creative_id_a: number;
  creative_id_b: number;
  hamming_distance: number;
  duplicate_type: string;
  detected_at: string;
}

// --- API calls ---

export const api = {
  getCampaigns: (): Promise<Campaign[]> =>
    client.get('/campaigns').then(r => r.data),

  getCampaign: (id: number): Promise<Campaign> =>
    client.get(`/campaigns/${id}`).then(r => r.data),

  createCampaign: (name: string, platform_tags: string[] = []): Promise<Campaign> =>
    client.post('/campaigns', { name, platform_tags }).then(r => r.data),

  getCampaignCreatives: (id: number, skip = 0, limit = 20): Promise<CreativeSummary[]> =>
    client.get(`/campaigns/${id}/creatives`, { params: { skip, limit } }).then(r => r.data),

  uploadCreative: (campaignId: number, file: File): Promise<UploadResponse> => {
    const form = new FormData();
    form.append('file', file);
    return client.post(`/campaigns/${campaignId}/creatives`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data);
  },

  getCreative: (id: number): Promise<Creative> =>
    client.get(`/creatives/${id}`).then(r => r.data),

  getFatigue: (id: number): Promise<FatigueResponse> =>
    client.get(`/creatives/${id}/fatigue`).then(r => r.data),

  getDuplicates: (id: number): Promise<DuplicatePair[]> =>
    client.get(`/creatives/${id}/duplicates`).then(r => r.data),
};
