import type { ReactNode } from "react";
import { AuthGate } from "@/components/auth/AuthGate";
import { VoiceAssistant } from "@/components/assistant/VoiceAssistant";

export default function PrivateLayout({ children }: { children: ReactNode }) {
  return <AuthGate>{children}<VoiceAssistant /></AuthGate>;
}
