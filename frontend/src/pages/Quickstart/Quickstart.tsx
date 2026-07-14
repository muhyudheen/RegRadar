import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Copy, Check, ArrowRight, ExternalLink } from 'lucide-react';
import Navbar from '../../components/Navbar/Navbar';
import Footer from '../../components/Footer/Footer';
import styles from './Quickstart.module.css';

// Public API host — endpoints live under /v1 (matches the rest of the app).
const API_BASE = 'https://api.lawhook.dev';

/* ─────────────────────────────────────────────
   Code samples — mirror the real backend exactly
   ───────────────────────────────────────────── */

const CURL_CREATE = `curl -X POST ${API_BASE}/v1/subscriptions \\
  -H "Authorization: Bearer lh_live_your_api_key" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "RBI fintech alerts",
    "jurisdiction": "IN",
    "industry": "fintech",
    "topics": ["kyc", "aml"],
    "webhook_url": "https://your-app.com/webhooks/lawhook",
    "severity_min": "major"
  }'`;

const CREATE_RESPONSE = `{
  "id": "8a1b2c3d-4e5f-6789-abcd-ef0123456789",
  "name": "RBI fintech alerts",
  "jurisdiction": "IN",
  "industry": "fintech",
  "topics": ["kyc", "aml"],
  "webhook_url": "https://your-app.com/webhooks/lawhook",
  "severity_min": "major",
  "is_active": true,
  "created_at": "2026-07-14T09:20:00Z",
  "updated_at": "2026-07-14T09:20:00Z",
  "signing_secret": "whsec_a3f8c2d1e9b4f7a2c8d3e1f0b5a9c2d4e7f1a3b8"
}`;

const WEBHOOK_PAYLOAD = `{
  "event": "regulation.changed",
  "delivery_id": "b3d9f0c1-2a34-4b56-8c90-1d2e3f4a5b6c",
  "change_id": "c47a1e02-9f3b-4d81-a0c2-5e6f7a8b9c0d",
  "jurisdiction": "IN",
  "industry": "fintech",
  "topic": "kyc",
  "severity": "critical",
  "summary": "RBI mandates video-KYC re-verification for accounts dormant over 12 months.",
  "source": {
    "authority": "Reserve Bank of India",
    "url": "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx",
    "archived_at": "2026-07-14T09:15:00Z"
  },
  "diff": {
    "added": ["Video-KYC mandatory for accounts dormant more than 12 months"],
    "removed": ["Periodic document upload considered sufficient"],
    "modified": []
  },
  "effective_date": "2026-08-01",
  "detected_at": "2026-07-14T09:14:30Z"
}`;

const VERIFY_PYTHON = `import hashlib
import hmac
import time

from flask import Flask, request, abort

app = Flask(__name__)

# The signing_secret returned once when you created the subscription.
SIGNING_SECRET = "whsec_a3f8c2d1e9b4f7a2c8d3e1f0b5a9c2d4e7f1a3b8"
TOLERANCE_SECONDS = 300  # reject webhooks older than 5 minutes


@app.post("/webhooks/lawhook")
def lawhook_webhook():
    signature = request.headers.get("X-Lawhook-Signature", "")
    timestamp = request.headers.get("X-Lawhook-Timestamp", "")
    body = request.get_data()  # RAW bytes — never re-serialize before verifying

    # 1. Reject stale / replayed webhooks
    try:
        ts = int(timestamp)
    except ValueError:
        abort(400)
    age = int(time.time()) - ts
    if age > TOLERANCE_SECONDS or age < -30:
        abort(400)

    # 2. Recompute the signature over "{timestamp}.{raw_body}"
    signed = timestamp.encode() + b"." + body
    expected = "sha256=" + hmac.new(
        SIGNING_SECRET.encode(), signed, hashlib.sha256
    ).hexdigest()

    # 3. Constant-time compare
    if not hmac.compare_digest(signature, expected):
        abort(401)

    event = request.get_json()
    print("Verified:", event["event"], event["change_id"])
    return "", 204`;

const VERIFY_NODE = `import express from "express";
import crypto from "node:crypto";

const app = express();

// The signing_secret returned once when you created the subscription.
const SIGNING_SECRET = "whsec_a3f8c2d1e9b4f7a2c8d3e1f0b5a9c2d4e7f1a3b8";
const TOLERANCE_SECONDS = 300; // reject webhooks older than 5 minutes

// Capture the RAW body — the signature is over the exact bytes we received.
app.post(
  "/webhooks/lawhook",
  express.raw({ type: "application/json" }),
  (req, res) => {
    const signature = req.get("X-Lawhook-Signature") || "";
    const timestamp = req.get("X-Lawhook-Timestamp") || "";
    const body = req.body; // Buffer

    // 1. Reject stale / replayed webhooks
    const ts = Number.parseInt(timestamp, 10);
    if (!Number.isFinite(ts)) return res.sendStatus(400);
    const age = Math.floor(Date.now() / 1000) - ts;
    if (age > TOLERANCE_SECONDS || age < -30) return res.sendStatus(400);

    // 2. Recompute the signature over "{timestamp}.{raw_body}"
    const signed = Buffer.concat([Buffer.from(timestamp + "."), body]);
    const expected =
      "sha256=" +
      crypto.createHmac("sha256", SIGNING_SECRET).update(signed).digest("hex");

    // 3. Constant-time compare (guard equal length first)
    const a = Buffer.from(signature);
    const b = Buffer.from(expected);
    if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) {
      return res.sendStatus(401);
    }

    const event = JSON.parse(body.toString("utf8"));
    console.log("Verified:", event.event, event.change_id);
    res.sendStatus(204);
  },
);

app.listen(3000);`;

/* ─────────────────────────────────────────────
   Copyable code block
   ───────────────────────────────────────────── */

function CodeBlock({ code, label }: { code: string; label?: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      /* clipboard unavailable — the text can still be selected */
    }
  }

  return (
    <div className={styles.codeBlock}>
      <div className={styles.codeBar}>
        <span className={styles.codeLabel}>{label}</span>
        <button type="button" className={styles.copyBtn} onClick={copy}>
          {copied ? <Check size={13} /> : <Copy size={13} />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre className={styles.pre}>
        <code>{code}</code>
      </pre>
    </div>
  );
}

/** Field row for the payload reference. */
function Field({ name, type, children }: { name: string; type: string; children: React.ReactNode }) {
  return (
    <div className={styles.field}>
      <div className={styles.fieldHead}>
        <code className={styles.fieldName}>{name}</code>
        <span className={styles.fieldType}>{type}</span>
      </div>
      <p className={styles.fieldDesc}>{children}</p>
    </div>
  );
}

/* ─────────────────────────────────────────────
   Page
   ───────────────────────────────────────────── */

export default function Quickstart() {
  return (
    <>
      <Navbar />
      <main className={styles.main}>
        <motion.div
          className={styles.content}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
        >
          <header className={styles.header}>
            <span className={styles.eyebrow}>Docs</span>
            <h1 className={styles.title}>Quickstart</h1>
            <p className={styles.lead}>
              Go from zero to verified regulatory-change webhooks in a few minutes.
              Every request authenticates with{' '}
              <code className={styles.inline}>Authorization: Bearer &lt;api_key&gt;</code>.
            </p>
          </header>

          {/* 1 — API key */}
          <section id="api-key" className={styles.section}>
            <h2 className={styles.h2}>
              <span className={styles.stepNum}>1</span> Get your API key
            </h2>
            <p className={styles.p}>
              Create a free account and generate a key. Your key looks like{' '}
              <code className={styles.inline}>lh_live_…</code> and is shown only once —
              store it somewhere safe. Send it as a Bearer token on every API request.
            </p>
            <Link to="/get-started" className={styles.cta}>
              Get your API key
              <ArrowRight size={15} />
            </Link>
          </section>

          {/* 2 — Create subscription */}
          <section id="subscribe" className={styles.section}>
            <h2 className={styles.h2}>
              <span className={styles.stepNum}>2</span> Create a subscription
            </h2>
            <p className={styles.p}>
              A subscription tells Lawhook which changes to send you and where. Pick a{' '}
              <code className={styles.inline}>jurisdiction</code> (
              <code className={styles.inline}>IN</code>,{' '}
              <code className={styles.inline}>US</code>,{' '}
              <code className={styles.inline}>SG</code>,{' '}
              <code className={styles.inline}>AU</code>), an{' '}
              <code className={styles.inline}>industry</code>, a minimum{' '}
              <code className={styles.inline}>severity_min</code> (
              <code className={styles.inline}>minor</code>,{' '}
              <code className={styles.inline}>major</code>, or{' '}
              <code className={styles.inline}>critical</code>), and your{' '}
              <code className={styles.inline}>webhook_url</code>.
            </p>
            <CodeBlock code={CURL_CREATE} label="POST /v1/subscriptions" />

            <p className={styles.p}>
              A <code className={styles.inline}>201</code> response returns the subscription,
              including a <code className={styles.inline}>signing_secret</code>:
            </p>
            <CodeBlock code={CREATE_RESPONSE} label="201 Created" />

            <div className={styles.callout}>
              <strong className={styles.calloutStrong}>Store the signing_secret now.</strong>{' '}
              It’s returned <em>once only</em>, at creation — it never appears in any later
              response. You’ll need it to verify webhooks (step&nbsp;4).
            </div>
          </section>

          {/* 3 — Receive webhooks */}
          <section id="receive" className={styles.section}>
            <h2 className={styles.h2}>
              <span className={styles.stepNum}>3</span> Receive webhooks
            </h2>
            <p className={styles.p}>
              When a matching change is detected, Lawhook sends a{' '}
              <code className={styles.inline}>POST</code> to your{' '}
              <code className={styles.inline}>webhook_url</code> with this JSON body:
            </p>
            <CodeBlock code={WEBHOOK_PAYLOAD} label="Webhook payload" />

            <div className={styles.fields}>
              <Field name="event" type="string">
                Always <code className={styles.inline}>"regulation.changed"</code>.
              </Field>
              <Field name="delivery_id" type="string">
                Unique id for this delivery attempt — use it for idempotency / dedupe.
              </Field>
              <Field name="change_id" type="string">
                Id of the underlying regulatory change.
              </Field>
              <Field name="jurisdiction" type="string">
                ISO code of the source jurisdiction (e.g. <code className={styles.inline}>IN</code>).
              </Field>
              <Field name="industry" type="string">
                Lowercase industry the change applies to (e.g.{' '}
                <code className={styles.inline}>fintech</code>).
              </Field>
              <Field name="topic" type="string | null">
                Topic within the industry, when known.
              </Field>
              <Field name="severity" type="string | null">
                <code className={styles.inline}>minor</code>,{' '}
                <code className={styles.inline}>major</code>, or{' '}
                <code className={styles.inline}>critical</code>.
              </Field>
              <Field name="summary" type="string | null">
                Plain-language AI summary of what changed.
              </Field>
              <Field name="source" type="object">
                <code className={styles.inline}>authority</code> (issuing body),{' '}
                <code className={styles.inline}>url</code> (source document), and{' '}
                <code className={styles.inline}>archived_at</code> (snapshot timestamp, or{' '}
                <code className={styles.inline}>null</code>).
              </Field>
              <Field name="diff" type="object | null">
                Structured change:{' '}
                <code className={styles.inline}>added</code>,{' '}
                <code className={styles.inline}>removed</code>, and{' '}
                <code className={styles.inline}>modified</code> — each a list of strings.
              </Field>
              <Field name="effective_date" type="string | null">
                When the change takes effect (ISO date).
              </Field>
              <Field name="detected_at" type="string | null">
                When Lawhook detected the change (ISO timestamp).
              </Field>
            </div>

            <p className={styles.p}>
              Each delivery also carries these headers:{' '}
              <code className={styles.inline}>X-Lawhook-Signature</code>,{' '}
              <code className={styles.inline}>X-Lawhook-Timestamp</code>,{' '}
              <code className={styles.inline}>Content-Type: application/json</code>, and{' '}
              <code className={styles.inline}>User-Agent: Lawhook-Webhook/1.0</code>.
            </p>
          </section>

          {/* 4 — Verify signature */}
          <section id="verify" className={styles.section}>
            <h2 className={styles.h2}>
              <span className={styles.stepNum}>4</span> Verify the signature
            </h2>
            <p className={styles.p}>
              Every webhook is signed so you can confirm it genuinely came from Lawhook.
              The <code className={styles.inline}>X-Lawhook-Signature</code> header is{' '}
              <code className={styles.inline}>sha256=&lt;hex&gt;</code>, an{' '}
              <strong className={styles.strong}>HMAC-SHA256</strong> of{' '}
              <code className={styles.inline}>"&#123;timestamp&#125;.&#123;raw_body&#125;"</code>{' '}
              keyed with your subscription’s{' '}
              <code className={styles.inline}>signing_secret</code>, where{' '}
              <code className={styles.inline}>timestamp</code> is the{' '}
              <code className={styles.inline}>X-Lawhook-Timestamp</code> header. Always verify
              against the <strong className={styles.strong}>raw request body</strong> (don’t
              re-serialize the JSON), and reject anything older than 5 minutes.
            </p>

            <CodeBlock code={VERIFY_PYTHON} label="Python — Flask" />
            <CodeBlock code={VERIFY_NODE} label="Node — Express" />
          </section>

          {/* 5 — Next steps */}
          <section id="next" className={styles.section}>
            <h2 className={styles.h2}>
              <span className={styles.stepNum}>5</span> Next steps
            </h2>
            <ul className={styles.linkList}>
              <li>
                <a
                  className={styles.extLink}
                  href={`${API_BASE}/docs`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Full API reference (Swagger) <ExternalLink size={13} />
                </a>
                <span className={styles.linkNote}>
                  Every endpoint, request, and response at{' '}
                  <code className={styles.inline}>{API_BASE}/docs</code>.
                </span>
              </li>
              <li>
                <span className={styles.sdkName}>Python SDK — lawhook</span>
                <span className={styles.linkNote}>
                  <code className={styles.inline}>from lawhook import LawhookClient</code>
                </span>
              </li>
              <li>
                <span className={styles.sdkName}>TypeScript SDK — lawhook</span>
                <span className={styles.linkNote}>
                  <code className={styles.inline}>
                    import &#123; LawhookClient &#125; from "lawhook"
                  </code>
                </span>
              </li>
            </ul>
          </section>
        </motion.div>
      </main>
      <Footer />
    </>
  );
}
