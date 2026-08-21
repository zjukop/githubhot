#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";

const endpoint = process.env.CHROME_DEBUG_ENDPOINT || "http://[::1]:9222";
const draftDir = path.resolve(process.argv[2] || ".local/social-drafts", process.argv[3] || new Date().toISOString().slice(0, 10));
const manifestPath = path.join(draftDir, "manifest.json");

function loadJson(name) {
  return JSON.parse(fs.readFileSync(path.join(draftDir, name), "utf8"));
}

function updateManifest(platform, status, details = {}) {
  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  Object.assign(manifest.platforms[platform], { status, ...details, attempted_at: new Date().toISOString() });
  fs.writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
}

class CdpPage {
  constructor(socket, ownsTarget = false) {
    this.socket = socket;
    this.ownsTarget = ownsTarget;
    this.nextId = 1;
    this.pending = new Map();
    socket.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);
      if (message.method === "Page.javascriptDialogOpening") {
        void this.send("Page.handleJavaScriptDialog", { accept: true }).catch(() => {});
        return;
      }
      if (!message.id || !this.pending.has(message.id)) return;
      const { resolve, reject } = this.pending.get(message.id);
      this.pending.delete(message.id);
      message.error ? reject(new Error(message.error.message)) : resolve(message.result);
    });
  }

  static async open(url) {
    const response = await fetch(`${endpoint}/json/new?${encodeURIComponent(url)}`, { method: "PUT" });
    if (!response.ok) throw new Error(`Chrome target creation failed: HTTP ${response.status}`);
    const target = await response.json();
    const socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      socket.addEventListener("open", resolve, { once: true });
      socket.addEventListener("error", reject, { once: true });
    });
    const page = new CdpPage(socket, true);
    await page.send("Page.enable");
    await page.send("Runtime.enable");
    return page;
  }

  static async connect(target) {
    const socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      socket.addEventListener("open", resolve, { once: true });
      socket.addEventListener("error", reject, { once: true });
    });
    const page = new CdpPage(socket);
    await page.send("Page.enable");
    await page.send("Runtime.enable");
    return page;
  }

  send(method, params = {}) {
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }

  async evaluate(expression) {
    const result = await this.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) {
      const description = result.exceptionDetails.exception?.description;
      throw new Error(description || result.exceptionDetails.text || "browser evaluation failed");
    }
    return result.result.value;
  }

  async waitFor(expression, timeoutMs = 30000) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      if (await this.evaluate(expression)) return;
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
    throw new Error(`Timed out waiting for page condition: ${expression}`);
  }

  async setFile(selector, filePath) {
    const document = await this.send("DOM.getDocument", { depth: 1 });
    const node = await this.send("DOM.querySelector", { nodeId: document.root.nodeId, selector });
    if (!node.nodeId) throw new Error(`file input not found: ${selector}`);
    await this.send("DOM.setFileInputFiles", { nodeId: node.nodeId, files: [path.resolve(filePath)] });
    await this.evaluate(`(() => {
      const input = document.querySelector(${JSON.stringify(selector)});
      if (!input) return false;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    })()`);
  }

  async close() {
    if (this.ownsTarget) {
      try {
        await this.send("Page.close");
      } catch {
        // Closing the target can end the socket before Chrome returns a response.
      }
    }
    this.socket.close();
  }
}

async function clickVisibleText(page, expected) {
  const point = await page.evaluate(`(() => {
    const expected = ${JSON.stringify("__CLICK_TEXT__")};
    const matches = [...document.querySelectorAll('body *')]
      .filter((candidate) => {
        const rect = candidate.getBoundingClientRect();
        const style = getComputedStyle(candidate);
        return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none'
          && candidate.textContent.trim().includes(expected);
      });
    const interactive = matches
      .map((candidate) => candidate.closest('button,[role="button"],a') || candidate)
      .filter((candidate, index, items) => items.indexOf(candidate) === index);
    const element = interactive.sort((left, right) => left.textContent.trim().length - right.textContent.trim().length)[0];
    if (!element) return null;
    const rect = element.getBoundingClientRect();
    return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
  })()`.replace("__CLICK_TEXT__", expected));
  let clicked = false;
  if (point) {
    await page.send("Input.dispatchMouseEvent", { type: "mousePressed", x: point.x, y: point.y, button: "left", clickCount: 1 });
    await page.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: point.x, y: point.y, button: "left", clickCount: 1 });
    clicked = true;
  }
  if (!clicked) {
    const tree = await page.send("Accessibility.getFullAXTree");
    const node = tree.nodes.find((candidate) =>
      candidate.name?.value?.includes(expected) && candidate.backendDOMNodeId
    );
    if (node) {
      const resolved = await page.send("DOM.resolveNode", { backendNodeId: node.backendDOMNodeId });
      await page.send("Runtime.callFunctionOn", {
        objectId: resolved.object.objectId,
        functionDeclaration: "function () { this.click(); return true; }",
        returnByValue: true,
      });
      clicked = true;
    }
  }
  if (!clicked) throw new Error(`visible text not found: ${expected}`);
}

async function inspectTarget(targetId) {
  const response = await fetch(`${endpoint}/json/list`);
  if (!response.ok) throw new Error(`Chrome target listing failed: HTTP ${response.status}`);
  const targets = await response.json();
  const target = targets.find((item) => item.id === targetId);
  if (!target) throw new Error(`Chrome target not found: ${targetId}`);
  const page = await CdpPage.connect(target);
  try {
    if (process.env.INSPECT_CLICK_TEXT) {
      for (const clickText of process.env.INSPECT_CLICK_TEXT.split("|")) {
        await clickVisibleText(page, clickText);
        await new Promise((resolve) => setTimeout(resolve, 2500));
      }
    }
    return await page.evaluate(`(() => ({
      url: location.href,
      title: document.title,
      fields: [...document.querySelectorAll('input,textarea,[contenteditable="true"]')].map((element, index) => ({
        index,
        tag: element.tagName,
        type: element.getAttribute('type'),
        accept: element.getAttribute('accept'),
        placeholder: element.getAttribute('placeholder'),
        testid: element.getAttribute('data-testid'),
        ariaLabel: element.getAttribute('aria-label'),
        contenteditable: element.getAttribute('contenteditable')
      })),
      controls: [...document.querySelectorAll('button,[role="button"],a')].map((element) => element.textContent.trim()).filter(Boolean).slice(0, 80),
      links: [...document.querySelectorAll('a[href]')].map((element) => ({ text: element.textContent.trim(), href: element.href })).filter((item) => item.text).slice(0, 80),
      saveTextNodes: [...document.querySelectorAll('body *')]
        .filter((element) => ["暂存离开", "保存草稿", "存草稿", "Save", "保存"].includes(element.textContent.trim()))
        .slice(0, 20)
        .map((element) => ({
          tag: element.tagName,
          className: String(element.className),
          role: element.getAttribute('role'),
          text: element.textContent.trim(),
          parentTag: element.parentElement?.tagName,
          parentClass: String(element.parentElement?.className || "")
        })),
      addButtons: [...document.querySelectorAll('[data-testid="addButton"]')].map((element) => ({
        tag: element.tagName,
        disabled: element.disabled,
        ariaDisabled: element.getAttribute('aria-disabled'),
        className: String(element.className),
        visible: element.offsetParent !== null
      })),
      bodyText: document.body.innerText.slice(0, 3000)
    }))()`);
  } finally {
    await page.close();
  }
}

async function inspectUrl(url) {
  const page = await CdpPage.open(url);
  try {
    await new Promise((resolve) => setTimeout(resolve, 3000));
    if (process.env.INSPECT_CLICK_TEXT) {
      for (const clickText of process.env.INSPECT_CLICK_TEXT.split("|")) {
        await clickVisibleText(page, clickText);
        await new Promise((resolve) => setTimeout(resolve, 2500));
      }
    }
    return await page.evaluate(`({
      url: location.href,
      title: document.title,
      draftNodes: [...document.querySelectorAll('body *')]
        .filter((element) => ["草稿", "Drafts"].includes(element.textContent.trim()))
        .slice(0, 12)
        .map((element) => ({
          tag: element.tagName,
          role: element.getAttribute('role'),
          testid: element.getAttribute('data-testid'),
          html: element.outerHTML.slice(0, 500),
          parent: element.parentElement?.outerHTML.slice(0, 700)
        })),
      bodyText: document.body.innerText.slice(0, 4000)
    })`);
  } finally {
    await page.close();
  }
}

async function saveXDraft(draft) {
  const posts = draft.content.split("\n\n---\n\n");
  if (posts.length > 4) throw new Error(`X draft has ${posts.length} posts; browser flow supports at most 4`);
  const page = await CdpPage.open("https://x.com/compose/post");
  try {
    const editorSelector = '[role="dialog"] div[data-testid^="tweetTextarea_"]';
    await page.waitFor(`document.querySelector(${JSON.stringify(editorSelector)}) !== null`);
    for (let index = 0; index < posts.length; index += 1) {
      if (index > 0) {
        const added = await page.evaluate(`(() => { const button = document.querySelector('button[data-testid="addButton"]'); if (!button) return false; button.click(); return true; })()`);
        if (!added) throw new Error("X add-to-thread button was not found");
        await page.waitFor(`document.querySelectorAll(${JSON.stringify(editorSelector)}).length > ${index}`);
      }
      const focused = await page.evaluate(`(() => {
        const editor = document.querySelectorAll(${JSON.stringify(editorSelector)})[${index}];
        if (!editor) return false;
        editor.focus();
        return true;
      })()`);
      if (!focused) throw new Error(`X thread editor ${index + 1} was not found`);
      await page.send("Input.insertText", { text: posts[index] });
    }
    const closed = await page.evaluate(`(() => { const button = document.querySelector('button[data-testid="app-bar-close"], button[aria-label="Close"]'); if (!button) return false; button.click(); return true; })()`);
    if (!closed) throw new Error("X close-draft button was not found");
    await page.waitFor(`[...document.querySelectorAll('button,[role="button"]')].some((element) => ["Save", "保存"].includes(element.textContent.trim()))`);
    const saved = await page.evaluate(`(() => { const button = [...document.querySelectorAll('button,[role="button"]')].find((element) => ["Save", "保存"].includes(element.textContent.trim())); if (!button) return false; button.click(); return true; })()`);
    if (!saved) throw new Error("X Save button was not found");
    await new Promise((resolve) => setTimeout(resolve, 3000));
  } finally {
    await page.close();
  }
}

async function verifyXDraft(draft) {
  const page = await CdpPage.open("https://x.com/compose/post");
  try {
    await page.waitFor(`document.querySelector('[role="dialog"] div[data-testid^="tweetTextarea_"]') !== null`);
    const opened = await page.evaluate(`(() => {
      const button = document.querySelector('button[data-testid="unsentButton"]');
      if (!button) return false;
      button.click();
      return true;
    })()`);
    if (!opened) throw new Error("X drafts button was not found");
    await page.waitFor(`location.pathname.includes('/unsent/')`);
    const onDraftsPage = await page.evaluate(`location.pathname.endsWith('/drafts')`);
    if (!onDraftsPage) {
      const draftsSelected = await page.evaluate(`(() => {
        const labels = ["Drafts", "草稿", "Unsent posts", "未发送的帖子"];
        const tab = [...document.querySelectorAll('[role="tab"],a,button')]
          .find((element) => labels.includes(element.textContent.trim()));
        if (!tab) return false;
        tab.click();
        return true;
      })()`);
      if (!draftsSelected) throw new Error("X Drafts tab was not found");
      await page.waitFor(`location.pathname.endsWith('/drafts')`);
    }
    // X can expose any post from a saved thread in the drafts list.
    const markers = draft.content.split("\n\n---\n\n").map((post) => post.split("\n", 1)[0].trim());
    await page.waitFor(`${JSON.stringify(markers)}.some((marker) => document.body.innerText.includes(marker))`, 15000);
  } finally {
    await page.close();
  }
}

async function saveXiaohongshuDraft(draft, coverPath) {
  const page = await CdpPage.open("https://creator.xiaohongshu.com/publish/publish");
  try {
    await page.waitFor(`document.body.innerText.includes("上传图文")`);
    const imageModeSelected = await page.evaluate(`(() => {
      const candidates = [...document.querySelectorAll('button,[role="button"],div')]
        .filter((element) => element.textContent.trim() === "上传图文");
      const target = candidates.find((element) => element.offsetParent !== null);
      if (!target) return false;
      target.click();
      return true;
    })()`);
    if (!imageModeSelected) throw new Error("Xiaohongshu image-post tab was not found");
    const imageInput = 'input[type="file"][accept*=".jpg"], input[type="file"][accept*="image/"]';
    await page.waitFor(`document.querySelector(${JSON.stringify(imageInput)}) !== null`);
    await page.setFile(imageInput, coverPath);
    try {
      await page.waitFor(`document.querySelector('input[placeholder*="标题"], textarea[placeholder*="标题"]') !== null`, 60000);
    } catch (error) {
      const state = await page.evaluate(`({ url: location.href, text: document.body.innerText.slice(0, 1200), files: [...document.querySelectorAll('input[type="file"]')].map((input) => input.files?.length || 0) })`);
      throw new Error(`Xiaohongshu did not enter editor after upload: ${JSON.stringify(state)}`);
    }
    const titleFocused = await page.evaluate(`(() => {
      const element = document.querySelector('input[placeholder*="标题"], textarea[placeholder*="标题"]');
      if (!element) return false;
      element.focus();
      return true;
    })()`);
    if (!titleFocused) throw new Error("Xiaohongshu title editor was not found");
    await page.send("Input.insertText", { text: draft.title });
    const contentSelector = 'div[contenteditable="true"], textarea[placeholder*="正文"], textarea[placeholder*="描述"]';
    await page.waitFor(`document.querySelector(${JSON.stringify(contentSelector)}) !== null`);
    const contentFocused = await page.evaluate(`(() => {
      const element = document.querySelector(${JSON.stringify(contentSelector)});
      if (!element) return false;
      element.focus();
      return true;
    })()`);
    if (!contentFocused) throw new Error("Xiaohongshu content editor was not found");
    await page.send("Input.insertText", { text: draft.content });
    await page.waitFor(`document.querySelector('input[placeholder*="标题"], textarea[placeholder*="标题"]')?.value === ${JSON.stringify(draft.title)}`);
    await new Promise((resolve) => setTimeout(resolve, 5000));
    await page.waitFor(`document.body.innerText.includes("编辑于")`, 30000);
  } finally {
    await page.close();
  }
}

async function verifyXiaohongshuDraft(draft) {
  const page = await CdpPage.open("https://creator.xiaohongshu.com/publish/publish");
  try {
    await page.waitFor(`document.body.innerText.includes("草稿箱")`);
    const draftBoxLabel = await page.evaluate(`document.body.innerText.match(/草稿箱\(\d+\)/)?.[0] || "草稿箱"`);
    await clickVisibleText(page, draftBoxLabel);
    await new Promise((resolve) => setTimeout(resolve, 1500));
    await page.waitFor(`document.body.innerText.includes("图文笔记")`);
    const imageDraftLabel = await page.evaluate(`document.body.innerText.match(/图文笔记\(\d+\)/)?.[0] || "图文笔记"`);
    await clickVisibleText(page, imageDraftLabel);
    await page.waitFor(`document.body.innerText.includes(${JSON.stringify(draft.title)})`, 15000);
  } finally {
    await page.close();
  }
}

async function deliver(platform, action) {
  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  const forcedPlatform = process.env.FORCE_DRAFT_PLATFORM || "";
  if (manifest.platforms[platform].status === "drafted" && forcedPlatform !== platform) {
    process.stdout.write(`${platform} draft already recorded; skipping\n`);
    return;
  }
  try {
    await action();
    updateManifest(platform, "drafted", { delivery: "browser", error: null });
    process.stdout.write(`${platform} draft saved in browser\n`);
  } catch (error) {
    updateManifest(platform, "failed", { delivery: "browser", error: String(error.message || error) });
    throw error;
  }
}

if (process.env.INSPECT_TARGET_ID) {
  process.stdout.write(`${JSON.stringify(await inspectTarget(process.env.INSPECT_TARGET_ID), null, 2)}\n`);
  process.exit(0);
}
if (process.env.INSPECT_URL) {
  process.stdout.write(`${JSON.stringify(await inspectUrl(process.env.INSPECT_URL), null, 2)}\n`);
  process.exit(0);
}

if (!fs.existsSync(manifestPath)) throw new Error(`manifest not found: ${manifestPath}`);
const xDraft = loadJson("x.json");
const xiaohongshuDraft = loadJson("xiaohongshu.json");
const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
if (!manifest.cover) throw new Error("cover image is missing from social draft manifest");

if (process.env.VERIFY_X_DRAFT === "1") {
  await verifyXDraft(xDraft);
  process.stdout.write("x draft verified in browser\n");
  process.exit(0);
}

const failures = [];
for (const [platform, action] of [
  ["xiaohongshu", async () => {
    await saveXiaohongshuDraft(xiaohongshuDraft, manifest.cover);
    await verifyXiaohongshuDraft(xiaohongshuDraft);
  }],
  ["x", async () => {
    await saveXDraft(xDraft);
    await verifyXDraft(xDraft);
  }],
]) {
  try {
    await deliver(platform, action);
  } catch (error) {
    failures.push(`${platform}: ${error.message || error}`);
  }
}
if (failures.length) throw new Error(failures.join("; "));
