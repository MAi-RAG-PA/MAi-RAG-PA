// frontend/src/hooks/useEventNotifications.ts
import { useEffect, useRef } from "react";
import apiClient from "../api/client";

const DEFAULT_INTERVALS = [
  { label: "24h", minutes: 1440, enabled: true },
  { label: "1h", minutes: 60, enabled: true },
  { label: "30m", minutes: 30, enabled: true },
  { label: "15m", minutes: 15, enabled: true },
  { label: "5m", minutes: 5, enabled: true },
  { label: "0m", minutes: 0, enabled: true },
];

interface NotificationRecord {
  eventId: string;
  interval: string;
  notifiedAt: string;
}

interface NotificationIntervalSetting {
  label: string;
  minutes: number;
  enabled: boolean;
}

const NOTIFICATION_SOUND_URL = "/sounds/notification.mp3";
const STORAGE_KEY = "notification-history";

export const useEventNotifications = (showToast: (msg: string) => void) => {
  const notificationHistory = useRef<NotificationRecord[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const isAudioReady = useRef(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const audio = new Audio(NOTIFICATION_SOUND_URL);
    audio.preload = "auto";
    audio.volume = 0.7;
    audioRef.current = audio;

    const handleCanPlayThrough = () => {
      isAudioReady.current = true;
    };

    audio.addEventListener("canplaythrough", handleCanPlayThrough, { once: true });
    audio.load();

    const unlockAudio = () => {
      if (audioRef.current && !isAudioReady.current) {
        audioRef.current
          .play()
          .then(() => {
            audioRef.current?.pause();
            if (audioRef.current) {
              audioRef.current.currentTime = 0;
            }
            isAudioReady.current = true;
          })
          .catch((err) => console.warn("Audio unlock failed:", err));
      }
    };

    document.addEventListener("click", unlockAudio, { once: true });
    document.addEventListener("keydown", unlockAudio, { once: true });

    return () => {
      audio.removeEventListener("canplaythrough", handleCanPlayThrough);
      document.removeEventListener("click", unlockAudio);
      document.removeEventListener("keydown", unlockAudio);
      audio.pause();
      audioRef.current = null;
    };
  }, []);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as NotificationRecord[];
        notificationHistory.current = Array.isArray(parsed) ? parsed : [];
      }
    } catch (err) {
      console.error("Failed to load notification history:", err);
      notificationHistory.current = [];
    }

    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }

    const saveNotificationHistory = () => {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(notificationHistory.current));
      } catch (err) {
        console.error("Failed to save notification history:", err);
      }
    };

    const hasBeenNotified = (eventId: string, interval: string): boolean => {
      return notificationHistory.current.some(
        (record) => record.eventId === eventId && record.interval === interval
      );
    };

    const recordNotification = (eventId: string, interval: string) => {
      notificationHistory.current.push({
        eventId,
        interval,
        notifiedAt: new Date().toISOString(),
      });
      saveNotificationHistory();
    };

    const playNotificationSound = async () => {
      if (!audioRef.current) return;

      try {
        audioRef.current.currentTime = 0;
        await audioRef.current.play();
      } catch (err) {
        console.error("Failed to play notification sound:", err);
      }
    };

    const processItems = (
      items: unknown,
      now: Date,
      userIntervals: NotificationIntervalSetting[]
    ) => {
      if (!Array.isArray(items)) return;

      items.forEach((item: any) => {
        const dueTimeStr = item.start_time || item.due_time;
        if (!dueTimeStr) return;

        const dueTime = new Date(dueTimeStr);
        const timeDiffMinutes = (dueTime.getTime() - now.getTime()) / (1000 * 60);

        userIntervals.forEach(({ label, minutes, enabled }) => {
          if (!enabled) return;
          if (hasBeenNotified(item.id, label)) return;

          const windowStart = minutes - 2;
          const windowEnd = minutes + 2;

          if (timeDiffMinutes >= windowStart && timeDiffMinutes <= windowEnd) {
            recordNotification(item.id, label);

            const title = item.title || item.text || "Untitled item";
            let message = "";

            if (label === "24h") message = `Tomorrow: ${title}`;
            else if (label === "1h") message = `In 1 hour: ${title}`;
            else if (label === "30m") message = `In 30 minutes: ${title}`;
            else if (label === "15m") message = `In 15 minutes: ${title}`;
            else if (label === "5m") message = `In 5 minutes: ${title}`;
            else if (label === "0m") message = `Now: ${title}`;

            showToast(message);
            void playNotificationSound();
          }
        });
      });
    };

    const checkNotifications = async () => {
      try {
        const settingsRes = await apiClient.get("/api/settings/notifications");
        const userIntervals = (settingsRes.data.intervals || DEFAULT_INTERVALS) as NotificationIntervalSetting[];

        const response = await apiClient.get("/api/memory/sqlite/notifications/due-soon");
        const events = response.data?.events || [];
        const reminders = response.data?.reminders || [];

        if (events.length === 0 && reminders.length === 0) {
          return;
        }

        const now = new Date();
        processItems(events, now, userIntervals);
        processItems(reminders, now, userIntervals);
      } catch (err) {
        console.error("Background notification check failed", err);
      }
    };

    void checkNotifications();
    intervalRef.current = setInterval(checkNotifications, 30000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [showToast]);
};
