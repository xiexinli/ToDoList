"use client";
/**
 * 页面骨架模板：客户端组件 + localStorage，符合 eslint-config-next 16 的 React Compiler 规则。
 * 要点：
 * - 不要在 useEffect 里 setState 读 localStorage（会被 react-hooks/set-state-in-effect 判 error）。
 *   用 useState 的 lazy initializer 读取，并让页面以 ssr:false 动态加载（避免 SSR 时没有 window）。
 * - 写入 localStorage 放在事件处理里或 useEffect（只写不 setState）。
 * 用法：在 src/app/page.tsx 里（Next 16：`ssr:false` 只能在 Client Component 里用，所以 page.tsx 也要 "use client"）
 *   "use client";
 *   import dynamic from "next/dynamic";
 *   const Client = dynamic(() => import("./client"), { ssr: false });
 *   export default function Page() { return <Client />; }
 */
import { useEffect, useState } from "react";

const KEY = "<feature>:history";

type HistoryItem = { id: string; createdAt: string; summary: string };

function load(): HistoryItem[] {
  try {
    return JSON.parse(window.localStorage.getItem(KEY) ?? "[]");
  } catch {
    return [];
  }
}

export default function Client() {
  const [history, setHistory] = useState<HistoryItem[]>(() => load());
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<unknown>(null);

  useEffect(() => {
    window.localStorage.setItem(KEY, JSON.stringify(history)); // 只写，不 setState
  }, [history]);

  async function submit(form: FormData) {
    setBusy(true);
    try {
      const res = await fetch("/api/<route>", { method: "POST", body: form });
      const body = await res.json();
      setResult(body);
      if (res.ok) setHistory((h) => [{ id: body.jobId ?? body.sessionId, createdAt: new Date().toISOString(), summary: "…" }, ...h].slice(0, 20));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-4xl p-6 space-y-6">
      <h1 className="text-2xl font-semibold">&lt;feature 标题&gt;</h1>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void submit(new FormData(e.currentTarget));
        }}
        className="space-y-3"
      >
        {/* 表单控件 */}
        <button disabled={busy} className="rounded bg-black px-4 py-2 text-white disabled:opacity-50">
          {busy ? "处理中…" : "提交"}
        </button>
      </form>
      {result ? <pre className="overflow-auto rounded bg-gray-50 p-3 text-xs">{JSON.stringify(result, null, 2)}</pre> : null}
      <section>
        <h2 className="font-medium">历史（localStorage）</h2>
        <ul className="text-sm">
          {history.map((h) => (
            <li key={h.id}>{h.createdAt} · {h.id} · {h.summary}</li>
          ))}
        </ul>
      </section>
    </main>
  );
}
