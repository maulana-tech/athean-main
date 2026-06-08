import Link from "next/link";

export const metadata = {
  title: "Methodology — Brier decomposition, conformal Kelly, council aggregation",
  description:
    "The math the website is selling. Brier score decomposition. Why aggregation closes 80% of the LLM-vs-human gap. Conformal Kelly intervals. Reproduction commands.",
};

export default function MethodologyPage() {
  return (
    <article className="prose-pantheon space-y-12 py-10">
      <header className="space-y-5">
        <span className="text-caption text-primary">
          Methodology · the math behind the marketing
        </span>
        <h1 className="text-h1 text-foreground">
          How we measure whether the council helps.
        </h1>
        <p className="text-lead max-w-3xl text-muted-foreground">
          Every probabilistic claim on this site reduces to one of three
          measurements: Brier-score decomposition, council aggregation gain,
          and conformal Kelly sizing. This page documents each — formula,
          implementation path, reproduction command.
        </p>
      </header>

      {/* ── Section 1 — Brier decomposition ───────────────────────── */}
      <section className="space-y-5 border-t border-primary/15 pt-10">
        <span className="text-caption text-primary">
          §1 · Brier-score decomposition (Murphy 1973)
        </span>
        <h2 className="text-h2 text-foreground">
          What sharpness, calibration, and resolution actually mean.
        </h2>
        <p className="text-body text-muted-foreground">
          The Brier score on a binary forecast is the mean-squared error
          between predicted probability and realized outcome:
        </p>
        <Formula>
          BS = (1/n) · Σ (p_i − o_i)²
        </Formula>
        <p className="text-body text-muted-foreground">
          Murphy (1973) showed BS decomposes into three terms when forecasts
          are binned by predicted probability:
        </p>
        <Formula>
          BS = Reliability − Resolution + Uncertainty
        </Formula>
        <ul className="text-body space-y-3 text-muted-foreground">
          <li>
            <strong className="font-mono text-foreground">Reliability</strong>{" "}
            measures calibration error. For each probability bin, how far
            does the average forecast differ from the average outcome?
            Lower is better. A perfectly calibrated forecaster has{" "}
            <code className="font-mono text-primary">Reliability = 0</code>.
          </li>
          <li>
            <strong className="font-mono text-foreground">Resolution</strong>{" "}
            measures discrimination. How much does the forecast distinguish
            between events that resolve YES vs NO? Higher is better — but
            only when calibration is held constant.
          </li>
          <li>
            <strong className="font-mono text-foreground">Uncertainty</strong>{" "}
            is a property of the sample, not the forecaster. It equals{" "}
            <code className="font-mono text-primary">ō · (1 − ō)</code> where
            ō is the base rate. A random forecaster matches uncertainty;
            anything below adds value.
          </li>
        </ul>
        <p className="text-body text-muted-foreground">
          Implementation:{" "}
          <code className="font-mono text-primary">
            services/ostrakon/src/ostrakon/brier.py
          </code>
          . Tests:{" "}
          <code className="font-mono text-primary">
            services/ostrakon/tests/test_brier.py
          </code>
          .
        </p>
      </section>

      {/* ── Section 2 — Council aggregation ───────────────────────── */}
      <section className="space-y-5 border-t border-primary/15 pt-10">
        <span className="text-caption text-primary">
          §2 · Council aggregation gain
        </span>
        <h2 className="text-h2 text-foreground">
          Why eleven heads beat one.
        </h2>
        <p className="text-body text-muted-foreground">
          On a 200-market Manifold sample, the empirical Brier scores are:
        </p>
        <Table
          rows={[
            ["Manifold consensus (free human prior)", "0.126"],
            ["Single-shot Gemini", "0.260"],
            ["5-role council, simple mean aggregation", "0.149"],
          ]}
        />
        <p className="text-body text-muted-foreground">
          The council closes <strong>80% of the LLM-vs-human gap</strong>{" "}
          ((0.260 − 0.149) / (0.260 − 0.126) ≈ 0.83) without beating the
          human prior. We treat this as an honest empirical finding: LLMs are
          worse than free human consensus, but aggregating multiple
          structured roles recovers most of the gap. The aggregation gain of
          ~0.11 Brier is an{" "}
          <strong>order of magnitude larger</strong> than any individual data
          source we have falsified to date (best: −0.004 from Wikipedia
          attention).
        </p>
        <p className="text-body text-muted-foreground">
          The aggregation rule is a weighted mean over roles with weights
          tuned via softmax-over-(-Brier) on a calibration set:
        </p>
        <Formula>
          p_council = Σ w_r · p_r , where w_r = softmax(−τ · Brier_r)
        </Formula>
        <p className="text-body text-muted-foreground">
          Implementation:{" "}
          <code className="font-mono text-primary">
            services/ostrakon/src/ostrakon/brier_weighted_council.py
          </code>
          . Tests: 14 hermetic cases covering edge degeneracies (one role,
          tied Briers, single-class outcome).
        </p>
      </section>

      {/* ── Section 3 — Conformal Kelly ───────────────────────────── */}
      <section className="space-y-5 border-t border-primary/15 pt-10">
        <span className="text-caption text-primary">
          §3 · Conformal Kelly (interval-bound sizing)
        </span>
        <h2 className="text-h2 text-foreground">
          Sizing against the lower bound, not the point estimate.
        </h2>
        <p className="text-body text-muted-foreground">
          The classical half-Kelly formula sizes positions against a point
          estimate of the edge. This over-trades whenever the model is
          miscalibrated. We use a conformal prediction interval (Vovk et al)
          and size against the <em>lower</em> bound.
        </p>
        <Formula>
          For YES: p_used = max(0, p_council − q̂_α)
          {"\n"}
          For NO : p_used = 1 − min(1, p_council + q̂_α)
          {"\n\n"}
          half_kelly = max(0, (p_used · b − (1 − p_used)) / b) · 0.5
        </Formula>
        <p className="text-body text-muted-foreground">
          <code className="font-mono text-primary">q̂_α</code> is the
          empirical (1 − α)-quantile of absolute prediction errors on a
          held-out calibration set. With α = 0.10, we&apos;re sizing against
          the 90% lower bound — the model has to be confidently right, not
          just nominally right, before we touch a half-Kelly stake.
        </p>
        <p className="text-body text-muted-foreground">
          Implementation:{" "}
          <code className="font-mono text-primary">
            services/areopagus/src/areopagus/kelly.py:size_position_conformal
          </code>
          .
        </p>
      </section>

      {/* ── Section 4 — Source falsification ──────────────────────── */}
      <section className="space-y-5 border-t border-primary/15 pt-10">
        <span className="text-caption text-primary">
          §4 · Edge-source falsification protocol
        </span>
        <h2 className="text-h2 text-foreground">
          How a source earns the right to influence the prior.
        </h2>
        <p className="text-body text-muted-foreground">
          12 Pythia sources are plumbed into{" "}
          <code className="font-mono text-primary">
            apollo.scorer.MarketSnapshot
          </code>
          . Each contributes an oracle delta clamped to ±0.05. Combined cap
          on the full 7-feature stack: ±0.35.
        </p>
        <p className="text-body text-muted-foreground">
          A source graduates HOLD → ADOPT when its paired Brier-delta on a
          ≥200-market resolved sample beats the council baseline by &gt;
          0.002, with applicability ≥ 5%. Anything below: HOLD (live for
          telemetry, oracle delta forced to zero) or UNTESTABLE (insufficient
          applicable sample).
        </p>
        <p className="text-body text-muted-foreground">
          Currently ADOPTED (2): Wikipedia attention (Δ −0.0040, 33.5%
          applicable), Nitter crowd_sentiment (Δ −0.0040, 36.0%). All others
          stay HOLD or UNTESTABLE pending a Polymarket-flavoured corpus.
        </p>
      </section>

      {/* ── Section 5 — Reproduce locally ─────────────────────────── */}
      <section className="space-y-5 border-t border-primary/15 pt-10">
        <span className="text-caption text-primary">
          §5 · Reproduce every number on this page
        </span>
        <h2 className="text-h2 text-foreground">
          From clone to verified Brier in ~5 minutes.
        </h2>
        <pre className="overflow-x-auto rounded-md border border-primary/15 bg-card/40 p-5 font-mono text-sm leading-[1.6] text-foreground/90">
          {`# clone + install
git clone https://github.com/NAME0x0/Pantheon-Trades.git
cd Pantheon-Trades
pnpm install                          # JS deps
cd contracts && forge test            # 57 contract tests
cd ../services/ostrakon && uv run pytest    # Brier + calibration suite
cd ../boule && uv run pytest          # council aggregation suite

# rerun the 200-market backtest (requires GEMINI_API_KEY in .env)
cd ../..
python scripts/backtest_sources_xml.py \\
  --n 200 \\
  --provider gemini \\
  --model gemini-2.5-flash-lite \\
  --council
# artifact lands in artifacts/sources_brier_<timestamp>.json
# expected total cost: ~$0.12 USD on Gemini flash-lite
`}
        </pre>
        <p className="text-body text-muted-foreground">
          Every number cited on the demo page traces back to one of these
          commands. If a run produces a different number than this site
          claims, that is a bug worth reporting.
        </p>
      </section>

      {/* ── Section 6 — Honest limitations ────────────────────────── */}
      <section className="space-y-5 border-t border-primary/15 pt-10">
        <span className="text-caption text-primary">
          §6 · Honest limitations
        </span>
        <h2 className="text-h2 text-foreground">
          What this methodology does not prove.
        </h2>
        <ul className="text-body space-y-3 text-muted-foreground">
          <li>
            <strong className="font-mono text-foreground">Sample bias.</strong>{" "}
            Manifold markets skew toward niche meta-bets, technology, and
            US politics. Brier numbers may not transfer cleanly to
            Polymarket&apos;s real-money distribution. We&apos;re working
            toward the Polymarket-flavoured corpus once the geo-block proxy
            is deployed.
          </li>
          <li>
            <strong className="font-mono text-foreground">
              Beats LLM, not humans.
            </strong>{" "}
            On this sample, the council improves on a single-shot LLM by
            0.11 Brier but still trails Manifold&apos;s play-money human
            consensus by 0.023 Brier. The system&apos;s alpha is{" "}
            <em>conditional</em> on outperforming LLMs and on edge sources
            that we have not yet falsified at scale.
          </li>
          <li>
            <strong className="font-mono text-foreground">
              No live trading.
            </strong>{" "}
            Every Brier reported here is on resolved historical markets, not
            forward-looking real fills. The transition from backtest to
            production is the next-largest source of variance and is
            currently blocked on geo-bypass + builder-code approval.
          </li>
          <li>
            <strong className="font-mono text-foreground">
              No external audit.
            </strong>{" "}
            Contracts pass Foundry + Halmos symbolic verification on the
            two flagship contracts (PoR + PantheonConstitution). They have
            not been audited by an external security firm. Do not deploy
            to mainnet without one.
          </li>
        </ul>
      </section>

      <footer className="border-t border-primary/15 pt-10">
        <p className="text-body text-muted-foreground">
          Questions on any of the math? Open an issue on{" "}
          <a
            href="https://github.com/NAME0x0/Pantheon-Trades/issues"
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary underline-offset-4 hover:underline"
          >
            GitHub
          </a>{" "}
          or read the council prompts at{" "}
          <Link
            href="/council"
            className="text-primary underline-offset-4 hover:underline"
          >
            /council
          </Link>
          .
        </p>
      </footer>
    </article>
  );
}

function Formula({ children }: { children: React.ReactNode }) {
  return (
    <pre className="overflow-x-auto rounded-md border border-primary/20 bg-primary/[0.04] px-5 py-4 font-mono text-sm leading-[1.7] text-foreground">
      {children}
    </pre>
  );
}

function Table({ rows }: { rows: readonly [string, string][] }) {
  return (
    <div className="overflow-hidden rounded-md border border-primary/15">
      <table className="w-full text-sm">
        <thead className="bg-card/40">
          <tr>
            <th className="px-4 py-2 text-left text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
              Forecaster
            </th>
            <th className="px-4 py-2 text-left text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
              Brier
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-primary/10">
          {rows.map(([forecaster, brier]) => (
            <tr key={forecaster} className="hover:bg-primary/[0.03]">
              <td className="px-4 py-2.5 font-serif text-foreground/90">
                {forecaster}
              </td>
              <td className="px-4 py-2.5">
                <code className="font-mono text-primary">{brier}</code>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
