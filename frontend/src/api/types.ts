/** Hand-picked response shapes mirroring the backend schemas (kept small and explicit). */

export type Role = "student" | "instructor" | "admin";

export interface UserOut {
  id: string;
  email: string;
  role: Role;
  email_verified: boolean;
  totp_enabled: boolean;
  created_at: string;
}

export interface Cohort {
  name: string;
  ends_at: string;
}

export interface AccessOut {
  has_access: boolean;
  cohorts: Cohort[];
  pending_request: boolean;
}

export interface QuotaOut {
  used: number;
  limit: number | null;
  remaining: number | null;
  resets_at: string;
}

export interface MeOut {
  user: UserOut;
  access: AccessOut;
  quota: QuotaOut;
}

export interface EngageLevelOut {
  number: number;
  title: string;
  solved: boolean;
  lesson: string | null;
}

export interface CatalogSkill {
  name: string;
  description: string;
}

export interface ScanFinding {
  kind: string;
  severity: "info" | "warning" | "danger";
  message: string;
  excerpt: string;
}

export interface ScanOut {
  suspicious: boolean;
  max_severity: string;
  findings: ScanFinding[];
  as_human_reads: string;
  as_model_reads: string;
}

export interface LabStateOut {
  workspace: Record<string, string>;
  attacker_log: { method: string; url: string; body: string }[];
  outbox: { to: string; subject: string; body: string }[];
  blocked_actions: { tool: string; defense: string; reason: string }[];
}

export interface DebriefOut {
  attacked: boolean;
  exfiltrated: boolean;
  steps: string[];
  technique: string;
  stopped_by: string[];
  learn_slug: string;
}

export interface ArticleSummary {
  slug: string;
  title: string;
  summary: string;
}

export interface LearnIndex {
  articles: ArticleSummary[];
  prompting_guide_url: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}
