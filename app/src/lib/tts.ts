import * as Speech from "expo-speech";

/**
 * Speak the briefing summary. Prefers an Indian-English voice when present.
 * Devanagari text falls back to a Hindi voice so Hindi replies sound natural.
 */
export async function speak(text: string, onDone?: () => void): Promise<void> {
  await Speech.stop();
  const containsDevanagari = /[ऀ-ॿ]/.test(text);
  Speech.speak(text, {
    language: containsDevanagari ? "hi-IN" : "en-IN",
    rate: 0.98,
    pitch: 1.0,
    onDone,
    onStopped: onDone,
    onError: onDone,
  });
}

export function stopSpeaking(): Promise<void> {
  return Speech.stop();
}

export function isSpeaking(): Promise<boolean> {
  return Speech.isSpeakingAsync();
}
