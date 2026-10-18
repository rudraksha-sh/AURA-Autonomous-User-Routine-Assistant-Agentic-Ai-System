"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Check, CircleAlert, Loader2, MessageCircle, Mic, MicOff, Send, Trash2, Volume2, VolumeX, X } from "lucide-react";
import { runAssistantTool } from "@/services/assistant";
import type { Goal } from "@/types/goal";
import type { Task } from "@/types/task";

type VoicePhase = "idle" | "listening" | "processing" | "speaking" | "error";
type Message = { id: number; role: "user" | "assistant"; text: string };
type PendingAction =
  | { kind: "create-goal"; title: string; idempotencyKey: string }
  | { kind: "complete-task"; task: Task; idempotencyKey: string }
  | { kind: "create-task"; title: string; goal: Goal; idempotencyKey: string };

type RecognitionResult = { isFinal: boolean; 0: { transcript: string; confidence?: number } };
type RecognitionEvent = Event & { results: ArrayLike<RecognitionResult>; resultIndex: number };
type RecognitionErrorEvent = Event & { error: string };
interface BrowserRecognition extends EventTarget {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: RecognitionEvent) => void) | null;
  onerror: ((event: RecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}
type RecognitionConstructor = new () => BrowserRecognition;
type SpeechWindow = Window & {
  SpeechRecognition?: RecognitionConstructor;
  webkitSpeechRecognition?: RecognitionConstructor;
};

const LANGUAGES = [
  { value: "en-US", label: "English (US)" },
  { value: "en-IN", label: "English (India)" },
  { value: "hi-IN", label: "Hindi (India)" },
];
const WELCOME_MESSAGE = "Hi. I can read your tasks and goals, open AURA pages, and prepare a few changes for your review. Commands run through your signed-in AURA account. Voice recognition depends on your browser; you can always type instead.";

function normalize(value: string) {
  return value.trim().toLocaleLowerCase().replace(/\s+/g, " ").replace(/[.!?]+$/, "");
}

function priorityRank(priority: string) {
  return ({ high: 0, medium: 1, low: 2 } as Record<string, number>)[priority.toLowerCase()] ?? 3;
}

async function listTasks() {
  return (await runAssistantTool({ tool: "list_tasks" })).tasks ?? [];
}

async function listGoals() {
  return (await runAssistantTool({ tool: "list_goals" })).goals ?? [];
}

export function VoiceAssistant() {
  const router = useRouter();
  const [open, setOpen] = React.useState(false);
  const [phase, setPhase] = React.useState<VoicePhase>("idle");
  const [notice, setNotice] = React.useState("");
  const [draft, setDraft] = React.useState("");
  const [interim, setInterim] = React.useState("");
  const [language, setLanguage] = React.useState(() => {
    if (typeof window === "undefined") return "en-US";
    try {
      const savedLanguage = window.localStorage.getItem("aura_voice_language");
      return savedLanguage && LANGUAGES.some((item) => item.value === savedLanguage) ? savedLanguage : "en-US";
    } catch {
      return "en-US";
    }
  });
  const [speakResponses, setSpeakResponses] = React.useState(false);
  const [speechRate, setSpeechRate] = React.useState(1);
  const [messages, setMessages] = React.useState<Message[]>([
    { id: 1, role: "assistant", text: WELCOME_MESSAGE },
  ]);
  const [pendingAction, setPendingAction] = React.useState<PendingAction | null>(null);
  const [busy, setBusy] = React.useState(false);
  const recognitionRef = React.useRef<BrowserRecognition | null>(null);
  const messageIdRef = React.useRef(2);
  const inputRef = React.useRef<HTMLTextAreaElement>(null);

  React.useEffect(() => () => {
    recognitionRef.current?.abort();
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
  }, []);

  function addMessage(role: Message["role"], text: string) {
    setMessages((current) => [...current, { id: messageIdRef.current++, role, text }].slice(-100));
  }

  function speak(text: string) {
    if (!speakResponses || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = language;
    utterance.rate = speechRate;
    utterance.onstart = () => setPhase("speaking");
    utterance.onend = () => setPhase("idle");
    utterance.onerror = () => setPhase("idle");
    window.speechSynthesis.speak(utterance);
  }

  function respond(text: string) {
    addMessage("assistant", text);
    setNotice(text);
    speak(text);
  }

  function startListening() {
    if (recognitionRef.current) return;
    const speechWindow = window as SpeechWindow;
    const Recognition = speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition;
    if (!Recognition) {
      setPhase("error");
      setNotice("Speech recognition is not supported by this browser. You can still type a command below.");
      return;
    }

    setDraft("");
    setInterim("");
    setNotice("Listening. Your browser may process speech according to its own speech service and privacy settings; AURA does not store raw audio.");
    const recognition = new Recognition();
    recognition.lang = language;
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.onresult = (event) => {
      let finalText = "";
      let interimText = "";
      let lowConfidence = false;
      for (let index = 0; index < event.results.length; index += 1) {
        const result = event.results[index];
        if (!result?.[0]?.transcript) continue;
        if (result.isFinal) {
          finalText += `${result[0].transcript} `;
          if (typeof result[0].confidence === "number" && result[0].confidence < 0.5) lowConfidence = true;
        }
        else interimText += `${result[0].transcript} `;
      }
      setDraft(finalText.trim());
      setInterim(interimText.trim());
      if (lowConfidence) setNotice("This transcript may be uncertain. Review and edit it before sending.");
    };
    recognition.onerror = (event) => {
      recognitionRef.current = null;
      setPhase("error");
      setNotice(event.error === "not-allowed" || event.error === "service-not-allowed"
        ? "Microphone access was denied. Allow access in your browser settings or type a command."
        : event.error === "no-speech"
          ? "No speech was detected. Try again or type your request."
          : "Speech recognition failed. You can retry or type your request.");
    };
    recognition.onend = () => {
      recognitionRef.current = null;
      setInterim("");
      setPhase((current) => current === "listening" ? "idle" : current);
    };
    recognitionRef.current = recognition;
    try {
      recognition.start();
      setPhase("listening");
    } catch {
      recognitionRef.current = null;
      setPhase("error");
      setNotice("The microphone could not start. Check browser permissions, then retry or type a command.");
    }
  }

  function stopAudio() {
    recognitionRef.current?.stop();
    recognitionRef.current = null;
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    setInterim("");
    setPhase("idle");
    setNotice("Voice input and playback stopped.");
  }

  async function interpret(text: string) {
    const command = normalize(text);
    if (!command) {
      respond("I did not get a command. Try again or type one.");
      return;
    }
    setBusy(true);
    setPhase("processing");
    setNotice("Checking your request against available AURA actions…");
    addMessage("user", text.trim());
    setPendingAction(null);
    try {
      if (/^(hi|hello|hey|नमस्ते)$/.test(command)) {
        respond("Hello. You can ask for your priority tasks, open a page, create a goal, create a task for a goal, or complete a task by its exact title.");
      } else if (/^(help|what can you do|commands)$/.test(command)) {
        respond("Available: ‘show my important tasks’, ‘show my goals’, ‘open the planner’, ‘create goal titled …’, ‘create task … for goal …’, and ‘mark task … complete’. Changes require review and confirmation. Workflows and focus sessions are not available yet.");
      } else if (/^(open|go to|show me) (the )?(dashboard|home)$/.test(command)) {
        router.push("/dashboard");
        respond("Opening your dashboard.");
      } else if (/^(open|go to|show me) (the )?(planner|daily planner|schedule)$/.test(command) || command.startsWith("plan my day")) {
        router.push("/planner/daily");
        respond("Opening the daily planner. It will build a proposal for you to review.");
      } else if (/^(open|go to|show me) (the )?tasks?$/.test(command)) {
        router.push("/tasks");
        respond("Opening your tasks.");
      } else if (/^(open|go to|show me) (the )?goals?$/.test(command)) {
        router.push("/goals");
        respond("Opening your goals.");
      } else if (/^(what are|show|list).*(important|priority|priorit(y|ies)|top tasks)/.test(command)) {
        const tasks = await listTasks();
        const pending = tasks.filter((task) => task.status.toLowerCase() !== "completed")
          .sort((left, right) => priorityRank(left.priority) - priorityRank(right.priority)
            || (left.deadline ? Date.parse(left.deadline) : Number.POSITIVE_INFINITY) - (right.deadline ? Date.parse(right.deadline) : Number.POSITIVE_INFINITY));
        if (!pending.length) respond("You have no open tasks right now.");
        else respond(`Your top ${Math.min(3, pending.length)} open tasks are: ${pending.slice(0, 3).map((task, index) => `${index + 1}, ${task.title}, ${task.priority} priority${task.deadline ? `, due ${new Date(task.deadline).toLocaleDateString()}` : ""}`).join("; ")}.`);
      } else if (/^(what are|show|list).*(my )?goals?$/.test(command)) {
        const goals = await listGoals();
        respond(goals.length ? `You have ${goals.length} goals: ${goals.slice(0, 8).map((goal) => goal.title).join("; ")}.` : "You do not have any goals yet.");
      } else if (/^(create|add) goal (?:titled|called) (.+)$/.test(command)) {
        const title = text.trim().match(/^(?:create|add) goal (?:titled|called) (.+)$/i)?.[1]?.trim();
        if (!title) respond("Please include a goal title, for example: create goal titled Learn guitar.");
        else {
          setPendingAction({ kind: "create-goal", title, idempotencyKey: crypto.randomUUID() });
          respond(`I can create the goal ‘${title}’. Review it below and confirm to save.`);
        }
      } else if (/^(create|add) task .+ for goal .+$/.test(command)) {
        const match = text.trim().match(/^(?:create|add) task (.+) for goal (.+)$/i);
        const title = match?.[1]?.trim();
        const goalQuery = match?.[2]?.trim();
        if (!title || !goalQuery) respond("Say: create task <task title> for goal <goal title>.");
        else {
          const goals = await listGoals();
          const matches = goals.filter((goal) => normalize(goal.title) === normalize(goalQuery));
          if (matches.length !== 1) respond(matches.length ? "More than one goal matches that title. Use a more specific goal title." : "I could not find a goal with that exact title.");
          else {
            setPendingAction({ kind: "create-task", title, goal: matches[0], idempotencyKey: crypto.randomUUID() });
            respond(`I can add ‘${title}’ to ‘${matches[0].title}’. Review and confirm below to save.`);
          }
        }
      } else if (/^(mark|set) task .+ complete$/.test(command)) {
        const title = text.trim().match(/^(?:mark|set) task (.+) complete$/i)?.[1]?.trim();
        const tasks = await listTasks();
        const matches = tasks.filter((task) => normalize(task.title) === normalize(title ?? "") && task.status.toLowerCase() !== "completed");
        if (matches.length !== 1) respond(matches.length ? "More than one open task matches. Use a unique exact title." : "I could not find an open task with that exact title.");
        else {
          setPendingAction({ kind: "complete-task", task: matches[0], idempotencyKey: crypto.randomUUID() });
          respond(`I can mark ‘${matches[0].title}’ complete. Review and confirm below to save.`);
        }
      } else if (/^(pause|resume|cancel|status).*(workflow|agent)/.test(command)) {
        respond("Workflow controls are not implemented in this AURA build, so I have not changed any workflow.");
      } else if (command.includes("focus session") || command.includes("pomodoro")) {
        respond("Focus sessions are not implemented yet. No timer or session was started.");
      } else {
        respond("I could not match that to an available AURA command. I do not use an external language model here. Say ‘help’ to see supported commands, or open a page and use its controls.");
      }
    } catch (error) {
      respond(error instanceof Error ? error.message : "AURA could not complete that request. Nothing was reported as successful.");
    } finally {
      setBusy(false);
      setPhase((current) => current === "processing" ? "idle" : current);
    }
  }

  async function confirmAction() {
    if (!pendingAction || busy) return;
    const action = pendingAction;
    setBusy(true);
    setPhase("processing");
    try {
      if (action.kind === "create-goal") {
        const response = await runAssistantTool({ tool: "create_goal", idempotency_key: action.idempotencyKey, title: action.title });
        const created = response.result as Goal | null | undefined;
        if (!created) throw new Error("AURA did not return the saved goal.");
        const verified = (await listGoals()).some((goal) => goal.id === created.id && normalize(goal.title) === normalize(action.title));
        if (!verified) throw new Error("AURA did not return the new goal when I verified it. Please check your goals before retrying.");
        setPendingAction(null);
        respond(`Goal ‘${created.title}’ was saved and verified.`);
      } else if (action.kind === "create-task") {
        const response = await runAssistantTool({ tool: "create_task", idempotency_key: action.idempotencyKey, goal_id: action.goal.id, title: action.title });
        const created = response.result as Task | null | undefined;
        if (!created) throw new Error("AURA did not return the saved task.");
        const verified = (await listTasks()).some((task) => task.id === created.id && task.goal_id === action.goal.id);
        if (!verified) throw new Error("AURA did not return the new task when I verified it. Please check your tasks before retrying.");
        setPendingAction(null);
        respond(`Task ‘${created.title}’ was saved under ‘${action.goal.title}’ and verified.`);
      } else {
        const response = await runAssistantTool({ tool: "complete_task", idempotency_key: action.idempotencyKey, task_id: action.task.id });
        const updated = response.result as Task | null | undefined;
        if (!updated) throw new Error("AURA did not return the updated task.");
        const verified = (await listTasks()).some((task) => task.id === action.task.id && task.status.toLowerCase() === "completed");
        if (!verified || updated.status.toLowerCase() !== "completed") throw new Error("AURA did not verify the task completion. Please check your task list.");
        setPendingAction(null);
        respond(`Task ‘${updated.title}’ is marked complete and verified.`);
      }
    } catch (error) {
      respond(error instanceof Error ? error.message : "AURA could not verify this change. Check the relevant page before retrying.");
    } finally {
      setBusy(false);
      setPhase((current) => current === "processing" ? "idle" : current);
    }
  }

  function submitDraft(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || busy) return;
    setDraft("");
    void interpret(text);
  }

  function changeLanguage(value: string) {
    setLanguage(value);
    try {
      window.localStorage.setItem("aura_voice_language", value);
    } catch {
      setNotice("This browser does not allow saving preferences. The language will apply for this visit.");
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
        aria-controls="aura-voice-panel"
        className="fixed bottom-4 right-4 z-40 inline-flex items-center gap-2 rounded-full bg-slate-900 px-4 py-3 text-sm font-semibold text-white shadow-lg transition hover:bg-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
      >
        <MessageCircle aria-hidden="true" className="size-5" />Assistant
      </button>

      {open && <section id="aura-voice-panel" aria-label="AURA voice and text assistant" className="fixed inset-x-3 bottom-20 z-50 flex max-h-[min(72vh,680px)] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl sm:inset-x-auto sm:right-4 sm:w-[min(28rem,calc(100vw-2rem))]">
        <header className="flex items-start justify-between gap-3 border-b border-slate-100 p-4">
          <div><h2 className="font-semibold text-slate-900">AURA Assistant</h2><p className="mt-1 text-xs text-slate-500">Rule-based commands · connected to your signed-in data</p></div>
          <div className="flex items-center gap-1">
            <button type="button" aria-label="Clear conversation transcript" onClick={() => { stopAudio(); setPendingAction(null); setMessages([{ id: messageIdRef.current++, role: "assistant", text: WELCOME_MESSAGE }]); }} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100"><Trash2 aria-hidden="true" className="size-4" /></button>
            <button type="button" aria-label="Close assistant" onClick={() => { stopAudio(); setOpen(false); }} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100"><X aria-hidden="true" className="size-4" /></button>
          </div>
        </header>

        <div className="flex flex-wrap items-center gap-3 border-b border-slate-100 px-4 py-3">
          <label className="flex items-center gap-2 text-xs font-medium text-slate-600">Language
            <select aria-label="Speech language" value={language} onChange={(event) => changeLanguage(event.target.value)} className="rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-xs">
              {LANGUAGES.map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}
            </select>
          </label>
          <label className="ml-auto inline-flex items-center gap-2 text-xs text-slate-600"><input type="checkbox" checked={speakResponses} onChange={(event) => {
            if (event.target.checked && (!("speechSynthesis" in window) || typeof SpeechSynthesisUtterance === "undefined")) {
              setNotice("Spoken replies are not supported in this browser. Text replies remain available.");
              setSpeakResponses(false);
              return;
            }
            setSpeakResponses(event.target.checked);
          }} />Speak replies</label>
          {speakResponses && <label className="flex items-center gap-2 text-xs text-slate-600">Rate <input aria-label="Speech rate" type="range" min="0.7" max="1.3" step="0.1" value={speechRate} onChange={(event) => setSpeechRate(Number(event.target.value))} /></label>}
        </div>

        <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4" aria-live="polite" aria-relevant="additions text">
          {messages.map((message) => <article key={message.id} className={`max-w-[92%] rounded-2xl px-3 py-2.5 text-sm leading-5 ${message.role === "user" ? "ml-auto bg-blue-600 text-white" : "bg-slate-100 text-slate-800"}`}><span className="sr-only">{message.role === "user" ? "You said: " : "AURA: "}</span>{message.text}</article>)}
          {interim && <p className="rounded-xl border border-blue-200 bg-blue-50 px-3 py-2 text-sm italic text-slate-600">{interim}</p>}
          {pendingAction && <section className="rounded-xl border border-amber-200 bg-amber-50 p-3" aria-label="Action awaiting confirmation">
            <p className="text-xs font-semibold uppercase tracking-wide text-amber-800">Review before saving</p>
            <p className="mt-2 text-sm text-slate-800">{pendingAction.kind === "create-goal" ? `Create goal: ${pendingAction.title}` : pendingAction.kind === "create-task" ? `Create task “${pendingAction.title}” for goal “${pendingAction.goal.title}”` : `Mark task complete: ${pendingAction.task.title}`}</p>
            <div className="mt-3 flex gap-2"><button type="button" disabled={busy} onClick={() => void confirmAction()} className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">{busy ? <Loader2 aria-hidden="true" className="size-3.5 animate-spin" /> : <Check aria-hidden="true" className="size-3.5" />}Confirm and save</button><button type="button" disabled={busy} onClick={() => { setPendingAction(null); respond("Cancelled. No change was made."); }} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700">Cancel</button></div>
          </section>}
        </div>

        <div className="border-t border-slate-100 p-4">
          <p className="mb-2 flex min-h-5 items-center gap-2 text-xs text-slate-500" role="status">
            {phase === "listening" ? <><span className="size-2 animate-pulse rounded-full bg-rose-500" />Listening · speak a command</> : phase === "processing" ? <><Loader2 aria-hidden="true" className="size-3.5 animate-spin" />Checking AURA data</> : phase === "speaking" ? <><Volume2 aria-hidden="true" className="size-3.5" />Speaking · interrupt any time</> : phase === "error" ? <><CircleAlert aria-hidden="true" className="size-3.5 text-rose-600" />Voice unavailable · text mode remains active</> : notice || "Ready. Voice starts only when you press the microphone."}
          </p>
          <form onSubmit={submitDraft} className="flex items-end gap-2">
            <button type="button" aria-label={phase === "listening" ? "Stop microphone" : "Start microphone"} disabled={busy || phase === "speaking"} onClick={phase === "listening" ? stopAudio : startListening} className={`inline-flex size-10 shrink-0 items-center justify-center rounded-xl border ${phase === "listening" ? "border-rose-300 bg-rose-50 text-rose-700" : "border-slate-300 text-slate-700 hover:bg-slate-50"} disabled:opacity-50`}>{phase === "listening" ? <MicOff aria-hidden="true" className="size-4" /> : <Mic aria-hidden="true" className="size-4" />}</button>
            {phase === "speaking" && <button type="button" aria-label="Interrupt spoken response" onClick={stopAudio} className="inline-flex size-10 shrink-0 items-center justify-center rounded-xl border border-amber-300 bg-amber-50 text-amber-800"><VolumeX aria-hidden="true" className="size-4" /></button>}
            <textarea ref={inputRef} aria-label="Type or edit your command" rows={2} maxLength={1000} value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Type a command or edit your transcript…" className="min-h-10 min-w-0 flex-1 resize-y rounded-xl border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100" />
            <button type="submit" aria-label="Send command" disabled={!draft.trim() || busy} className="inline-flex size-10 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40"><Send aria-hidden="true" className="size-4" /></button>
          </form>
          <p className="mt-2 text-[11px] leading-4 text-slate-500">AURA uses fixed command patterns, not an LLM. Browser speech services may process audio under your browser’s settings. No audio or transcript is saved by this panel.</p>
        </div>
      </section>}
    </>
  );
}
