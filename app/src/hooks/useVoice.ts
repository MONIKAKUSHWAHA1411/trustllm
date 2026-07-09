import { useCallback, useRef, useState } from "react";
import {
  ExpoSpeechRecognitionModule,
  useSpeechRecognitionEvent,
} from "expo-speech-recognition";

export type VoiceState = "idle" | "listening" | "processing";

interface UseVoiceOptions {
  /** Called once with the final transcript after the user stops speaking. */
  onFinalTranscript: (transcript: string) => void;
  locale?: string;
}

/**
 * Tap-to-talk wrapper around the native iOS speech recognizer
 * (SFSpeechRecognizer via expo-speech-recognition).
 */
export function useVoice({ onFinalTranscript, locale = "en-IN" }: UseVoiceOptions) {
  const [state, setState] = useState<VoiceState>("idle");
  const [partial, setPartial] = useState("");
  const [error, setError] = useState<string | null>(null);
  // Keep the latest transcript here; "result" fires repeatedly with interim text.
  const lastTranscript = useRef("");
  const submitted = useRef(false);

  useSpeechRecognitionEvent("start", () => {
    setState("listening");
    setPartial("");
    setError(null);
    lastTranscript.current = "";
    submitted.current = false;
  });

  useSpeechRecognitionEvent("result", (event) => {
    const transcript = event.results?.[0]?.transcript ?? "";
    lastTranscript.current = transcript;
    setPartial(transcript);
  });

  useSpeechRecognitionEvent("end", () => {
    const text = lastTranscript.current.trim();
    if (text && !submitted.current) {
      submitted.current = true;
      setState("processing");
      onFinalTranscript(text);
    } else if (!submitted.current) {
      setState("idle");
    }
  });

  useSpeechRecognitionEvent("error", (event) => {
    // "no-speech" is a normal outcome of tapping and saying nothing.
    if (event.error !== "no-speech") {
      setError(event.message || event.error || "Speech recognition failed");
    }
    setState("idle");
  });

  const start = useCallback(async () => {
    const perms = await ExpoSpeechRecognitionModule.requestPermissionsAsync();
    if (!perms.granted) {
      setError("Microphone and speech permissions are required.");
      return;
    }
    ExpoSpeechRecognitionModule.start({
      lang: locale,
      interimResults: true,
      continuous: false,
    });
  }, [locale]);

  const stop = useCallback(() => {
    ExpoSpeechRecognitionModule.stop();
  }, []);

  /** Call when the backend round-trip finishes (success or failure). */
  const done = useCallback(() => {
    setState("idle");
    setPartial("");
  }, []);

  return { state, partial, error, start, stop, done, setError };
}
