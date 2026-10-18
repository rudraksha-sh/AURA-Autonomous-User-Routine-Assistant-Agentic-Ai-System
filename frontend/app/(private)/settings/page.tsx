"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowLeft, CircleAlert, LoaderCircle, Monitor, Moon, Save, Sun, Trash2, Upload } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { fetchProfile, removeProfilePhoto, saveProfile, saveThemePreference, uploadProfilePhoto, type Profile, type ThemePreference } from "@/services/profile";
import { useTheme } from "@/components/theme/ThemeProvider";

export default function SettingsPage() {
  const { theme, setThemePreference } = useTheme();
  const [profile, setProfile] = React.useState<Profile | null>(null);
  const [name, setName] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [loading, setLoading] = React.useState(true);
  const [busy, setBusy] = React.useState(false);
  const [themeBusy, setThemeBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [notice, setNotice] = React.useState<string | null>(null);

  const refresh = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchProfile();
      setProfile(data);
      setName(data.name);
      setEmail(data.email);
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to load your profile."); }
    finally { setLoading(false); }
  }, []);

  React.useEffect(() => {
    let active = true;
    fetchProfile().then((data) => {
      if (!active) return;
      setProfile(data); setName(data.name); setEmail(data.email);
    }).catch((err: unknown) => {
      if (active) setError(err instanceof Error ? err.message : "Unable to load your profile.");
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(null); setNotice(null);
    try {
      const updated = await saveProfile({ name, email });
      setProfile(updated); setName(updated.name); setEmail(updated.email); setNotice("Profile settings saved.");
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to save your profile."); }
    finally { setBusy(false); }
  }

  async function chooseTheme(nextTheme: ThemePreference) {
    if (nextTheme === theme || themeBusy) return;
    const previousTheme = theme;
    setThemePreference(nextTheme);
    setThemeBusy(true); setError(null); setNotice(null);
    try {
      const savedTheme = await saveThemePreference(nextTheme);
      setThemePreference(savedTheme);
      setNotice("Appearance preference saved.");
    } catch (err) {
      setThemePreference(previousTheme);
      setError(err instanceof Error ? `Could not save the appearance preference: ${err.message}` : "Could not save the appearance preference.");
    } finally { setThemeBusy(false); }
  }

  async function upload(file: File | undefined) {
    if (!file) return;
    setBusy(true); setError(null); setNotice(null);
    try {
      const updated = await uploadProfilePhoto(file);
      setProfile(updated); setNotice("Profile photo updated.");
      window.dispatchEvent(new Event("aura:profile-updated"));
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to upload the photo."); }
    finally { setBusy(false); }
  }

  async function removePhoto() {
    if (!window.confirm("Remove your profile photo?")) return;
    setBusy(true); setError(null); setNotice(null);
    try {
      setProfile(await removeProfilePhoto()); setNotice("Profile photo removed.");
      window.dispatchEvent(new Event("aura:profile-updated"));
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to remove the photo."); }
    finally { setBusy(false); }
  }

  return <div className="min-h-screen bg-slate-50 md:flex">
    <Sidebar />
    <div className="min-w-0 flex-1">
      <Header title="Settings" userName={profile?.name ?? ""} />
      <main className="mx-auto w-full max-w-4xl px-4 py-6 sm:px-6 md:px-8 md:py-8">
        <Link href="/dashboard" className="inline-flex items-center gap-2 rounded-lg text-sm font-medium text-slate-600 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"><ArrowLeft aria-hidden="true" className="size-4" />Back to dashboard</Link>
        <div className="mt-5">
          <h2 className="text-2xl font-bold tracking-tight text-slate-900">Account settings</h2>
          <p className="mt-1 text-sm text-slate-600">Update the profile details associated with your account.</p>
        </div>
        {error && <div role="alert" className="mt-5 flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"><CircleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0" /><span>{error}</span><button type="button" onClick={() => void refresh()} className="ml-auto font-semibold underline">Retry</button></div>}
        {notice && <p role="status" className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">{notice}</p>}
        {loading ? <p role="status" className="mt-6 text-sm text-slate-500">Loading account settings…</p> : profile && <div className="mt-6 grid gap-5">
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
            <fieldset disabled={themeBusy}>
              <legend className="text-base font-semibold text-slate-900">Appearance</legend>
              <p className="mt-1 text-sm text-slate-600">Choose how AURA looks. System Default follows your device setting.</p>
              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                {(["light", "dark", "system"] as const).map((choice) => {
                  const Icon = choice === "dark" ? Moon : choice === "system" ? Monitor : Sun;
                  const label = choice === "system" ? "System Default" : `${choice[0].toUpperCase()}${choice.slice(1)} Mode`;
                  return <label key={choice} className={`flex cursor-pointer items-center gap-3 rounded-xl border p-3 text-sm font-medium transition focus-within:ring-2 focus-within:ring-blue-600 ${theme === choice ? "border-blue-500 bg-blue-50 text-blue-800" : "border-slate-200 text-slate-700 hover:bg-slate-50"} ${themeBusy ? "cursor-wait opacity-60" : ""}`}>
                    <input type="radio" name="theme" value={choice} checked={theme === choice} onChange={() => void chooseTheme(choice)} className="size-4 accent-blue-600" />
                    <Icon aria-hidden="true" className="size-4" />
                    <span>{label}</span>
                  </label>;
                })}
              </div>
              {themeBusy && <p role="status" className="mt-3 text-sm text-slate-500">Saving appearance preference…</p>}
            </fieldset>
          </section>
          <form onSubmit={save} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
            <h3 className="text-base font-semibold text-slate-900">Profile</h3>
            <p className="mt-1 text-sm text-slate-600">Your name and email are used across AURA.</p>
            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <label className="grid gap-1.5 text-sm font-medium text-slate-700">Display name<input required maxLength={100} value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" className="rounded-lg border border-slate-300 px-3 py-2.5 font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" /></label>
              <label className="grid gap-1.5 text-sm font-medium text-slate-700">Email<input required type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" className="rounded-lg border border-slate-300 px-3 py-2.5 font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" /></label>
            </div>
            <div className="mt-5 flex flex-wrap items-center gap-3">
              <button disabled={busy} className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2">{busy ? <LoaderCircle className="size-4 animate-spin" /> : <Save className="size-4" />}Save profile</button>
              <span className="text-xs text-slate-500">Account role: {profile.role}</span>
            </div>
          </form>
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
            <h3 className="text-base font-semibold text-slate-900">Profile photo</h3>
            {profile.role === "admin" ? <>
              <p className="mt-1 text-sm text-slate-600">Administrators can upload a JPEG, PNG, or WebP image up to 5 MB.</p>
              <div className="mt-4 flex flex-wrap gap-3">
                <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 focus-within:ring-2 focus-within:ring-blue-600"><Upload aria-hidden="true" className="size-4" />{profile.profile_photo_available ? "Replace photo" : "Upload photo"}<input type="file" accept="image/jpeg,image/png,image/webp" disabled={busy} onChange={(e) => { void upload(e.target.files?.[0]); e.currentTarget.value = ""; }} className="sr-only" /></label>
                {profile.profile_photo_available && <button type="button" disabled={busy} onClick={() => void removePhoto()} className="inline-flex items-center gap-2 rounded-lg border border-rose-200 px-4 py-2.5 text-sm font-semibold text-rose-700 hover:bg-rose-50 disabled:opacity-60"><Trash2 aria-hidden="true" className="size-4" />Remove photo</button>}
              </div>
            </> : <p className="mt-1 text-sm text-slate-600">Profile photo management is available to administrator accounts.</p>}
          </section>
        </div>}
      </main>
    </div>
  </div>;
}
