import { useEffect, useRef, useState } from "react";
import { request } from "../services/api";

/** Owns the selected run's live status, persisted samples, and event cursor. */
export default function useLiveRun({ runId, tab, refresh, setTab, setNotice }) {
  const [live, setLive] = useState(null);
  const [liveSamples, setLiveSamples] = useState([]);
  const [events, setEvents] = useState([]);
  const [liveError, setLiveError] = useState("");
  const eventCursor = useRef(0);
  const observedActiveRun = useRef("");
  useEffect(() => {
    setLive(null);
    setLiveSamples([]);
    setEvents([]);
    setLiveError("");
    eventCursor.current = 0;
    observedActiveRun.current = "";
  }, [runId]);
  useEffect(() => {
    if (!runId || tab !== "Training") return;
    let disposed = false,
      pending = false,
      timer = null;
    const poll = async () => {
      if (pending || disposed) return;
      pending = true;
      try {
        const data = await request(
          `/runs/${encodeURIComponent(runId)}/live-status?after=${eventCursor.current}`,
        );
        if (!disposed) {
          setLive(data);
          setLiveSamples(data.progress_samples || []);
          setLiveError("");
          eventCursor.current = data.next_cursor;
          setEvents((prev) => [...prev, ...data.events].slice(-300));

          const isActive =
            data.status === "RUNNING" ||
            data.status === "PENDING" ||
            data.status === "QUEUED" ||
            data.status === "EVALUATING";

          if (isActive) {
            observedActiveRun.current = runId;
            if (!timer) {
              timer = setInterval(poll, 1000);
            }
          } else {
            if (timer) {
              clearInterval(timer);
              timer = null;
            }
            refresh();
            if (
              data.status === "COMPLETED" &&
              observedActiveRun.current === runId
            ) {
              observedActiveRun.current = "";
              setNotice(
                "Training complete. Review this run against other candidates, then record your decision.",
              );
              setTab("Compare");
            }
          }
        }
      } catch (e) {
        if (!disposed) {
          setLiveError(e.message);
          if (timer) {
            clearInterval(timer);
          }
          timer = setInterval(poll, 3000);
        }
      } finally {
        pending = false;
      }
    };
    poll();
    return () => {
      disposed = true;
      if (timer) clearInterval(timer);
    };
  }, [runId, tab, refresh]);
  return {
    live,
    liveSamples,
    events,
    liveError,
  };
}
