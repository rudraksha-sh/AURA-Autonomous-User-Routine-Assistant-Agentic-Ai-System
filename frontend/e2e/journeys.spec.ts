import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { randomUUID } from "node:crypto";

const password = "Browser-Test#12345";
const target = "2030-01-02";

async function register(page: Page) {
  const email = `e2e-${randomUUID()}@example.com`;
  await page.goto("/register");
  await page.getByLabel("Name", { exact: true }).fill("Browser test");
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByLabel(/confirm password/i).fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/verify-email/);
  const otp = await page.request.get("/api/e2e/verification-code", { params: { email } });
  expect(otp.ok()).toBe(true);
  const { code } = await otp.json() as { code: string };
  await page.getByLabel("Code digit 1").fill(code[0]);
  await expect(page.getByLabel("Code digit 2")).toBeFocused();
  await page.getByLabel("Code digit 2").pressSequentially(code.slice(1));
  await page.getByRole("button", { name: "Verify email" }).click();
  await expect(page.getByRole("status")).toContainText("Your email is verified");
  return email;
}

async function signIn(page: Page, email: string) {
  await expect(page).toHaveURL(/\/login(?:\?|$)/);
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("button", { name: "Log out" })).toBeVisible();
}

async function newSession(page: Page) {
  const email = await register(page);
  await page.getByRole("link", { name: "Go to sign in" }).click();
  await signIn(page, email);
  return email;
}

function observe(page: Page) {
  const errors: string[] = [];
  const failures: string[] = [];
  const http: string[] = [];
  page.on("pageerror", (error) => errors.push(error.name));
  page.on("console", (message) => {
    if (/hydration|did not match/i.test(message.text())) errors.push("hydration");
    if (message.type() === "error" && !message.text().startsWith("Failed to load resource:")) {
      errors.push("browser console error");
    }
  });
  page.on("requestfailed", (request) => {
    if (request.failure()?.errorText !== "net::ERR_ABORTED") failures.push(new URL(request.url()).pathname);
  });
  page.on("response", (response) => {
    const path = new URL(response.url()).pathname;
    if (response.status() === 404 && path === "/api/profile/photo") return;
    if (response.status() >= 400) http.push(`${response.status()} ${path}`);
  });
  return { errors, failures, http };
}

test("register, verify, sign in to a protected destination, and log out", async ({ page }) => {
  const browser = observe(page);
  await page.goto("/goals");
  await expect(page).toHaveURL(/\/login\?next=%2Fgoals/);
  const email = await register(page);
  await page.goto("/login?next=%2Fgoals");
  await signIn(page, email);
  await expect(page).toHaveURL(/\/goals$/);
  await expect(page.getByRole("heading", { name: "Your goals" })).toBeVisible();
  await expect(page.getByText("0 goals", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Log out" }).click();
  await expect(page).toHaveURL(/\/login/);
  await page.goto("/planner/workflows");
  await expect(page).toHaveURL(/\/login\?next=%2Fplanner%2Fworkflows/);
  expect(browser).toEqual({ errors: [], failures: [], http: [] });
});

test("plan, visualize, approve, schedule, replan, reject, and run bounded autonomy with tenant isolation", async ({ page, browser }) => {
  test.setTimeout(60_000);
  const observed = observe(page);
  await newSession(page);
  await page.goto("/goals");
  await page.getByLabel("Title", { exact: true }).fill("Learn garden design");
  const goalResponse = page.waitForResponse((r) => r.url().endsWith("/api/goals") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Create goal" }).click();
  const created = await goalResponse;
  expect(created.ok()).toBe(true);
  const { id: goalId } = await created.json() as { id: number };

  await page.goto("/planner/workflows");
  await page.getByLabel("Schedule preview date").fill(target);
  const preview = page.waitForResponse((r) => r.url().endsWith("/api/v1/workflows") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Preview plan", exact: true }).click();
  const runResponse = await preview;
  expect(runResponse.status()).toBe(201);
  const { id: runId } = await runResponse.json() as { id: string };
  await expect(page.getByRole("status").filter({ hasText: "Awaiting approval" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Schedule estimate" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Activity timeline" })).toBeVisible();
  for (const [width, height] of [[1440, 900], [820, 1180], [390, 844]]) {
    await page.setViewportSize({ width, height });
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
  }
  await page.getByRole("button", { name: "Pause", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "Paused" })).toBeVisible();
  await page.getByRole("button", { name: "Resume review" }).click();
  await page.getByRole("button", { name: "Approve and create tasks" }).click();
  await expect(page.getByText(/Receipt for \d+ tasks/)).toBeVisible();

  await page.getByRole("link", { name: "Open daily planner" }).click();
  await page.getByLabel("Schedule date").fill(target);
  await page.getByRole("button", { name: "Build schedule" }).click();
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Review and approve schedule" }).click();
  await expect(page.getByRole("heading", { name: "Saved timeline" })).toBeVisible();

  await page.goto("/planner/workflows");
  await page.getByRole("button", { name: "Preview a revised plan" }).click();
  await expect(page.getByRole("heading", { name: "Changes since the earlier plan" })).toBeVisible();
  await page.getByRole("button", { name: "Reject", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "Rejected" })).toBeVisible();

  await page.getByLabel("Set up an autonomous grant").check();
  await page.getByLabel("Allow AURA to create local tasks").check();
  await page.getByLabel("I authorize task creation within these limits.").check();
  await page.getByRole("button", { name: "Enable grant" }).click();
  await page.getByLabel("Use for the next run").check();
  await page.getByLabel("Schedule preview date").fill(target);
  const autonomous = page.waitForResponse((r) => r.url().endsWith("/api/v1/workflows") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Create tasks with selected grant" }).click();
  expect((await (await autonomous).json()).status).toBe("completed");
  await expect(page.getByText(/Receipt for \d+ tasks/)).toBeVisible();

  const other = await browser.newPage({ baseURL: "http://127.0.0.1:3100" });
  try {
    await newSession(other);
    await other.goto("/planner/workflows");
    await expect(other.getByText("Your workflow history will appear here.")).toBeVisible();
    const token = await other.evaluate(() => localStorage.getItem("aura_access_token"));
    const headers = { Authorization: `Bearer ${token}` };
    expect((await other.request.get(`/api/v1/workflows/${runId}`, { headers })).status()).toBe(404);
    expect((await other.request.get(`/api/goals/${goalId}`, { headers })).status()).toBe(404);
  } finally {
    await other.close();
  }

  expect(observed.errors).toEqual([]);
  expect(observed.failures).toEqual([]);
  expect(observed.http).toEqual([]);
});

test("Google mocked consent, revoke warning and disconnect with keyboard and accessible layouts", async ({ page }) => {
  test.setTimeout(60_000);
  const observed = observe(page);
  const external: string[] = [];
  await page.route("**/*", async (route) => {
    if (new URL(route.request().url()).hostname === "127.0.0.1") await route.continue();
    else { external.push(new URL(route.request().url()).hostname); await route.abort(); }
  });
  await newSession(page);
  await page.goto("/settings");
  const tab = page.getByRole("tab", { name: "Integrations" });
  await page.getByRole("tab", { name: "Planning" }).click();
  await page.keyboard.press("ArrowRight");
  await expect(tab).toBeFocused();
  await expect(tab).toHaveAttribute("aria-selected", "true");
  const select = page.getByLabel("Read access");
  await expect(select).toBeVisible();
  await select.selectOption("gmail");
  await page.getByRole("button", { name: "Connect Google" }).click();
  await expect(page.getByRole("heading", { name: "Mock Google consent" })).toBeVisible();
  await page.getByRole("link", { name: "Allow read access" }).click();
  await expect(tab).toHaveAttribute("aria-selected", "true");
  const panel = page.getByRole("tabpanel", { name: "Integrations" });
  await expect(panel.getByText("https://www.googleapis.com/auth/gmail.readonly", { exact: true })).toBeVisible();
  const revoke = page.getByRole("button", { name: "Revoke Google access" });
  await expect(revoke).toHaveAccessibleDescription(/Gmail, Calendar and Drive.*AURA Google project/);
  for (const [width, height, colorScheme] of [[1440, 900, "light"], [820, 1180, "light"], [390, 844, "dark"]] as const) {
    await page.setViewportSize({ width, height });
    await page.emulateMedia({ colorScheme });
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
    const result = await new AxeBuilder({ page }).include("#settings-panel").withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
    expect(result.violations.map(({ id, nodes }) => ({ id, targets: nodes.map(({ target }) => target) }))).toEqual([]);
  }
  await revoke.focus();
  page.once("dialog", async (dialog) => {
    expect(dialog.message()).toMatch(/Gmail, Calendar and Drive/);
    await dialog.dismiss();
  });
  await page.keyboard.press("Enter");
  await expect(revoke).toBeFocused();
  page.once("dialog", (dialog) => dialog.accept());
  const disconnect = page.waitForResponse((response) => response.request().method() === "DELETE");
  await page.keyboard.press("Enter");
  const deleted = await disconnect;
  expect(new URL(deleted.url()).searchParams.get("revoke_provider")).toBe("true");
  expect(deleted.status()).toBe(204);
  await expect(panel.getByText("Not connected", { exact: true })).toBeVisible();
  await expect(panel.getByRole("heading", { name: "Google integrations" })).toBeFocused();
  await page.getByRole("button", { name: "Connect Google" }).click();
  await page.getByRole("link", { name: "Allow read access" }).click();
  const localDisconnect = page.waitForResponse((response) => response.request().method() === "DELETE");
  await page.getByRole("button", { name: "Disconnect locally" }).click();
  const removed = await localDisconnect;
  expect(new URL(removed.url()).searchParams.has("revoke_provider")).toBe(false);
  expect(removed.status()).toBe(204);
  await expect(panel.getByText("Not connected", { exact: true })).toBeVisible();
  expect(external).toEqual([]);
  expect(observed).toEqual({ errors: [], failures: [], http: [] });
});

test("session loading, timeout, retry and expiration", async ({ page }) => {
  const observed = observe(page);
  await newSession(page);
  let release: () => void = () => {};
  const pending = new Promise<void>((resolve) => { release = resolve; });
  await page.route("**/api/auth/me", async (route) => {
    await pending;
    await route.abort().catch(() => {});
  }, { times: 1 });
  await page.goto("/planner/workflows");
  await expect(page.getByRole("status").filter({ hasText: "Verifying your session" })).toBeVisible();
  await expect(page.getByRole("alert").filter({ hasText: "Could not verify your session" })).toContainText("Session verification timed out", { timeout: 15_000 });
  release();
  await page.getByRole("button", { name: "Retry" }).click();
  await expect(page.getByRole("heading", { name: "Agent workflows" }).last()).toBeVisible();
  await page.route("**/api/goals", (route) => route.fulfill({
    status: 503, json: { message: "Goals are temporarily unavailable." },
  }), { times: 1 });
  await page.goto("/goals");
  await expect(page.getByRole("alert").filter({ hasText: "Goals are temporarily unavailable." })).toBeVisible();
  await page.getByRole("button", { name: "Retry loading goals" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Goals are temporarily unavailable." })).toHaveCount(0);
  await expect(page.getByText("0 goals", { exact: true })).toBeVisible();
  await page.goto("/planner/workflows");
  await expect(page.getByRole("heading", { name: "Agent workflows" }).last()).toBeVisible();
  await page.evaluate(() => localStorage.setItem("aura_access_token", "expired-fixture"));
  await page.reload();
  await expect(page).toHaveURL(/\/login\?next=%2Fplanner%2Fworkflows/);
  expect(await page.evaluate(() => localStorage.getItem("aura_access_token"))).toBeNull();
  expect(observed.errors).toEqual([]);
  expect(observed.http.filter((response) => response !== "401 /api/profile/theme"))
    .toEqual(["503 /api/goals", "401 /api/auth/me"]);
  expect(observed.failures.filter((path) => path !== "/api/auth/me")).toEqual([]);
});
