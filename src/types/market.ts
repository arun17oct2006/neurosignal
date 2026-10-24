export type SignalType = "STRONG_BUY" | "STRONG_SELL" | "NEUTRAL";

export interface UserSession {
  user_id: string;
  email: string;
  authenticated_via: "magic_link" | "passkey" | "otp" | "google";
}

export interface MarketDataPoint {
  date: string;
  close: number;
  sma_20: number;
  rsi: number;
}

export interface AnalysisResponse {
  ticker: string;
  live_price: number;
  target_price: number;
  predicted_return_pct: number;
  hit_ratio: number;
  rsi_now: number;
  signal: SignalType;
  model_used: "XGBoost" | "Random Forest";
  rmse: number;
  chart_data: MarketDataPoint[];
  feature_importance?: { feature: string; weight: number }[];
  exchange?: string;
  currency?: string;
  currency_symbol?: string;
}

export interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  content: string;
  timestamp: string;
}

/** Minimal payload used by the chatbot header. */
export interface ChatSummaryContext {
  ticker: string;
  rsi: number;
  signal: SignalType;
  target: number;
  currency_symbol?: string;
}
