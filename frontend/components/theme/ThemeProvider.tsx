"use client";

import * as React from "react";
import { getAccessToken } from "@/services/auth-storage";
import { fetchThemePreference, type ThemePreference } from "@/services/profile";

type ThemeContextValue = {
  theme: ThemePreference;
  setThemePreference: (theme: ThemePreference) => void;
};
const ThemeContext = React.createContext<ThemeContextValue | null>(null);
const STORAGE_KEY = "aura_theme";

function readTheme(value: string | null): ThemePreference {
  return value === "light" || value === "dark" || value === "system" ? value : "system";
}

function applyTheme(theme: ThemePreference) {
  const systemPrefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  document.documentElement.classList.toggle("dark", theme === "dark" || (theme === "system" && systemPrefersDark));
  document.documentElement.style.colorScheme = theme === "system" ? "light dark" : theme;
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = React.useState<ThemePreference>("system");
  const themeRef = React.useRef<ThemePreference>("system");
  const preferenceChangeVersion = React.useRef(0);

  const commitTheme = React.useCallback((next: ThemePreference) => {
    preferenceChangeVersion.current += 1;
    themeRef.current = next;
    window.localStorage.setItem(STORAGE_KEY, next);
    applyTheme(next);
    setTheme(next);
  }, []);

  React.useEffect(() => {
    let active = true;
    const localTheme = readTheme(window.localStorage.getItem(STORAGE_KEY));
    themeRef.current = localTheme;
    applyTheme(localTheme);
    void Promise.resolve().then(() => { if (active) setTheme(localTheme); });

    const syncAccountTheme = async () => {
      if (!getAccessToken()) return;
      const versionAtStart = preferenceChangeVersion.current;
      try {
        const preference = await fetchThemePreference();
        if (!active || versionAtStart !== preferenceChangeVersion.current) return;
        themeRef.current = preference.theme;
        window.localStorage.setItem(STORAGE_KEY, preference.theme);
        applyTheme(preference.theme);
        setTheme(preference.theme);
      } catch {
        // Keep the device preference when the account preference is unavailable.
      }
    };
    const handleStorage = (event: StorageEvent) => {
      if (event.key !== STORAGE_KEY) return;
      preferenceChangeVersion.current += 1;
      const next = readTheme(event.newValue);
      themeRef.current = next;
      applyTheme(next);
      setTheme(next);
    };
    const handleSystemChange = () => {
      if (themeRef.current === "system") applyTheme("system");
    };

    window.addEventListener("aura:auth-changed", syncAccountTheme);
    window.addEventListener("storage", handleStorage);
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    media.addEventListener("change", handleSystemChange);
    void syncAccountTheme();
    return () => {
      active = false;
      window.removeEventListener("aura:auth-changed", syncAccountTheme);
      window.removeEventListener("storage", handleStorage);
      media.removeEventListener("change", handleSystemChange);
    };
  }, []);

  React.useEffect(() => {
    // The early root-layout script applies saved preferences before hydration.
    if (readTheme(window.localStorage.getItem(STORAGE_KEY)) === theme) applyTheme(theme);
  }, [theme]);

  return <ThemeContext.Provider value={{ theme, setThemePreference: commitTheme }}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const context = React.useContext(ThemeContext);
  if (!context) throw new Error("useTheme must be used within ThemeProvider");
  return context;
}
