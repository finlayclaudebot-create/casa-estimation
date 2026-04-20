import { z } from "zod";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export const PlanCreatedResponseSchema = z.object({
  plan_id: z.string().uuid(),
  filename: z.string(),
  page_count: z.number().int(),
  uploaded_at: z.string(),
});
export type PlanCreatedResponse = z.infer<typeof PlanCreatedResponseSchema>;

export const TriggerResponseSchema = z.object({
  takeoff_id: z.string().uuid(),
  status: z.string(),
  poll_url: z.string(),
});
export type TriggerResponse = z.infer<typeof TriggerResponseSchema>;

const MatchKeySchema = z.object({
  category: z.string(),
  dimensions: z
    .object({
      width_mm: z.number().nullable().optional(),
      height_mm: z.number().nullable().optional(),
      length_mm: z.number().nullable().optional(),
    })
    .passthrough(),
  attributes: z.record(z.unknown()),
  quantity_unit: z.string(),
});

export const TakeoffElementSchema = z.object({
  id: z.string().uuid(),
  element_type: z.string(),
  element_subtype: z.string().nullable(),
  schedule_id: z.string().nullable(),
  properties: z.record(z.unknown()).nullable(),
  source: z.string(),
  confidence: z.union([z.string(), z.number()]),
  status: z.string(),
  match_key: MatchKeySchema,
});
export type TakeoffElement = z.infer<typeof TakeoffElementSchema>;

const ProcessingStepSchema = z.object({
  name: z.string(),
  status: z.string(),
  started_at: z.string().nullable().optional(),
  finished_at: z.string().nullable().optional(),
  detail: z.record(z.unknown()).nullable().optional(),
});

export const TakeoffSchema = z.object({
  id: z.string().uuid(),
  plan_id: z.string().uuid(),
  status: z.string(),
  started_at: z.string(),
  completed_at: z.string().nullable(),
  error_message: z.string().nullable(),
  total_confidence: z.union([z.string(), z.number()]).nullable(),
  processing_log: z
    .object({ steps: z.array(ProcessingStepSchema).optional() })
    .nullable()
    .optional(),
  door_count: z.number().int(),
  window_count: z.number().int(),
  elements: z.array(TakeoffElementSchema),
});
export type Takeoff = z.infer<typeof TakeoffSchema>;

async function parseError(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: string };
    return body.detail ?? `HTTP ${res.status}`;
  } catch {
    return `HTTP ${res.status}`;
  }
}

export async function uploadPlan(file: File): Promise<PlanCreatedResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE_URL}/plans`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(await parseError(res));
  return PlanCreatedResponseSchema.parse(await res.json());
}

export async function triggerTakeoff(planId: string): Promise<TriggerResponse> {
  const res = await fetch(`${API_BASE_URL}/plans/${planId}/takeoff`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await parseError(res));
  return TriggerResponseSchema.parse(await res.json());
}

export async function getLatestTakeoff(planId: string): Promise<Takeoff> {
  const res = await fetch(`${API_BASE_URL}/plans/${planId}/takeoffs/latest`);
  if (!res.ok) throw new Error(await parseError(res));
  return TakeoffSchema.parse(await res.json());
}

export async function getTakeoff(takeoffId: string): Promise<Takeoff> {
  const res = await fetch(`${API_BASE_URL}/takeoffs/${takeoffId}`);
  if (!res.ok) throw new Error(await parseError(res));
  return TakeoffSchema.parse(await res.json());
}

export const TERMINAL_STATUSES = new Set(["completed", "needs_review", "failed"]);
