import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { AGENT_BY_ID, AGENT_PROMPTS } from "@/lib/agent-prompts";

export const metadata = {
  title: "The Council — eleven prompts, verbatim",
  description:
    "The actual Markdown prompts that define each council agent. No marketing copy — these are the strings shipped to Gemini and Claude.",
};

const ROLE_ORDER = [
  "bull",
  "bear",
  "risk-veto",
  "procedural",
  "execution",
  "adversarial",
] as const;

const ROLE_LABEL: Record<string, string> = {
  bull: "Bull",
  bear: "Bear",
  "risk-veto": "Risk · veto",
  procedural: "Procedural",
  execution: "Execution",
  adversarial: "Adversarial",
};

function resolveAgent(id: string | undefined) {
  if (id && AGENT_BY_ID[id]) return AGENT_BY_ID[id];
  return AGENT_PROMPTS[0];
}

export default function CouncilPage({
  searchParams,
}: {
  searchParams: { agent?: string };
}) {
  const active = resolveAgent(searchParams.agent);

  // Group by role for the sidebar.
  const byRole = ROLE_ORDER.map((r) => ({
    role: r,
    agents: AGENT_PROMPTS.filter((a) => a.role === r),
  }));

  return (
    <div className="py-10">
      <header className="space-y-5">
        <span className="text-caption text-primary">
          The council · eleven prompts, verbatim
        </span>
        <h1 className="text-h1 text-foreground">
          What each agent actually receives.
        </h1>
        <p className="text-lead max-w-3xl text-muted-foreground">
          The system prompt that defines every council role — copied straight
          from <code className="font-mono text-primary">services/boule/src/boule/prompts/</code>{" "}
          with zero edits. No marketing wrapper, no summary. These are the
          strings shipped to Gemini and Claude at every deliberation.
        </p>
      </header>

      <div className="mt-12 grid gap-10 lg:grid-cols-[16rem_1fr]">
        {/* ── Agent index ─────────────────────────────────────────── */}
        <aside className="space-y-6 lg:sticky lg:top-24 lg:self-start">
          {byRole.map(({ role, agents }) => (
            <div key={role}>
              <div className="text-caption mb-2 text-primary/70">
                {ROLE_LABEL[role]}
              </div>
              <ul className="space-y-1.5">
                {agents.map((a) => (
                  <li key={a.id}>
                    <Link
                      href={`/council?agent=${a.id}`}
                      className={`flex items-baseline justify-between rounded px-2 py-1.5 text-sm transition-colors hover:bg-primary/5 ${
                        a.id === active.id
                          ? "bg-primary/10 text-foreground"
                          : "text-muted-foreground"
                      }`}
                    >
                      <span className="font-display tracking-[0.06em]">
                        {a.name}
                      </span>
                      {a.veto && (
                        <Badge
                          variant="destructive"
                          className="ml-2 text-[9px] uppercase tracking-[0.18em]"
                        >
                          veto
                        </Badge>
                      )}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </aside>

        {/* ── Prompt viewer ────────────────────────────────────────── */}
        <article className="space-y-6">
          <header className="space-y-3 border-b border-primary/15 pb-6">
            <div className="text-caption text-primary/80">
              {active.greek} · weight {active.weight.toFixed(1)} ·{" "}
              {ROLE_LABEL[active.role]}
              {active.veto && " · supreme veto"}
            </div>
            <h2 className="text-h2 text-foreground">{active.name}</h2>
            <p className="text-body max-w-2xl italic text-muted-foreground">
              {active.oneLiner}
            </p>
            <a
              href={`https://github.com/NAME0x0/Pantheon-Trades/blob/main/services/boule/src/boule/prompts/${active.id}.md`}
              target="_blank"
              rel="noopener noreferrer"
              className="display inline-flex items-baseline text-[11px] uppercase tracking-[0.28em] text-primary transition-opacity hover:opacity-80"
            >
              View source on GitHub ↗
            </a>
          </header>

          <pre className="overflow-x-auto whitespace-pre-wrap break-words rounded-md border border-primary/15 bg-card/40 p-6 font-mono text-[13px] leading-[1.65] text-foreground/90">
            {active.prompt}
          </pre>

          <p className="text-xs leading-[1.55] text-muted-foreground">
            <strong className="font-mono uppercase tracking-wider text-foreground">
              Verbatim ·
            </strong>{" "}
            this is the exact prompt sent to the LLM at every council round.
            No summarisation. No marketing pass. If you want to audit what the
            system <em>actually</em> thinks any agent should do, this is the
            ground truth.
          </p>
        </article>
      </div>
    </div>
  );
}
