import type { ReservationStatus } from "@/lib/api";
import { STATUS_LABELS } from "@/lib/format";
import { Badge, type BadgeTone } from "./ui";

const TONES: Record<ReservationStatus, BadgeTone> = {
  PENDING: "orange",
  AWAITING_TRAINING: "blue",
  APPROVED: "green",
  REJECTED: "red",
  CANCELLED: "gray",
  COMPLETED: "gray",
};

export function ReservationBadge({ status }: { status: ReservationStatus }) {
  return <Badge tone={TONES[status]}>{STATUS_LABELS[status]}</Badge>;
}
