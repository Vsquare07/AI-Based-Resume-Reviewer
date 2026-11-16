"use client";

import React, { useState, useRef, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import {
  UploadCloud,
  FileText,
  X,
  Sparkles,
  RefreshCw,
  AlertTriangle,
  Check,
  CheckCircle2,
  XCircle,
  Loader2,
  Info,
  ShieldAlert,
  ShieldCheck,
  ExternalLink,
  GitFork,
  Code2,
  Mail,
  Phone,
  Globe,
  GraduationCap,
  Briefcase,
  Calendar,
} from "lucide-react";

function GithubIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      role="img"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
      <path d="M9 18c-4.51 2-5-2-7-2" />
    </svg>
  );
}
import { toast } from "sonner";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { ReviewResponse } from "@/types/review";
import { cn } from "cn";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const JOB_SUGGESTIONS = [
  "AI Engineer",
  "Software Engineer",
  "Data Scientist",
  "Cybersecurity Analyst",
  "Robotics Engineer",
  "Machine Learning Engineer",
  "Full Stack Developer",
  "DevOps Engineer",
];

function ScoreGauge({
  score,
  label,
  sublabel,
  size = 130,
}: {
  score: number;
  label: string;
  sublabel?: string;
  size?: number;
}) {
  const strokeWidth = 9;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const clampedScore = Math.min(100, Math.max(0, score || 0));
  const offset = circumference - (clampedScore / 100) * circumference;

  const getColorClass = (val: number) => {
    if (val >= 80) return "stroke-emerald-500 text-emerald-500";
    if (val >= 60) return "stroke-amber-500 text-amber-500";
    return "stroke-rose-500 text-rose-500";
  };

  const getBadgeText = (val: number) => {
    if (val >= 80) return "Strong Match";
    if (val >= 60) return "Moderate Match";
    return "Needs Improvement";
  };

  return (
    <div className="flex flex-col items-center justify-center p-3 text-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg className="w-full h-full -rotate-90" viewBox={`0 0 ${size} ${size}`}>
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            className="stroke-muted"
            strokeWidth={strokeWidth}
            fill="transparent"
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            className={cn("transition-all duration-1000 ease-out", getColorClass(clampedScore))}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            fill="transparent"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-extrabold tracking-tight">{clampedScore}</span>
          <span className="text-[11px] font-medium text-muted-foreground uppercase">/ 100</span>
        </div>
      </div>
      <div className="mt-3 font-semibold text-sm">{label}</div>
      <Badge
        variant="outline"
        className={cn(
          "mt-1 text-xs font-medium",
          clampedScore >= 80 && "border-emerald-500/40 text-emerald-600 dark:text-emerald-400 bg-emerald-500/10",
          clampedScore >= 60 && clampedScore < 80 && "border-amber-500/40 text-amber-600 dark:text-amber-400 bg-amber-500/10",
          clampedScore < 60 && "border-rose-500/40 text-rose-600 dark:text-rose-400 bg-rose-500/10"
        )}
      >
        {getBadgeText(clampedScore)}
      </Badge>
      {sublabel && <span className="mt-1 text-xs text-muted-foreground">{sublabel}</span>}
    </div>
  );
}

function parseContactDetail(raw: string) {
  const isBirthdayGlyph = raw.includes("\uf1fd");
  const isPhoneGlyph = raw.includes("\uf095");
  const isEmailGlyph = raw.includes("\uf0e0");
  const isGitHubGlyph = raw.includes("\uf09b");

  const cleaned = raw.replace(/[\uE000-\uF8FF]/g, "").trim();
  let href: string | null = null;
  let label = cleaned;

  // Extract trailing URL in parentheses like (tel:...), (mailto:...), (https://...)
  const linkInParens = cleaned.match(/\(((?:mailto|tel|https?):.*)\)$/i);
  if (linkInParens) {
    href = linkInParens[1].trim();
    label = cleaned.replace(/\s*\(((?:mailto|tel|https?):.*)\)$/i, "").trim();
  }

  // Handle email
  const emailMatch = label.match(/[\w.+-]+@[\w-]+\.[\w.-]+/);
  if (!href && (emailMatch || isEmailGlyph)) {
    if (emailMatch) {
      href = `mailto:${emailMatch[0]}`;
      label = emailMatch[0];
    }
  } else if (href && href.startsWith("mailto:")) {
    const cleanEmail = href.replace(/^mailto:/i, "").trim();
    if (cleanEmail) label = cleanEmail;
  }

  // Date check (e.g. DD-MM-YYYY, YYYY-MM-DD or birthday icon)
  const isDate = /^\d{1,4}[-/.]\d{1,2}[-/.]\d{2,4}$/.test(label) || isBirthdayGlyph;

  // Handle tel
  const telMatch = label.match(/(?:\+?\d[\d\s\-\(\)]{7,}\d)/);
  if (href && href.startsWith("tel:")) {
    const cleanDigits = href.replace(/^tel:/i, "").replace(/[^\d+]/g, "");
    href = `tel:${cleanDigits}`;
    if (!label || label.startsWith("tel:")) {
      label = telMatch ? telMatch[0].trim() : cleanDigits;
    }
  } else if (
    !href &&
    !isDate &&
    telMatch &&
    (isPhoneGlyph ||
      cleaned.toLowerCase().includes("tel") ||
      cleaned.toLowerCase().includes("phone") ||
      cleaned.toLowerCase().includes("mob") ||
      cleaned.startsWith("+") ||
      cleaned.startsWith("("))
  ) {
    const cleanDigits = telMatch[0].replace(/[^\d+]/g, "");
    href = `tel:${cleanDigits}`;
    label = telMatch[0].trim();
  }

  // Handle GitHub & URLs
  if (href && href.includes("github.com/")) {
    const ghUser = href.match(/github\.com\/([A-Za-z0-9_-]+)/)?.[1];
    if (ghUser) label = `@${ghUser}`;
  } else if (!href && (isGitHubGlyph || raw.includes("") || raw.toLowerCase().includes("github.com"))) {
    const ghUser =
      label.match(/github\.com\/([A-Za-z0-9_-]+)/)?.[1] ||
      label.replace(/github[:\s]*/i, "").trim().split(/\s+/)[0];
    if (ghUser && /^[A-Za-z0-9_-]+$/.test(ghUser)) {
      href = `https://github.com/${ghUser}`;
      label = `@${ghUser}`;
    }
  } else if (!href) {
    const urlMatch = label.match(/https?:\/\/[^\s]+/);
    if (urlMatch) {
      href = urlMatch[0];
      label = label.replace(urlMatch[0], "").trim() || urlMatch[0];
    }
  }

  label = label.replace(/^[\s\u2022\-\:\.]+|[\s\u2022\-\:\.]+$/g, "").trim();

  const isEmail = !!(href && href.startsWith("mailto:"));
  const isPhone = !!(href && href.startsWith("tel:"));
  const isGitHub = !!(href && href.includes("github.com"));
  const isLink = !!(href && !isEmail && !isPhone && !isGitHub);

  return { label, href, isEmail, isPhone, isGitHub, isLink, isDate };
}

function ReviewDashboard() {
  const searchParams = useSearchParams();
  const reviewIdParam = searchParams.get("reviewId");

  const [file, setFile] = useState<File | null>(null);
  const [cachedFileName, setCachedFileName] = useState("");
  const [jobTitle, setJobTitle] = useState("Software Engineer");
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [currentStepMessage, setCurrentStepMessage] = useState<string>("");
  const [reviewResult, setReviewResult] = useState<ReviewResponse | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auto-load cached review if reviewId is passed via URL query
  useEffect(() => {
    if (reviewIdParam) {
      const loadCachedReview = async () => {
        setLoading(true);
        try {
          const res = await fetch(`${API_BASE}/api/reviews/${reviewIdParam}`);
          if (!res.ok) throw new Error("Could not find review");
          const data: ReviewResponse = await res.json();
          setReviewResult(data);
          setJobTitle(data.job_title);
          setCachedFileName(data.filename);
          toast.success(`Loaded evaluation for "${data.candidate_name || data.filename}"`);
        } catch (e: unknown) {
          const msg = e instanceof Error ? e.message : "Failed to load review";
          toast.error(msg);
        } finally {
          setLoading(false);
        }
      };
      loadCachedReview();
    }
  }, [reviewIdParam]);

  // Elapsed timer while processing
  useEffect(() => {
    let secondInterval: NodeJS.Timeout;

    if (loading) {
      setElapsedSeconds(0);
      secondInterval = setInterval(() => {
        setElapsedSeconds((prev) => prev + 1);
      }, 1000);
    }

    return () => {
      clearInterval(secondInterval);
    };
  }, [loading]);

  const validateAndSetFile = (selectedFile: File) => {
    const isPdf =
      selectedFile.name.toLowerCase().endsWith(".pdf") ||
      selectedFile.type === "application/pdf";
    if (!isPdf) {
      toast.error("Please select a valid PDF file");
      return;
    }
    if (selectedFile.size > 5 * 1024 * 1024) {
      toast.error("File size exceeds 5 MB limit");
      return;
    }
    setFile(selectedFile);
    setCachedFileName("");
    toast.success(`Loaded "${selectedFile.name}"`);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const executeReview = async (forceReview = false) => {
    if (!file) {
      if (cachedFileName) {
        toast.info("Please select or drop a PDF file to re-run evaluation");
        fileInputRef.current?.click();
        return;
      }
      toast.error("Please select a resume PDF first");
      fileInputRef.current?.click();
      return;
    }
    if (!jobTitle.trim()) {
      toast.error("Please enter or select a target job title");
      document.getElementById("job-title-input")?.focus();
      return;
    }

    setLoading(true);
    setCurrentStepMessage("[0/4] Parsing resume...");

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("job_title", jobTitle.trim());
      formData.append("force", String(forceReview));
      formData.append("stream", "true");

      const res = await fetch(`${API_BASE}/api/review`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: `HTTP error ${res.status}` }));
        throw new Error(errorData.detail || "Pipeline evaluation failed");
      }

      if (res.headers.get("content-type")?.includes("text/event-stream") && res.body) {
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let finalData: ReviewResponse | null = null;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split("\n\n");
          buffer = parts.pop() || "";

          for (const part of parts) {
            const lines = part.split("\n");
            for (const line of lines) {
              const trimmed = line.trim();
              if (!trimmed.startsWith("data:")) continue;
              const payload = trimmed.replace(/^data:\s*/, "");
              try {
                const msg = JSON.parse(payload);
                if (msg.type === "log") {
                  let displayMsg = msg.message;
                  if (displayMsg.startsWith("[0/4]")) {
                    displayMsg = "[0/4] Parsing resume...";
                  }
                  if (displayMsg.startsWith("[")) {
                    setCurrentStepMessage(displayMsg);
                  }
                } else if (msg.type === "result") {
                  finalData = msg.data;
                } else if (msg.type === "error") {
                  throw new Error(msg.detail || "Pipeline execution failed");
                }
              } catch (err) {
                if (err instanceof Error && err.message.startsWith("Pipeline execution")) {
                  throw err;
                }
              }
            }
          }
        }

        if (finalData) {
          setReviewResult(finalData);
          if (finalData.already_reviewed && !forceReview) {
            toast.info("Retrieved cached review result");
          } else {
            toast.success("Resume evaluation completed!");
          }
        }
      } else {
        const data: ReviewResponse = await res.json();
        setReviewResult(data);

        if (data.already_reviewed && !forceReview) {
          toast.info("Retrieved cached review result");
        } else {
          toast.success("Resume evaluation completed!");
        }
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to review resume";
      toast.error(msg, {
        description: "Verify that the FastAPI backend (and Ollama) is running.",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight">AI Resume Reviewer</h1>
        <p className="text-muted-foreground mt-1 text-sm sm:text-base">
          Upload a candidate PDF resume and enter a target job title for multi-stage ATS keyword matching, GitHub verification, and LLM role fit analysis.
        </p>
      </div>

      {/* Review Submission Card */}
      <Card className="border-border/60 shadow-sm">
        <CardHeader>
          <CardTitle className="text-lg font-semibold">Upload &amp; Target Role</CardTitle>
          <CardDescription>
            Select your PDF (up to 5 MB) and specify the position you are targeting.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* If file is selected, show file preview card */}
          {file || cachedFileName ? (
            <div className="border-2 border-primary/50 bg-primary/5 rounded-xl p-8 text-center transition-all">
              <div className="flex items-center justify-between max-w-md mx-auto p-3.5 rounded-lg border bg-background shadow-xs">
                <div className="flex items-center gap-3 truncate mr-2">
                  <div className="p-2.5 rounded-md bg-primary/10 text-primary shrink-0">
                    <FileText className="h-6 w-6" />
                  </div>
                  <div className="text-left truncate">
                    <p className="text-sm font-semibold truncate text-foreground">
                      {file ? file.name : cachedFileName}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {file ? `${(file.size / 1024).toFixed(1)} KB • PDF` : "Saved PDF Resume"}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <label htmlFor="resume-file-input" className="cursor-pointer">
                    <span className="inline-flex items-center justify-center h-8 px-3 rounded-md border border-input bg-background hover:bg-muted text-xs font-semibold shadow-xs transition-colors">
                      Change
                    </span>
                  </label>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                    onClick={() => {
                      setFile(null);
                      setCachedFileName("");
                    }}
                    title="Remove file"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>
          ) : (
            /* If no file, show drag-and-drop label */
            <label
              htmlFor="resume-file-input"
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={cn(
                "flex flex-col items-center justify-center border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all select-none",
                isDragging
                  ? "border-primary bg-primary/5 scale-[1.01]"
                  : "border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/30"
              )}
            >
              <div className="p-3.5 rounded-full bg-primary/10 text-primary mb-3">
                <UploadCloud className="h-8 w-8" />
              </div>
              <span className="inline-flex items-center justify-center h-9 px-4 rounded-md bg-primary text-primary-foreground text-xs font-semibold shadow-xs hover:bg-primary/90 transition-colors">
                Select Resume PDF
              </span>
              <p className="text-xs text-muted-foreground mt-2">
                or drag and drop your PDF here (up to 5 MB)
              </p>
            </label>
          )}

          {/* Hidden File Input */}
          <input
            id="resume-file-input"
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            className="hidden"
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                validateAndSetFile(e.target.files[0]);
              }
            }}
          />

          {/* Job Title Input & Quick Suggestions */}
          <div className="flex flex-col gap-2">
            <label htmlFor="job-title-input" className="block text-sm font-medium">
              Target Job Title
            </label>
            <Input
              id="job-title-input"
              value={jobTitle}
              onChange={(e) => setJobTitle(e.target.value)}
              placeholder="e.g. AI Engineer, Software Engineer, Cybersecurity Analyst"
              className="max-w-xl px-4 py-2"
              disabled={loading}
            />

            <div className="flex flex-wrap items-center gap-1.5 pt-1">
              <span className="text-xs text-muted-foreground mr-1">Suggestions:</span>
              {JOB_SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => setJobTitle(suggestion)}
                  disabled={loading}
                  className={cn(
                    "px-2.5 py-1 text-xs rounded-full border transition-colors",
                    jobTitle === suggestion
                      ? "bg-primary text-primary-foreground border-primary"
                      : "bg-secondary text-secondary-foreground hover:bg-muted border-border"
                  )}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>

          {/* Submit Action */}
          <div className="flex items-center gap-4 pt-2">
            <Button
              type="button"
              disabled={loading}
              onClick={() => executeReview(false)}
              className="gap-2 px-6"
              size="lg"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Analyzing Resume...</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  <span>Analyze Resume</span>
                </>
              )}
            </Button>

            {loading && (
              <div className="flex flex-col gap-0.5 text-xs">
                <div className="flex items-center gap-1.5 font-medium text-foreground">
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
                  <span className="font-semibold text-primary truncate max-w-sm sm:max-w-md">
                    {currentStepMessage || "[0/4] Parsing resume..."}
                  </span>
                </div>
                <div className="text-[11px] text-muted-foreground">
                  <span>Elapsed: {elapsedSeconds}s</span>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Review Results */}
      {reviewResult && !loading && (
        <div className="space-y-6">
          {/* Cache Alert if already reviewed */}
          {reviewResult.already_reviewed && (
            <Alert className="border-amber-500/40 bg-amber-500/10 text-foreground">
              <Info className="h-4 w-4 text-amber-500" />
              <AlertTitle className="font-semibold text-amber-700 dark:text-amber-400">
                Cached Review Found
              </AlertTitle>
              <AlertDescription className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mt-1">
                <span className="text-sm text-muted-foreground">
                  This resume was evaluated for <strong>{reviewResult.job_title}</strong> on{" "}
                  {new Date(reviewResult.reviewed_at).toLocaleString()}. Showing saved evaluation.
                </span>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => executeReview(true)}
                  className="gap-1.5 shrink-0 border-amber-500/40 hover:bg-amber-500/20"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  <span>Re-run review</span>
                </Button>
              </AlertDescription>
            </Alert>
          )}

          {/* Candidate Basic Information Card */}
          <Card className="border-border/60 shadow-sm">
            <CardHeader className="pb-3">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="h-12 w-12 rounded-full bg-primary/10 text-primary flex items-center justify-center font-extrabold text-lg shrink-0">
                    {((reviewResult.candidate_name || reviewResult.result?.candidate_name || "C")[0] || "C").toUpperCase()}
                  </div>
                  <div>
                    <CardTitle className="text-xl font-bold tracking-tight">
                      {reviewResult.candidate_name || reviewResult.result?.candidate_name || "Candidate Profile"}
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Target Role: <span className="font-semibold text-foreground">{reviewResult.job_title}</span>
                    </CardDescription>
                  </div>
                </div>
                <Badge variant="secondary" className="px-3 py-1 text-xs font-semibold self-start sm:self-auto">
                  Candidate Overview
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4 pt-1">
              {/* Contact & Personal Details */}
              {((reviewResult.result?.candidate_info?.personal_details && reviewResult.result.candidate_info.personal_details.length > 0) ||
                (reviewResult.result?.personal_details && reviewResult.result.personal_details.length > 0)) && (
                <div className="flex flex-wrap gap-2 pt-1 border-t border-border/40">
                  {((reviewResult.result?.candidate_info?.personal_details || reviewResult.result?.personal_details || []) as string[]).map((detail: string, idx: number) => {
                    const parsed = parseContactDetail(detail);
                    if (!parsed.label) return null;

                    const icon = (
                      <>
                        {parsed.isEmail && <Mail className="h-3.5 w-3.5 text-primary shrink-0" />}
                        {parsed.isPhone && <Phone className="h-3.5 w-3.5 text-primary shrink-0" />}
                        {parsed.isGitHub && <GithubIcon className="h-3.5 w-3.5 text-primary shrink-0" />}
                        {parsed.isDate && <Calendar className="h-3.5 w-3.5 text-primary shrink-0" />}
                        {parsed.isLink && <Globe className="h-3.5 w-3.5 text-primary shrink-0" />}
                      </>
                    );

                    if (parsed.href) {
                      return (
                        <a
                          key={idx}
                          href={parsed.href}
                          target={parsed.isGitHub || parsed.isLink ? "_blank" : undefined}
                          rel={parsed.isGitHub || parsed.isLink ? "noopener noreferrer" : undefined}
                          className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-muted/60 hover:bg-muted text-xs text-foreground/90 hover:text-foreground border border-border/50 hover:border-primary/40 transition-colors cursor-pointer group"
                        >
                          {icon}
                          <span className="font-medium">{parsed.label}</span>
                          {(parsed.isGitHub || parsed.isLink) && (
                            <ExternalLink className="h-3 w-3 opacity-60 group-hover:opacity-100 ml-0.5 shrink-0 transition-opacity" />
                          )}
                        </a>
                      );
                    }

                    return (
                      <div
                        key={idx}
                        className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-muted/60 text-xs text-foreground/90 border border-border/50"
                      >
                        {icon}
                        <span>{parsed.label}</span>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Education & Experience Highlights */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                {reviewResult.result?.candidate_info?.education && reviewResult.result.candidate_info.education.length > 0 && (
                  <div className="space-y-1.5 p-3.5 rounded-lg bg-muted/30 border border-border/40 text-xs">
                    <div className="flex items-center gap-1.5 font-semibold text-foreground">
                      <GraduationCap className="h-4 w-4 text-primary shrink-0" />
                      <span>Education Background</span>
                    </div>
                    <ul className="space-y-1 text-muted-foreground pl-4 list-disc">
                      {reviewResult.result.candidate_info.education.map((edu, idx) => (
                        <li key={idx} className="leading-snug">{edu}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {reviewResult.result?.candidate_info?.experience && reviewResult.result.candidate_info.experience.length > 0 && (
                  <div className="space-y-1.5 p-3.5 rounded-lg bg-muted/30 border border-border/40 text-xs">
                    <div className="flex items-center gap-1.5 font-semibold text-foreground">
                      <Briefcase className="h-4 w-4 text-primary shrink-0" />
                      <span>Professional Experience</span>
                    </div>
                    <ul className="space-y-1 text-muted-foreground pl-4 list-disc">
                      {reviewResult.result.candidate_info.experience.map((exp, idx) => (
                        <li key={idx} className="leading-snug">{exp}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Score Gauges */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card className="border-border/60">
              <CardHeader className="pb-2">
                <CardTitle className="text-base font-semibold">Overall Pipeline Score</CardTitle>
                <CardDescription>
                  Holistic evaluation of candidate qualifications, experience depth, and role suitability
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-2">
                <ScoreGauge
                  score={reviewResult.score}
                  label="Overall Fit Score"
                />
              </CardContent>
            </Card>

            <Card className="border-border/60">
              <CardHeader className="pb-2">
                <CardTitle className="text-base font-semibold">ATS Compatibility Score</CardTitle>
                <CardDescription>
                  Keyword and technical skill match rate against target job requirements
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-2">
                <ScoreGauge
                  score={reviewResult.result?.ats_score ?? 0}
                  label="ATS Keyword Score"
                />
              </CardContent>
            </Card>
          </div>

          {/* Skills Breakdown */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Matched Skills */}
            <Card className="border-border/60">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                    <CardTitle className="text-base font-semibold">Matched Skills</CardTitle>
                  </div>
                  <Badge variant="outline" className="border-emerald-500/40 text-emerald-600 dark:text-emerald-400">
                    {reviewResult.result?.matched_skills?.length || 0} identified
                  </Badge>
                </div>
                <CardDescription>
                  Skills and tools found in candidate profile matching {reviewResult.job_title}
                </CardDescription>
              </CardHeader>
              <CardContent>
                {reviewResult.result?.matched_skills && reviewResult.result.matched_skills.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {reviewResult.result.matched_skills.map((skill, idx) => (
                      <Badge
                        key={idx}
                        variant="secondary"
                        className="bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/25 px-2.5 py-1 text-xs"
                      >
                        {skill}
                      </Badge>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground italic">No required skills matched.</p>
                )}
              </CardContent>
            </Card>

            {/* Missing Skills */}
            <Card className="border-border/60">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <XCircle className="h-5 w-5 text-rose-500" />
                    <CardTitle className="text-base font-semibold">Missing Skills</CardTitle>
                  </div>
                  <Badge variant="outline" className="border-rose-500/40 text-rose-600 dark:text-rose-400">
                    {reviewResult.result?.missing_skills?.length || 0} missing
                  </Badge>
                </div>
                <CardDescription>
                  Key skills expected for {reviewResult.job_title} that were absent
                </CardDescription>
              </CardHeader>
              <CardContent>
                {reviewResult.result?.missing_skills && reviewResult.result.missing_skills.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {reviewResult.result.missing_skills.map((skill, idx) => (
                      <Badge
                        key={idx}
                        variant="destructive"
                        className="bg-rose-500/15 text-rose-700 dark:text-rose-300 border border-rose-500/25 px-2.5 py-1 text-xs"
                      >
                        {skill}
                      </Badge>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">
                    All benchmark skills detected!
                  </p>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Candidate Weaknesses / Observations */}
          <Card className="border-border/60">
            <CardHeader>
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-amber-500" />
                <CardTitle className="text-base font-semibold">Areas of Improvement &amp; Weaknesses</CardTitle>
              </div>
              <CardDescription>
                Detailed observations identified during the automated resume review
              </CardDescription>
            </CardHeader>
            <CardContent>
              {reviewResult.result?.weaknesses && reviewResult.result.weaknesses.length > 0 ? (
                <ul className="space-y-2 text-sm">
                  {reviewResult.result.weaknesses.map((item, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-muted-foreground">
                      <span className="text-amber-500 font-bold leading-5">&bull;</span>
                      <span className="leading-5">{item}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-muted-foreground italic">No specific weaknesses noted.</p>
              )}
            </CardContent>
          </Card>

          {/* GitHub Code & Profile Audit */}
          {(() => {
            const audit = reviewResult.result?.github_audit;
            const status = audit?.status;
            const username = audit?.username || (
              typeof reviewResult.result?.candidate_info?.personal_details?.find((p) => p.includes("github.com/")) === "string"
                ? reviewResult.result.candidate_info.personal_details.find((p) => p.includes("github.com/"))?.match(/github\.com\/([A-Za-z0-9_-]+)/)?.[1]
                : undefined
            );
            const profileUrl = audit?.profile_url || (username ? `https://github.com/${username}` : undefined);
            const githubScore = audit?.github_score ?? reviewResult.result?.github_score;
            const riskLevel = audit?.risk_level;
            const auditFlags = audit?.flags || [];
            const legacyFlags = reviewResult.result?.github_flags || [];
            const verifiedSignals = audit?.verified_signals || [];
            const repos = audit?.repos || [];
            const skills = audit?.skills;
            const warnings = audit?.warnings || [];

            const isNotProvided = status === "not_provided" || (!username && auditFlags.length === 0 && legacyFlags.length === 0);
            const isNotFound = status === "not_found";

            return (
              <Card className="border-border/60 shadow-xs">
                <CardHeader>
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                    <div className="flex items-center gap-2.5">
                      <div className="p-2 rounded-md bg-muted text-foreground">
                        <GithubIcon className="h-5 w-5" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <CardTitle className="text-base font-semibold">GitHub Code &amp; Profile Audit</CardTitle>
                          {username && profileUrl && (
                            <a
                              href={profileUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 text-xs font-mono text-primary hover:underline"
                            >
                              <span>@{username}</span>
                              <ExternalLink className="h-3 w-3" />
                            </a>
                          )}
                        </div>
                        <CardDescription className="text-xs">
                          {isNotProvided
                            ? "Candidate code verification status"
                            : "Automated analysis of repository ownership, commit authenticity, and coding history"}
                        </CardDescription>
                      </div>
                    </div>

                    {/* Status & Risk Badges */}
                    <div className="flex items-center flex-wrap gap-2">
                      {isNotProvided ? (
                        <Badge variant="outline" className="text-muted-foreground border-border text-xs">
                          No GitHub Link Provided
                        </Badge>
                      ) : isNotFound ? (
                        <Badge variant="destructive" className="text-xs">
                          Profile Not Found
                        </Badge>
                      ) : (
                        <>
                          {riskLevel && (
                            <Badge
                              className={cn(
                                "text-xs font-semibold uppercase tracking-wider",
                                riskLevel === "low" && "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30",
                                (riskLevel === "review" || riskLevel === "medium") && "bg-amber-500/15 text-amber-700 dark:text-amber-300 border border-amber-500/30",
                                riskLevel === "high" && "bg-rose-500/15 text-rose-700 dark:text-rose-300 border border-rose-500/30"
                              )}
                            >
                              {riskLevel === "review" ? "Review Advised" : `${riskLevel} Risk`}
                            </Badge>
                          )}
                          {githubScore !== undefined && githubScore !== null && (
                            <Badge variant="outline" className="text-xs font-mono font-medium">
                              Score: <span className="font-bold text-foreground ml-1">{githubScore}/100</span>
                            </Badge>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="space-y-4">
                  {isNotProvided ? (
                    <div className="flex items-start gap-3 p-3.5 rounded-lg bg-muted/40 border border-border/50 text-xs text-muted-foreground">
                      <Info className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
                      <div>
                        <p className="font-medium text-foreground">No GitHub Profile Linked</p>
                        <p className="mt-0.5">
                          No public GitHub profile link was detected in the resume text. Code verification, commit authenticity, and repository checks were skipped without penalty.
                        </p>
                      </div>
                    </div>
                  ) : isNotFound ? (
                    <Alert className="border-rose-500/40 bg-rose-500/10 text-rose-800 dark:text-rose-300">
                      <AlertTriangle className="h-4 w-4" />
                      <AlertDescription className="text-xs font-medium">
                        The linked profile <strong>@{username}</strong> was not found on GitHub. Please check for typos in the candidate&apos;s resume link.
                      </AlertDescription>
                    </Alert>
                  ) : (
                    <>
                      {/* Flags Section */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                            <ShieldAlert className="h-3.5 w-3.5" />
                            <span>Audit Flags {auditFlags.length > 0 ? `(${auditFlags.length})` : ""}</span>
                          </h4>
                        </div>

                        {auditFlags.length > 0 ? (
                          <div className="space-y-2">
                            {auditFlags.map((flag, idx) => {
                              const sev = (flag.severity || "info").toLowerCase();
                              const flagUrl =
                                flag.url ||
                                flag.message.match(/https?:\/\/[^\s]+/)?.[0] ||
                                (flag.repo && username ? `https://github.com/${username}/${flag.repo}` : null);
                              const cleanedMessage = flag.message
                                .replace(/:\s*https?:\/\/[^\s]+/g, "")
                                .replace(/https?:\/\/[^\s]+/g, "")
                                .trim()
                                .replace(/:\s*$/, "");

                              return (
                                <div
                                  key={idx}
                                  className={cn(
                                    "p-3 rounded-lg border text-xs space-y-1.5 transition-colors",
                                    sev === "high" && "border-rose-500/40 bg-rose-500/10 text-rose-900 dark:text-rose-200",
                                    sev === "medium" && "border-amber-500/40 bg-amber-500/10 text-amber-900 dark:text-amber-200",
                                    sev === "low" && "border-yellow-500/40 bg-yellow-500/10 text-yellow-900 dark:text-yellow-200",
                                    sev === "info" && "border-blue-500/40 bg-blue-500/10 text-blue-900 dark:text-blue-200"
                                  )}
                                >
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <span
                                      className={cn(
                                        "px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider",
                                        sev === "high" && "bg-rose-500 text-white",
                                        sev === "medium" && "bg-amber-500 text-white",
                                        sev === "low" && "bg-yellow-600 dark:bg-yellow-500 text-white",
                                        sev === "info" && "bg-blue-500 text-white"
                                      )}
                                    >
                                      {sev}
                                    </span>
                                    {flag.repo && (
                                      flagUrl ? (
                                        <a
                                          href={flagUrl}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          className="font-mono font-semibold px-2 py-0.5 rounded bg-background/80 hover:bg-background border border-current/25 hover:border-current/50 text-[11px] flex items-center gap-1.5 transition-colors cursor-pointer hover:underline"
                                          title={`Open ${flag.url?.includes("/commit/") ? "commit" : "repository"} on GitHub`}
                                        >
                                          <GitFork className="h-3 w-3 shrink-0" />
                                          <span>{flag.repo}</span>
                                          <ExternalLink className="h-2.5 w-2.5 opacity-70 shrink-0" />
                                        </a>
                                      ) : (
                                        <span className="font-mono font-semibold px-2 py-0.5 rounded bg-background/60 border border-current/20 text-[11px] flex items-center gap-1">
                                          <GitFork className="h-3 w-3 shrink-0" />
                                          <span>{flag.repo}</span>
                                        </span>
                                      )
                                    )}
                                    <span className="font-medium flex-1">{cleanedMessage}</span>
                                  </div>
                                  {flag.evidence && (
                                    <p className="text-[11px] opacity-85 pl-1 font-mono">
                                      Evidence: {flag.evidence}
                                    </p>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        ) : legacyFlags.length > 0 ? (
                          <div className="space-y-2">
                            {legacyFlags.map((flagStr, idx) => {
                              const isHigh = flagStr.toUpperCase().includes("[HIGH]");
                              const isMedium = flagStr.toUpperCase().includes("[MEDIUM]");
                              const urlMatch = flagStr.match(/https?:\/\/[^\s]+/);
                              const flagUrl = urlMatch ? urlMatch[0] : null;
                              const cleaned = flagStr
                                .replace(/:\s*https?:\/\/[^\s]+/g, "")
                                .replace(/https?:\/\/[^\s]+/g, "")
                                .trim()
                                .replace(/:\s*$/, "");

                              return (
                                <Alert
                                  key={idx}
                                  className={cn(
                                    "py-2.5",
                                    isHigh && "border-rose-500/40 bg-rose-500/10 text-rose-800 dark:text-rose-300",
                                    isMedium && "border-amber-500/40 bg-amber-500/10 text-amber-800 dark:text-amber-300",
                                    !isHigh && !isMedium && "border-blue-500/40 bg-blue-500/10 text-blue-800 dark:text-blue-300"
                                  )}
                                >
                                  <ShieldAlert className="h-4 w-4" />
                                  <AlertDescription className="text-xs font-medium flex items-center justify-between gap-2 flex-wrap w-full">
                                    <span>{cleaned}</span>
                                    {flagUrl && (
                                      <a
                                        href={flagUrl}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="inline-flex items-center gap-1 font-mono text-[11px] underline opacity-85 hover:opacity-100 shrink-0"
                                      >
                                        <span>View commit</span>
                                        <ExternalLink className="h-3 w-3" />
                                      </a>
                                    )}
                                  </AlertDescription>
                                </Alert>
                              );
                            })}
                          </div>
                        ) : (
                          <div className="flex items-center gap-2 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/25 text-xs text-emerald-700 dark:text-emerald-300 font-medium">
                            <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
                            <span>Clean code history: No suspicious commit dumps, license mismatches, or repository flags detected.</span>
                          </div>
                        )}
                      </div>

                      {/* Positive Verified Signals */}
                      {verifiedSignals.length > 0 && (
                        <div className="space-y-2 pt-2 border-t border-border/40">
                          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                            <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" />
                            <span>Verified Developer Signals ({verifiedSignals.length})</span>
                          </h4>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                            {verifiedSignals.map((signal, idx) => (
                              <div
                                key={idx}
                                className="flex items-start gap-2 p-2.5 rounded-lg bg-emerald-500/5 border border-emerald-500/20 text-xs text-foreground/90"
                              >
                                <Check className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400 font-bold shrink-0 mt-0.5" />
                                <span className="leading-snug">{signal.replace(/^Positive:\s*/, "")}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Language Verification */}
                      {skills && ((skills.confirmed && skills.confirmed.length > 0) || (skills.unconfirmed && skills.unconfirmed.length > 0)) ? (
                        <div className="space-y-2 pt-2 border-t border-border/40">
                          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                            <Code2 className="h-3.5 w-3.5" />
                            <span>Language Verification</span>
                          </h4>
                          <div className="flex flex-wrap gap-1.5 items-center">
                            {skills.confirmed && skills.confirmed.length > 0 && (
                              <>
                                <span className="text-[11px] text-muted-foreground mr-1">Confirmed in code:</span>
                                {skills.confirmed.map((lang, idx) => (
                                  <Badge
                                    key={idx}
                                    variant="secondary"
                                    className="bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30 text-[11px] px-2 py-0.5 flex items-center gap-1"
                                  >
                                    <Check className="h-3 w-3 text-emerald-600 dark:text-emerald-400 shrink-0" />
                                    <span>{lang}</span>
                                  </Badge>
                                ))}
                              </>
                            )}
                            {skills.unconfirmed && skills.unconfirmed.length > 0 && (
                              <>
                                <span className="text-[11px] text-muted-foreground ml-2 mr-1">No repo evidence:</span>
                                {skills.unconfirmed.map((lang, idx) => (
                                  <Badge
                                    key={idx}
                                    variant="outline"
                                    className="text-muted-foreground border-border text-[11px] px-2 py-0.5"
                                  >
                                    {lang}
                                  </Badge>
                                ))}
                              </>
                            )}
                          </div>
                        </div>
                      ) : null}

                      {/* Audited Repositories Summary */}
                      {repos.length > 0 && (
                        <div className="space-y-2 pt-2 border-t border-border/40">
                          <div className="flex items-center justify-between">
                            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                              <GitFork className="h-3.5 w-3.5" />
                              <span>Audited Repositories ({repos.length})</span>
                            </h4>
                            <span className="text-[11px] text-muted-foreground hidden sm:inline">
                              Authenticity &amp; Code Quality Score
                            </span>
                          </div>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                            {repos.map((repo, idx) => {
                              const authorshipPct = repo.commits ? Math.round(((repo.own_commits || 0) / repo.commits) * 100) : 0;
                              const repoUrl =
                                repo.url ||
                                (username ? `https://github.com/${username}/${repo.name}` : null);

                              return (
                                <div
                                  key={idx}
                                  className="flex items-center justify-between p-2.5 rounded-lg bg-muted/30 border border-border/50 text-xs hover:border-border transition-colors"
                                >
                                  <div className="truncate mr-2">
                                    <div className="font-semibold text-foreground truncate flex items-center gap-1.5">
                                      <GitFork className="h-3 w-3 text-muted-foreground shrink-0" />
                                      {repoUrl ? (
                                        <a
                                          href={repoUrl}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          className="truncate hover:underline hover:text-primary flex items-center gap-1"
                                          title={`Open ${repo.name} on GitHub`}
                                        >
                                          <span>{repo.name}</span>
                                          <ExternalLink className="h-2.5 w-2.5 opacity-60 shrink-0" />
                                        </a>
                                      ) : (
                                        <span className="truncate">{repo.name}</span>
                                      )}
                                      {repo.is_fork && (
                                        <span className="text-[10px] text-muted-foreground uppercase px-1 py-0.5 rounded bg-muted font-normal">(Fork)</span>
                                      )}
                                    </div>
                                    <p className="text-[11px] text-muted-foreground mt-0.5">
                                      {repo.own_commits ?? 0} / {repo.commits ?? 0} commits ({authorshipPct}% own)
                                    </p>
                                  </div>
                                  <Badge
                                    variant="outline"
                                    className="font-mono text-[11px] shrink-0 font-semibold"
                                    title="Individual repository authenticity and code quality score (0-100) based on commit history, authorship, tests, CI/CD, and documentation"
                                  >
                                    Score: {repo.score}/100
                                  </Badge>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {/* Warnings if any */}
                      {warnings.length > 0 && (
                        <div className="pt-2 text-[11px] text-muted-foreground italic">
                          {warnings.join(" ")}
                        </div>
                      )}
                    </>
                  )}
                </CardContent>
              </Card>
            );
          })()}
        </div>
      )}
    </div>
  );
}

export default function ReviewPage() {
  return (
    <Suspense
      fallback={
        <div className="py-20 flex flex-col items-center justify-center gap-3 text-muted-foreground">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
          <p className="text-sm">Loading review page...</p>
        </div>
      }
    >
      <ReviewDashboard />
    </Suspense>
  );
}
