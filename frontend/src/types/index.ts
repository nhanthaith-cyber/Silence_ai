export interface Conversation {
  id: string;
  platform: 'facebook' | 'instagram' | 'shopee' | 'tiktok';
  customer_id: string;
  customer_name: string;
  customer_avatar?: string;
  status: 'open' | 'ai_handling' | 'waiting_human' | 'human_handling' | 'resolved' | 'closed';
  assigned_agent?: string;
  last_message: string;
  last_message_at: string;
  unread_count: number;
  ai_confidence?: number;
  created_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  direction: 'inbound' | 'outbound';
  sender_name: string;
  content: string;
  image_url?: string;
  is_ai_generated: boolean;
  ai_confidence?: number;
  created_at: string;
}

export interface KnowledgeItem {
  id: string;
  category: string;
  question: string;
  answer: string;
  tags: string;
  is_active: boolean;
  usage_count: number;
  created_at: string;
}

export interface AgentConfig {
  id: string;
  name: string;
  platform: string;
  system_prompt: string;
  temperature: number;
  auto_reply: boolean;
  confidence_threshold: number;
  greeting_message: string;
  is_active: boolean;
  created_at: string;
}

export interface AnalyticsOverview {
  total_conversations: number;
  open_conversations: number;
  waiting_human: number;
  resolved_today: number;
  total_messages: number;
  ai_messages: number;
  ai_auto_reply_rate: number;
  platform_stats: Array<{ platform: string; count: number }>;
  status_stats: Array<{ status: string; count: number }>;
}

export interface Document {
  id: string;
  filename: string;
  created_at: string;
}

export interface CustomerMemory {
  id: string;
  customer_id: string;
  platform: string;
  preferred_sizes: string | null;
  preferred_fit: string | null;
  style_preferences: string | null;
  purchase_history_summary: string | null;
  last_purchase_date: string | null;
  complaint_history: string | null;
  price_sensitivity: string | null;
  satisfaction_score: number | null;
  communication_style: string | null;
  body_measurements: string | null;
  notes: string | null;
  expires_at: string | null;
  updated_at: string;
  created_at: string;
}

export interface Product {
  id: string;
  name: string;
  slug: string;
  category: string;
  subcategory: string | null;
  description: string | null;
  price: number;
  sale_price: number | null;
  sizes_available: string | null;
  size_chart: string | null;
  fabric: string | null;
  fabric_properties: string | null;
  fit_type: string | null;
  color: string | null;
  care_instructions: string | null;
  is_active: boolean;
  created_at: string;
}
