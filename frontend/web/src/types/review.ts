export interface CandidateInfo {
  name?: string;
  personal_details?: string[];
  education?: string[];
  experience?: string[];
}

export interface GitHubFlag {
  id: string;
  severity: "high" | "medium" | "low" | "info" | string;
  message: string;
  repo?: string;
  evidence?: string;
  commit?: string;
  url?: string;
}

export interface GitHubRepoSummary {
  name: string;
  full_name?: string;
  url?: string;
  score: number;
  is_fork: boolean;
  claimed?: boolean;
  commits?: number;
  own_commits?: number;
}

export interface GitHubAudit {
  status?: "analyzed" | "ok" | "partial" | "not_provided" | "not_found" | string;
  username?: string | null;
  profile_url?: string | null;
  github_score?: number | null;
  risk_level?: "low" | "review" | "medium" | "high" | string;
  repo_count?: number;
  flags?: GitHubFlag[];
  verified_signals?: string[];
  repos?: GitHubRepoSummary[];
  skills?: {
    confirmed?: string[];
    unconfirmed?: string[];
  };
  warnings?: string[];
}

export interface PipelineResult {
  candidate_name?: string;
  candidate_info?: CandidateInfo;
  personal_details?: string[];
  education?: string[];
  experience?: string[];
  score: number;
  ats_score: number;
  github_score?: number | null;
  github_audit?: GitHubAudit;
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
