export interface CandidateInfo {
  name?: string;
  personal_details?: string[];
  education?: string[];
  experience?: string[];
}

export interface PipelineResult {
  candidate_name?: string;
  candidate_info?: CandidateInfo;
  personal_details?: string[];
  education?: string[];
  experience?: string[];
  score: number;
  ats_score: number;
  matched_skills: string[];
  missing_skills: string[];
  weaknesses: string[];
  github_flags: string[];
}

export interface ReviewResponse {
  id: number;
  file_hash: string;
  filename: string;
  candidate_name?: string;
  job_title: string;
  score: number;
  already_reviewed: boolean;
  reviewed_at: string;
  result: PipelineResult;
}

export interface ReviewSummary {
  id: number;
  filename: string;
  candidate_name?: string;
  job_title: string;
  score: number;
  created_at: string;
}

export interface ReviewListResponse {
  items: ReviewSummary[];
  reviews?: ReviewSummary[];
  total: number;
  page: number;
  size: number;
  pages: number;
}
