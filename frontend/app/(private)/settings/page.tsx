"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, CircleAlert, LoaderCircle, Save, Trash2, Upload, Unplug, Link2 } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { changePassword, fetchAppearancePreferences, fetchProfile, removeProfilePhoto, saveAppearancePreferences, saveProfile, uploadProfilePhoto, type AppearancePreferences, type Profile } from "@/services/profile";
import { getPlanningPreferences, savePlanningPreferences } from "@/services/planner";
import type { PlanningPreferences } from "@/types/planner";
import { clearAccessToken } from "@/services/auth-storage";
import { useTheme } from "@/components/theme/ThemeProvider";
import { disconnectGoogleIntegration, getGoogleConnectUrl, getGoogleIntegrationStatus, type GoogleIntegrationStatus } from "@/services/integrations";
import { getNotificationPreferences, saveNotificationPreferences, type NotificationPreferences } from "@/services/notifications";
import { getAIPlanningPreference, getAIProviderStatus, saveAIPlanningPreference, type AIProviderStatus } from "@/services/ai-settings";
import { deleteAccount as deleteAccountRequest, downloadAccountExport } from "@/services/account-data";

const TABS = ["Profile", "Appearance", "Planning", "Integrations", "Notifications", "AI", "Data and account"] as const;
type Tab = (typeof TABS)[number];
const intlTimeZones = Intl as typeof Intl & { supportedValuesOf?: (key: "timeZone") => string[] };
const TIME_ZONES = [
  ...new Set([
    "UTC",
    ...(intlTimeZones.supportedValuesOf?.("timeZone") ?? ["Asia/Kolkata", "America/New_York", "Europe/London", "Asia/Tokyo"]),
  ]),
].sort();

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <section className={`rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6 ${className}`}>{children}</section>;
}

function TextField({ label, ...props }: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return <label className="grid gap-1.5 text-sm font-medium text-slate-700">{label}<input {...props} className={`rounded-lg border border-slate-300 px-3 py-2.5 font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 ${props.className ?? ""}`} /></label>;
}

export default function SettingsPage() {
  const router = useRouter();
  const { setThemePreference } = useTheme();
  const [activeTab, setActiveTab] = React.useState<Tab>("Profile");
  const [profile, setProfile] = React.useState<Profile | null>(null);
  const [name, setName] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [appearance, setAppearance] = React.useState<AppearancePreferences>({ theme: "system", accent_color: "blue", density: "comfortable", font_size: "medium" });
  const [savedAppearance, setSavedAppearance] = React.useState<AppearancePreferences>({ theme: "system", accent_color: "blue", density: "comfortable", font_size: "medium" });
  const [planning, setPlanning] = React.useState<PlanningPreferences>({ timezone_name: "UTC", workday_start: "09:00", workday_end: "17:00", preferred_session_minutes: 50, break_minutes: 10, daily_capacity_minutes: 360 });
  const [savedPlanning, setSavedPlanning] = React.useState<PlanningPreferences>({ timezone_name: "UTC", workday_start: "09:00", workday_end: "17:00", preferred_session_minutes: 50, break_minutes: 10, daily_capacity_minutes: 360 });
  const [googleStatus, setGoogleStatus] = React.useState<GoogleIntegrationStatus | null>(null);
  const [integrationLoading, setIntegrationLoading] = React.useState(true);
  const [notifications, setNotifications] = React.useState<NotificationPreferences>({ due_soon_reminders: true, overdue_alerts: true, weekly_summary: false, reminder_lead_time_minutes: 60 });
  const [savedNotifications, setSavedNotifications] = React.useState<NotificationPreferences>({ due_soon_reminders: true, overdue_alerts: true, weekly_summary: false, reminder_lead_time_minutes: 60 });
  const [useAIPlanning, setUseAIPlanning] = React.useState(true);
  const [savedUseAIPlanning, setSavedUseAIPlanning] = React.useState(true);
  const [aiStatus, setAIStatus] = React.useState<AIProviderStatus | null>(null);
  const [aiLoading, setAILoading] = React.useState(true);
  const [deleteConfirmation, setDeleteConfirmation] = React.useState("");
  const [currentPassword, setCurrentPassword] = React.useState("");
  const [newPassword, setNewPassword] = React.useState("");
  const [confirmPassword, setConfirmPassword] = React.useState("");
  const [loading, setLoading] = React.useState(true);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [notice, setNotice] = React.useState<string | null>(null);
  const lastAction = React.useRef<(() => Promise<void>) | null>(null);
  const profileDirty = Boolean(profile && (name !== profile.name || email !== profile.email));
  const appearanceDirty = JSON.stringify(appearance) !== JSON.stringify(savedAppearance);
  const planningDirty = JSON.stringify(planning) !== JSON.stringify(savedPlanning);
  const notificationsDirty = JSON.stringify(notifications) !== JSON.stringify(savedNotifications);
  const aiDirty = useAIPlanning !== savedUseAIPlanning;
  const dirty = profileDirty || appearanceDirty || planningDirty || notificationsDirty || aiDirty;

  const refresh = React.useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const data = await fetchProfile();
      setProfile(data); setName(data.name); setEmail(data.email);
    } catch (err) {
      if (err instanceof Error && "status" in err && err.status === 401) { clearAccessToken(); router.replace("/login"); return; }
      setError(err instanceof Error ? err.message : "Unable to load your profile.");
    } finally { setLoading(false); }
  }, [router]);

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

  React.useEffect(() => {
    let active = true;
    Promise.all([getAIPlanningPreference(), getAIProviderStatus()]).then(([preference, status]) => {
      if (active) { setUseAIPlanning(preference.use_ai_planning); setSavedUseAIPlanning(preference.use_ai_planning); setAIStatus(status); }
    }).catch((err: unknown) => {
      if (active && !(err instanceof Error && "status" in err && err.status === 401)) setError(err instanceof Error ? err.message : "Unable to load AI settings.");
    }).finally(() => { if (active) setAILoading(false); });
    return () => { active = false; };
  }, []);

  React.useEffect(() => {
    let active = true;
    getNotificationPreferences().then((data) => { if (active) { setNotifications(data); setSavedNotifications(data); } })
      .catch((err: unknown) => { if (active && !(err instanceof Error && "status" in err && err.status === 401)) setError(err instanceof Error ? err.message : "Unable to load notification settings."); });
    return () => { active = false; };
  }, []);

  const refreshGoogleStatus = React.useCallback(async () => {
    lastAction.current = refreshGoogleStatus;
    setIntegrationLoading(true);
    try { setGoogleStatus(await getGoogleIntegrationStatus()); }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to load Google connection status."); }
    finally { setIntegrationLoading(false); }
  }, []);

  React.useEffect(() => {
    let active = true;
    getGoogleIntegrationStatus().then((status) => { if (active) setGoogleStatus(status); })
      .catch((err: unknown) => { if (active) setError(err instanceof Error ? err.message : "Unable to load Google connection status."); })
      .finally(() => { if (active) setIntegrationLoading(false); });
    return () => { active = false; };
  }, []);

  async function connectGoogle() {
    lastAction.current = connectGoogle;
    setBusy(true); setError(null); setNotice(null);
    try { const result = await getGoogleConnectUrl(); window.location.assign(result.authorization_url); }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to start Google connection."); }
    finally { setBusy(false); }
  }

  async function disconnectGoogle() {
    lastAction.current = disconnectGoogle;
    setBusy(true); setError(null); setNotice(null);
    try {
      await disconnectGoogleIntegration();
      setGoogleStatus({ status: "disconnected", scopes: [], last_sync_at: null });
      setNotice("Google Calendar disconnected and stored credentials removed.");
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to disconnect Google Calendar."); }
    finally { setBusy(false); }
  }

  async function exportData(format: "json" | "csv") {
    setBusy(true); setError(null); setNotice(null);
    const action = async () => { await downloadAccountExport(format); setError(null); setNotice(`Your ${format.toUpperCase()} export is ready.`); };
    lastAction.current = action;
    try { await action(); }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to export your data."); }
    finally { setBusy(false); }
  }

  async function deleteAccount() {
    if (deleteConfirmation !== "DELETE") return;
    lastAction.current = deleteAccount;
    setBusy(true); setError(null);
    try {
      await deleteAccountRequest();
      clearAccessToken();
      router.replace("/login");
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to delete your account."); }
    finally { setBusy(false); }
  }

  React.useEffect(() => {
    let active = true;
    fetchAppearancePreferences().then((data) => {
      if (!active) return;
      setAppearance(data); setSavedAppearance(data); setThemePreference(data.theme);
      document.documentElement.dataset.auraAccent = data.accent_color;
      document.documentElement.dataset.auraDensity = data.density;
      document.documentElement.dataset.auraFontSize = data.font_size;
    }).catch((err: unknown) => {
      if (active) setError(err instanceof Error ? err.message : "Unable to load appearance settings.");
    });
    return () => { active = false; };
  }, [setThemePreference]);

  React.useEffect(() => {
    let active = true;
    getPlanningPreferences().then((data) => {
      if (!active) return;
      const values = { ...data, workday_start: data.workday_start.slice(0, 5), workday_end: data.workday_end.slice(0, 5) };
      setPlanning(values); setSavedPlanning(values);
    }).catch((err: unknown) => {
      if (active && !(err instanceof Error && "status" in err && err.status === 401)) setError(err instanceof Error ? err.message : "Unable to load planning settings.");
    });
    return () => { active = false; };
  }, []);

  async function saveAllChanges() {
    setBusy(true); setError(null); setNotice(null);
    try {
      if (profileDirty) {
        const updated = await saveProfile({ name, email });
        setProfile(updated); setName(updated.name); setEmail(updated.email);
        window.dispatchEvent(new Event("aura:profile-updated"));
      }
      if (appearanceDirty) {
        const updated = await saveAppearancePreferences(appearance);
        setAppearance(updated); setSavedAppearance(updated); setThemePreference(updated.theme);
        document.documentElement.dataset.auraAccent = updated.accent_color;
        document.documentElement.dataset.auraDensity = updated.density;
        document.documentElement.dataset.auraFontSize = updated.font_size;
      }
      if (planningDirty) {
        const updated = await savePlanningPreferences(planning);
        const normalized = { ...updated, workday_start: updated.workday_start.slice(0, 5), workday_end: updated.workday_end.slice(0, 5) };
        setPlanning(normalized); setSavedPlanning(normalized);
      }
      if (notificationsDirty) {
        const updated = await saveNotificationPreferences(notifications);
        setNotifications(updated); setSavedNotifications(updated);
      }
      if (aiDirty) {
        const updated = await saveAIPlanningPreference(useAIPlanning);
        setUseAIPlanning(updated.use_ai_planning); setSavedUseAIPlanning(updated.use_ai_planning);
      }
      setNotice("Settings saved.");
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to save your settings."); }
    finally { setBusy(false); }
  }

  async function submitPassword(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(null); setNotice(null);
    if (newPassword !== confirmPassword) { setError("The new password and confirmation do not match."); return; }
    if (newPassword.length < 8) { setError("Use at least 8 characters for your new password."); return; }
    setBusy(true);
    const action = async () => {
      await changePassword({ current_password: currentPassword, new_password: newPassword });
      setCurrentPassword(""); setNewPassword(""); setConfirmPassword("");
      setNotice("Password changed. Other sessions have been signed out."); setError(null);
    };
    lastAction.current = action;
    try { await action(); }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to change your password."); }
    finally { setBusy(false); }
  }

  async function upload(file: File | undefined) {
    if (!file) return;
    lastAction.current = () => upload(file);
    setBusy(true); setError(null); setNotice(null);
    try { setProfile(await uploadProfilePhoto(file)); setNotice("Profile photo updated."); window.dispatchEvent(new Event("aura:profile-updated")); }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to upload the photo."); }
    finally { setBusy(false); }
  }

  async function removePhoto() {
    if (!window.confirm("Remove your profile photo?")) return;
    lastAction.current = removePhoto;
    setBusy(true); setError(null); setNotice(null);
    try { setProfile(await removeProfilePhoto()); setNotice("Profile photo removed."); window.dispatchEvent(new Event("aura:profile-updated")); }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to remove the photo."); }
    finally { setBusy(false); }
  }

  function onTabKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
    event.preventDefault();
    const offset = event.key === "ArrowRight" ? 1 : -1;
    const next = (TABS.indexOf(activeTab) + offset + TABS.length) % TABS.length;
    setActiveTab(TABS[next]);
    document.getElementById(`settings-tab-${next}`)?.focus();
  }

  return <div className="min-h-screen bg-slate-50 md:flex">
    <Sidebar />
    <div className="min-w-0 flex-1">
      <Header title="Settings" userName={profile?.name ?? ""} />
      <main className="mx-auto w-full max-w-4xl px-4 py-6 sm:px-6 md:px-8 md:py-8">
        <Link href="/dashboard" className="inline-flex items-center gap-2 rounded-lg text-sm font-medium text-slate-600 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"><ArrowLeft aria-hidden="true" className="size-4" />Back to dashboard</Link>
        <div className="mt-5"><h2 className="text-2xl font-bold tracking-tight text-slate-900">Account settings</h2><p className="mt-1 text-sm text-slate-600">Manage your profile, preferences, and AURA account.</p></div>
        {error && <div role="alert" className="mt-5 flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"><CircleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0" /><span>{error}</span><button type="button" onClick={() => { if (lastAction.current) void lastAction.current(); else void refresh(); }} className="ml-auto font-semibold underline">Retry</button></div>}
        {notice && <p role="status" className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">{notice}</p>}
        <div role="tablist" aria-label="Settings sections" onKeyDown={onTabKeyDown} className="mt-6 flex gap-1 overflow-x-auto rounded-xl border border-slate-200 bg-white p-1 shadow-sm">
          {TABS.map((tab, index) => <button key={tab} id={`settings-tab-${index}`} type="button" role="tab" aria-selected={activeTab === tab} aria-controls="settings-panel" tabIndex={activeTab === tab ? 0 : -1} onClick={() => setActiveTab(tab)} className={`shrink-0 rounded-lg px-3 py-2 text-sm font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 ${activeTab === tab ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"}`}>{tab}</button>)}
        </div>
        <div id="settings-panel" role="tabpanel" aria-labelledby={`settings-tab-${TABS.indexOf(activeTab)}`} className="mt-5 grid gap-5">
          {loading ? <p role="status" className="text-sm text-slate-500">Loading account settings…</p> : profile && activeTab === "Profile" && <>
            <form onSubmit={(event) => { event.preventDefault(); lastAction.current = saveAllChanges; void saveAllChanges(); }} className="grid gap-5">
              <Card><h3 className="text-base font-semibold text-slate-900">Profile</h3><p className="mt-1 text-sm text-slate-600">Your name and email are used across AURA.</p><div className="mt-5 grid gap-4 sm:grid-cols-2"><TextField label="Display name" required maxLength={100} value={name} onChange={(event) => setName(event.target.value)} autoComplete="name" /><TextField label="Email" required type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" /></div><p className="mt-4 text-xs text-slate-500">Account role: {profile.role}</p></Card>
            </form>
            <form onSubmit={(event) => void submitPassword(event)} className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
              <div><h3 className="text-base font-semibold text-slate-900">Change password</h3><p className="mt-1 text-sm text-slate-600">Confirm your current password. Changing it signs out your other sessions.</p></div>
              <TextField label="Current password" type="password" required minLength={8} maxLength={128} autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} />
              <div className="grid gap-4 sm:grid-cols-2"><TextField label="New password" type="password" required minLength={8} maxLength={128} autoComplete="new-password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} /><TextField label="Confirm new password" type="password" required minLength={8} maxLength={128} autoComplete="new-password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} /></div>
              <div><button disabled={busy || !currentPassword || !newPassword || !confirmPassword} className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600">{busy ? <LoaderCircle className="size-4 animate-spin" /> : <Save className="size-4" />}Change password</button></div>
            </form>
            <Card><h3 className="text-base font-semibold text-slate-900">Profile photo</h3>{profile.role === "admin" ? <><p className="mt-1 text-sm text-slate-600">Administrators can upload a JPEG, PNG, or WebP image up to 5 MB.</p><div className="mt-4 flex flex-wrap gap-3"><label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 focus-within:ring-2 focus-within:ring-blue-600"><Upload aria-hidden="true" className="size-4" />{profile.profile_photo_available ? "Replace photo" : "Upload photo"}<input type="file" accept="image/jpeg,image/png,image/webp" disabled={busy} onChange={(event) => { void upload(event.target.files?.[0]); event.currentTarget.value = ""; }} className="sr-only" /></label>{profile.profile_photo_available && <button type="button" disabled={busy} onClick={() => void removePhoto()} className="inline-flex items-center gap-2 rounded-lg border border-rose-200 px-4 py-2.5 text-sm font-semibold text-rose-700 hover:bg-rose-50 disabled:opacity-60"><Trash2 aria-hidden="true" className="size-4" />Remove photo</button>}</div></> : <p className="mt-1 text-sm text-slate-600">Profile photo management is available to administrator accounts.</p>}</Card>
          </>}
          {!loading && activeTab === "Appearance" && <>
            <Card>
              <h3 className="text-base font-semibold text-slate-900">Appearance</h3>
              <p className="mt-1 text-sm text-slate-600">Adjust the colors and spacing used throughout AURA.</p>
              <fieldset className="mt-5" disabled={busy}>
                <legend className="text-sm font-medium text-slate-700">Color theme</legend>
                <div className="mt-3 grid gap-3 sm:grid-cols-3">{(["light", "dark", "system"] as const).map((value) => <label key={value} className={`flex cursor-pointer items-center gap-3 rounded-xl border p-3 text-sm font-medium focus-within:ring-2 focus-within:ring-blue-600 ${appearance.theme === value ? "border-blue-500 bg-blue-50 text-blue-800" : "border-slate-200 text-slate-700 hover:bg-slate-50"}`}><input type="radio" name="appearance-theme" checked={appearance.theme === value} onChange={() => setAppearance({ ...appearance, theme: value })} className="size-4 accent-blue-600" /><span>{value === "system" ? "System Default" : `${value[0].toUpperCase()}${value.slice(1)} mode`}</span></label>)}</div>
              </fieldset>
              <div className="mt-5 grid gap-4 sm:grid-cols-3">
                <label className="grid gap-1.5 text-sm font-medium text-slate-700">Accent color<select value={appearance.accent_color} onChange={(event) => setAppearance({ ...appearance, accent_color: event.target.value as AppearancePreferences["accent_color"] })} className="rounded-lg border border-slate-300 bg-white px-3 py-2.5 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100">{["blue", "violet", "emerald", "rose", "amber"].map((color) => <option key={color} value={color}>{color[0].toUpperCase() + color.slice(1)}</option>)}</select></label>
                <label className="grid gap-1.5 text-sm font-medium text-slate-700">Layout density<select value={appearance.density} onChange={(event) => setAppearance({ ...appearance, density: event.target.value as AppearancePreferences["density"] })} className="rounded-lg border border-slate-300 bg-white px-3 py-2.5 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"><option value="comfortable">Comfortable</option><option value="compact">Compact</option></select></label>
                <label className="grid gap-1.5 text-sm font-medium text-slate-700">Font size<select value={appearance.font_size} onChange={(event) => setAppearance({ ...appearance, font_size: event.target.value as AppearancePreferences["font_size"] })} className="rounded-lg border border-slate-300 bg-white px-3 py-2.5 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"><option value="small">Small</option><option value="medium">Medium</option><option value="large">Large</option></select></label>
              </div>
            </Card>
          </>}
          {!loading && activeTab === "Planning" && <Card>
            <h3 className="text-base font-semibold text-slate-900">Planning preferences</h3>
            <p className="mt-1 text-sm text-slate-600">These settings guide your daily schedule and planning previews.</p>
            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <label className="grid gap-1.5 text-sm font-medium text-slate-700">Time zone<select value={planning.timezone_name} onChange={(event) => setPlanning({ ...planning, timezone_name: event.target.value })} className="rounded-lg border border-slate-300 bg-white px-3 py-2.5 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100">{[...new Set([...TIME_ZONES, planning.timezone_name])].map((zone) => <option key={zone} value={zone}>{zone}</option>)}</select></label>
              <label className="grid gap-1.5 text-sm font-medium text-slate-700">Preferred session (minutes)<input type="number" min={15} max={180} value={planning.preferred_session_minutes} onChange={(event) => setPlanning({ ...planning, preferred_session_minutes: Number(event.target.value) })} className="rounded-lg border border-slate-300 px-3 py-2.5 font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" /></label>
              <label className="grid gap-1.5 text-sm font-medium text-slate-700">Workday starts<input type="time" value={planning.workday_start} onChange={(event) => setPlanning({ ...planning, workday_start: event.target.value })} className="rounded-lg border border-slate-300 px-3 py-2.5 font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" /></label>
              <label className="grid gap-1.5 text-sm font-medium text-slate-700">Workday ends<input type="time" value={planning.workday_end} onChange={(event) => setPlanning({ ...planning, workday_end: event.target.value })} className="rounded-lg border border-slate-300 px-3 py-2.5 font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" /></label>
              <label className="grid gap-1.5 text-sm font-medium text-slate-700">Break between sessions (minutes)<input type="number" min={0} max={60} value={planning.break_minutes} onChange={(event) => setPlanning({ ...planning, break_minutes: Number(event.target.value) })} className="rounded-lg border border-slate-300 px-3 py-2.5 font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" /></label>
              <label className="grid gap-1.5 text-sm font-medium text-slate-700">Daily capacity (minutes)<input type="number" min={30} max={720} value={planning.daily_capacity_minutes} onChange={(event) => setPlanning({ ...planning, daily_capacity_minutes: Number(event.target.value) })} className="rounded-lg border border-slate-300 px-3 py-2.5 font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" /></label>
            </div>
          </Card>}
          {!loading && activeTab === "Integrations" && <Card>
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div><h3 className="text-base font-semibold text-slate-900">Google Calendar</h3><p className="mt-1 text-sm text-slate-600">Connect your calendar to see busy times while you plan your day.</p></div>
              {integrationLoading ? <span role="status" className="text-sm text-slate-500">Checking connection…</span> : googleStatus?.status === "connected" ? <span className="inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1 text-sm font-semibold text-emerald-800"><span aria-hidden="true" className="size-2 rounded-full bg-emerald-600" />Connected</span> : <span className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-sm font-semibold text-slate-700"><span aria-hidden="true" className="size-2 rounded-full bg-slate-400" />Not connected</span>}
            </div>
            {integrationLoading ? <p className="mt-5 text-sm text-slate-500">Loading Google status…</p> : googleStatus?.status === "connected" ? <div className="mt-5 space-y-4">
              <div><p className="text-sm font-semibold text-slate-700">Granted scopes</p>{googleStatus.scopes.length ? <ul className="mt-2 flex flex-wrap gap-2">{googleStatus.scopes.map((scope) => <li key={scope} className="rounded-lg bg-slate-100 px-2.5 py-1 text-xs text-slate-700">{scope}</li>)}</ul> : <p className="mt-1 text-sm text-slate-500">No scope details were returned by Google.</p>}</div>
              <p className="text-sm text-slate-600">Last successful sync: {googleStatus.last_sync_at ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(googleStatus.last_sync_at)) : "Not synced yet"}</p>
              <button type="button" disabled={busy} onClick={() => void disconnectGoogle()} className="inline-flex items-center gap-2 rounded-lg border border-rose-200 px-4 py-2.5 text-sm font-semibold text-rose-700 hover:bg-rose-50 disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-500"><Unplug aria-hidden="true" className="size-4" />Disconnect</button>
            </div> : <div className="mt-5"><button type="button" disabled={busy} onClick={() => void connectGoogle()} className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"><Link2 aria-hidden="true" className="size-4" />Connect Google Calendar</button></div>}
            {!integrationLoading && <button type="button" onClick={() => void refreshGoogleStatus()} className="mt-4 text-sm font-semibold text-blue-700 underline">Refresh status</button>}
          </Card>}
          {!loading && activeTab === "Notifications" && <Card>
            <h3 className="text-base font-semibold text-slate-900">Notifications</h3>
            <p className="mt-1 text-sm text-slate-600">Choose which reminders AURA should prepare for you.</p>
            <div className="mt-5 divide-y divide-slate-100">
              {([
                ["due_soon_reminders", "Due soon reminders", "Get a reminder as a task deadline approaches."],
                ["overdue_alerts", "Overdue alerts", "Get an alert when a task passes its deadline."],
                ["weekly_summary", "Weekly summary", "Receive a weekly summary of your goal and task progress."],
              ] as const).map(([key, title, description]) => <label key={key} className="flex cursor-pointer items-center justify-between gap-4 py-4 first:pt-0 last:pb-0"><span><span className="block text-sm font-semibold text-slate-800">{title}</span><span className="mt-1 block text-sm text-slate-500">{description}</span></span><input type="checkbox" role="switch" aria-label={title} checked={notifications[key]} onChange={(event) => setNotifications({ ...notifications, [key]: event.target.checked })} className="size-5 shrink-0 accent-blue-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2" /></label>)}
            </div>
            <label className="mt-5 grid max-w-sm gap-1.5 text-sm font-medium text-slate-700">Reminder lead time<select value={notifications.reminder_lead_time_minutes} onChange={(event) => setNotifications({ ...notifications, reminder_lead_time_minutes: Number(event.target.value) as NotificationPreferences["reminder_lead_time_minutes"] })} className="rounded-lg border border-slate-300 bg-white px-3 py-2.5 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"><option value={15}>15 minutes before</option><option value={30}>30 minutes before</option><option value={60}>1 hour before</option><option value={1440}>1 day before</option></select></label>
          </Card>}
          {!loading && activeTab === "AI" && <Card>
            <h3 className="text-base font-semibold text-slate-900">AI planning</h3>
            <p className="mt-1 text-sm text-slate-600">Choose whether AURA may use a configured AI provider when generating a plan.</p>
            <div className="mt-5 flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-200 p-4">
              <span><span className="block text-sm font-semibold text-slate-800">Use AI planning</span><span className="mt-1 block text-sm text-slate-500">When disabled or unavailable, AURA uses its rule-based planner.</span></span>
              {aiLoading ? <span role="status" className="text-sm text-slate-500">Checking provider…</span> : <label className="inline-flex items-center gap-3 text-sm font-medium text-slate-700"><span>{useAIPlanning ? "On" : "Off"}</span><input type="checkbox" role="switch" aria-label="Use AI planning" checked={useAIPlanning} onChange={(event) => setUseAIPlanning(event.target.checked)} className="size-5 accent-blue-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2" /></label>}
            </div>
            <div className="mt-4 rounded-xl bg-slate-50 p-4" role="status"><p className="text-sm font-semibold text-slate-800">AI provider: {aiLoading ? "Checking…" : aiStatus?.configured ? "Configured" : "Not configured"}</p><p className="mt-1 text-sm text-slate-600">{aiStatus?.configured ? "AURA can request AI generated plans when the setting is on." : "Rule-based planning remains available as a fallback."}</p></div>
          </Card>}
          {!loading && activeTab === "Data and account" && <>
            <Card>
              <h3 className="text-base font-semibold text-slate-900">Export your data</h3>
              <p className="mt-1 text-sm text-slate-600">Download all of your goals and tasks, including descriptions, notes, dates, and status.</p>
              <div className="mt-5 flex flex-wrap gap-3"><button type="button" disabled={busy} onClick={() => void exportData("json")} className="rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600">Download JSON</button><button type="button" disabled={busy} onClick={() => void exportData("csv")} className="rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600">Download CSV</button></div>
            </Card>
            <Card className="border-rose-200">
              <h3 className="text-base font-semibold text-rose-800">Delete account</h3>
              <p className="mt-1 text-sm text-slate-600">This permanently deletes your profile, goals, tasks, schedules, preferences, and connected integration credentials.</p>
              <div className="mt-5 grid gap-4 sm:grid-cols-[1fr_auto] sm:items-end"><TextField label={'Type DELETE to confirm'} value={deleteConfirmation} onChange={(event) => setDeleteConfirmation(event.target.value)} autoComplete="off" spellCheck={false} /><button type="button" disabled={busy || deleteConfirmation !== "DELETE"} onClick={() => void deleteAccount()} className="inline-flex items-center justify-center gap-2 rounded-lg bg-rose-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-rose-800 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600 focus-visible:ring-offset-2"><Trash2 aria-hidden="true" className="size-4" />Delete account</button></div>
            </Card>
          </>}
          {!loading && activeTab !== "Profile" && <Card><h3 className="text-base font-semibold text-slate-900">{activeTab}</h3><p className="mt-1 text-sm text-slate-600">This section is being prepared.</p></Card>}
        </div>
        {dirty && <div className="fixed inset-x-0 bottom-0 z-30 border-t border-slate-200 bg-white/95 px-4 py-3 shadow-lg backdrop-blur sm:px-6"><div className="mx-auto flex max-w-4xl items-center justify-between gap-3"><p className="text-sm font-medium text-slate-700">You have unsaved changes.</p><button type="button" disabled={busy} onClick={() => { lastAction.current = saveAllChanges; void saveAllChanges(); }} className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"><Save aria-hidden="true" className="size-4" />Save changes</button></div></div>}
      </main>
    </div>
  </div>;
}
