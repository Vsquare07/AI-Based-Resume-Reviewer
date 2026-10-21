"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Trash2,
  ChevronLeft,
  ChevronRight,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { ReviewSummary, ReviewListResponse } from "@/types/review";
import { cn } from "cn";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function HistoryPage() {
  const router = useRouter();
  const [data, setData] = useState<ReviewListResponse>({
    items: [],
    total: 0,
    page: 1,
    size: 10,
    pages: 1,
  });
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);

  // Delete Confirmation State
  const [deleteTarget, setDeleteTarget] = useState<ReviewSummary | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const fetchReviews = useCallback(async (targetPage = 1) => {
    setLoading(true);
    try {
      const url = new URL(`${API_BASE}/api/reviews`);
      url.searchParams.set("page", String(targetPage));
      url.searchParams.set("size", "10");

      const res = await fetch(url.toString());
      if (!res.ok) {
        throw new Error(`Failed to fetch reviews (HTTP ${res.status})`);
      }
      const json: ReviewListResponse = await res.json();
      setData({
        items: json.items || json.reviews || [],
        total: json.total || 0,
        page: json.page || 1,
        size: json.size || 10,
        pages: json.pages || 1,
      });
      setPage(json.page || 1);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error fetching history";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchReviews(1);
  }, [fetchReviews]);

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      const res = await fetch(`${API_BASE}/api/reviews/${deleteTarget.id}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        throw new Error("Failed to delete review");
      }
      toast.success(`Deleted review for "${deleteTarget.candidate_name || deleteTarget.filename}"`);
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
      fetchReviews(page);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error deleting review";
      toast.error(msg);
    } finally {
      setDeleting(false);
    }
  };

  const getScoreBadge = (score: number) => {
    if (score >= 80) {
      return (
        <Badge className="bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30">
          {score} / 100
        </Badge>
      );
    }
    if (score >= 60) {
      return (
        <Badge className="bg-amber-500/15 text-amber-700 dark:text-amber-300 border border-amber-500/30">
          {score} / 100
        </Badge>
      );
    }
    return (
      <Badge variant="destructive" className="bg-rose-500/15 text-rose-700 dark:text-rose-300 border border-rose-500/30">
        {score} / 100
      </Badge>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight">Review History</h1>
          <p className="text-muted-foreground mt-1 text-sm sm:text-base">
            Click any row to open the candidate&apos;s evaluation dashboard.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => fetchReviews(page)} className="gap-2 shrink-0">
          <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
          <span>Refresh</span>
        </Button>
      </div>

      {/* History Table Card */}
      <Card className="border-border/60">
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[35%] pl-6 sm:pl-8">Candidate</TableHead>
                <TableHead className="w-[30%]">Target Job Title</TableHead>
                <TableHead className="w-[15%]">Overall Score</TableHead>
                <TableHead className="w-[15%]">Evaluated On</TableHead>
                <TableHead className="w-[5%] pr-6 text-right">
                  <span className="sr-only">Actions</span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={5} className="h-32 text-center text-muted-foreground">
                    <div className="flex items-center justify-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>Loading stored reviews...</span>
                    </div>
                  </TableCell>
                </TableRow>
              ) : data.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="h-32 text-center text-muted-foreground">
                    <p>No past reviews found.</p>
                    <Link href="/" className="text-primary text-xs underline mt-1 inline-block">
                      Submit a new resume review
                    </Link>
                  </TableCell>
                </TableRow>
              ) : (
                data.items.map((item) => (
                  <TableRow
                    key={item.id}
                    onClick={() => router.push(`/?reviewId=${item.id}`)}
                    className="cursor-pointer hover:bg-muted/60 transition-colors group"
                  >
                    <TableCell className="pl-6 sm:pl-8 font-semibold text-foreground">
                      <span className="truncate block max-w-xs">{item.candidate_name || "Candidate"}</span>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="font-medium">{item.job_title}</Badge>
                    </TableCell>
                    <TableCell>{getScoreBadge(item.score)}</TableCell>
                    <TableCell className="text-muted-foreground text-xs">
                      {new Date(item.created_at).toLocaleDateString(undefined, {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                      })}
                    </TableCell>
                    <TableCell className="pr-6 text-right" onClick={(e) => e.stopPropagation()}>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-muted-foreground hover:text-destructive"
                        onClick={(e) => {
                          e.stopPropagation();
                          setDeleteTarget(item);
                          setDeleteDialogOpen(true);
                        }}
                        title="Delete review"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Pagination Controls */}
      {data.pages > 1 && (
        <div className="flex items-center justify-between text-xs text-muted-foreground pt-2">
          <span>
            Showing page {data.page} of {data.pages} ({data.total} total reviews)
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1 || loading}
              onClick={() => fetchReviews(page - 1)}
              className="gap-1 h-8"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
              <span>Previous</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= data.pages || loading}
              onClick={() => fetchReviews(page + 1)}
              className="gap-1 h-8"
            >
              <span>Next</span>
              <ChevronRight className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold">Delete Review Record?</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the review for{" "}
              <strong>{deleteTarget?.candidate_name || deleteTarget?.filename}</strong> ({deleteTarget?.job_title})? This action
              cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              size="sm"
              disabled={deleting}
              onClick={() => setDeleteDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              size="sm"
              disabled={deleting}
              onClick={confirmDelete}
              className="gap-1.5"
            >
              {deleting && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              <span>Delete Review</span>
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
