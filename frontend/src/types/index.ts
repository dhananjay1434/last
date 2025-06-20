// API Response Types
export interface ApiStatus {
  online: boolean;
  message: string;
}

export interface StatusResponse {
  enhanced_features?: boolean;
  transcription?: boolean;
  ocr_enhancement?: boolean;
  advanced_features?: boolean;
  [key: string]: any;
}

export interface ExtractResponse {
  job_id: string;
  message: string;
  status?: string;
}

export interface JobStatus {
  status: 'initializing' | 'processing' | 'completed' | 'failed' | 'pending';
  progress: number;
  message: string;
  error?: string;
  slides_count?: number;
  has_pdf?: boolean;
  has_study_guide?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface Slide {
  filename: string;
  path: string;
  timestamp: string;
  content: string;
  title: string;
  type: string;
  keywords: string[];
  similarity?: number;
  frame_number?: number;
}

export interface SlidesResponse {
  slides: Slide[];
  total_count: number;
  job_id: string;
}

export interface StudyGuideResponse {
  content: string;
  job_id: string;
  generated_at: string;
}

// Configuration Types
export interface ExtractionOptions {
  adaptive_sampling: boolean;
  extract_content: boolean;
  organize_slides: boolean;
  generate_pdf: boolean;
  enable_transcription: boolean;
  enable_ocr_enhancement: boolean;
  enable_concept_extraction: boolean;
  enable_slide_descriptions: boolean;
}

export interface ExtractionRequest extends ExtractionOptions {
  video_url: string;
  gemini_api_key?: string;
  interval?: number;
  similarity_threshold?: number;
  ocr_confidence?: number;
}

// Component Props Types
export interface ProgressBarProps {
  progress: number;
  status: string;
  message?: string;
}

export interface StatusIndicatorProps {
  status: JobStatus['status'];
  message: string;
}

export interface FeatureToggleProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}

// Error Types
export interface ApiError {
  error: string;
  message?: string;
  status_code?: number;
}

// Environment Types
export interface EnvironmentConfig {
  API_BASE_URL: string;
  NODE_ENV: 'development' | 'production' | 'test';
}

// Utility Types
export type JobStatusType = JobStatus['status'];
export type ExtractionOptionKey = keyof ExtractionOptions;

// Event Handler Types
export type InputChangeHandler = (event: React.ChangeEvent<HTMLInputElement>) => void;
export type CheckboxChangeHandler = (event: React.ChangeEvent<HTMLInputElement>) => void;
export type ButtonClickHandler = (event: React.MouseEvent<HTMLButtonElement>) => void;
