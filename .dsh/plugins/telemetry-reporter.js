/**
 * DSH Structured Telemetry Reporter (Plugin / Lifecycle Hook)
 *
 * Implements Architecture A: Direct JSON Telemetry Ingestion modeled after
 * OpenTelemetry, Datadog, and Sentry span/event structures.
 *
 * Emits zero-buffering HTTP payloads directly to FastAPI `/api/telemetry` (< 5ms latency).
 */
const http = require('http');
const https = require('https');

function sendTelemetry(event) {
  const telemetryUrl = process.env.DSH_TELEMETRY_URL || 'http://127.0.0.1:8000/api/telemetry';
  try {
    const url = new URL(telemetryUrl);
    const isHttps = url.protocol === 'https:';
    const client = isHttps ? https : http;
    const defaultPort = isHttps ? 443 : 80;
    const body = JSON.stringify({
      timestamp: Date.now() / 1000,
      service: 'dsh-coding-pipeline',
      environment: process.env.ENVIRONMENT || 'local',
      trace_id: process.env.DSH_TRACE_ID || undefined,
      issue_id: process.env.DSH_ISSUE_ID || undefined,
      branch: process.env.DSH_BRANCH || undefined,
      stage: process.env.DSH_STAGE || undefined,
      event_type: event.type || event.event_type || 'thought',
      message: event.message || event.thought || event.line || '',
      payload: event.payload || event.data || {},
      tokens: event.tokens || undefined,
      metrics: event.metrics || undefined,
      tags: {
        model: process.env.AGENT_MODEL || process.env.OPENAI_MODEL || 'unknown',
        ...(event.tags || {}),
      },
    });

    const req = client.request(
      {
        hostname: url.hostname,
        port: url.port ? Number(url.port) : defaultPort,
        path: url.pathname + url.search,
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(body),
        },
        timeout: 2000,
      },
      (res) => {
        res.resume();
      }
    );

    req.on('timeout', () => req.destroy());
    req.on('error', () => {}); // Fail-safe non-blocking
    req.write(body);
    req.end();
  } catch (_) {
    // Fail-safe
  }
}

// Cordis / DSH Plugin Interface
module.exports = {
  name: 'dsh-telemetry-reporter',
  apply(ctx) {
    if (!ctx || typeof ctx.on !== 'function') return;

    ctx.on('thought', (thought) => {
      sendTelemetry({ type: 'thought', message: String(thought) });
    });

    ctx.on('tool_call', (toolName, params) => {
      sendTelemetry({
        type: 'tool_call',
        message: `Execute tool: ${toolName}`,
        payload: { tool: toolName, params },
      });
    });

    ctx.on('api_call', (endpoint, metrics) => {
      sendTelemetry({
        type: 'api_call',
        message: `API request to ${endpoint}`,
        metrics,
      });
    });

    ctx.on('token_usage', (tokens) => {
      sendTelemetry({
        type: 'token_usage',
        tokens,
      });
    });

    ctx.on('step', (stepInfo) => {
      sendTelemetry({
        type: 'step',
        payload: stepInfo,
      });
    });
  },
  sendTelemetry,
};
