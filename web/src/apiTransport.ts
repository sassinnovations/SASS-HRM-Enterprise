/** Shared API network transport for all SASS HRM screens.
 * Keeps browser fetch semantics while standardizing outages, expired sessions
 * and slow requests. Never logs tokens, passwords or response bodies.
 */
export const HRM_SESSION_EXPIRED = 'sass-hrm:session-expired';
export const HRM_CONNECTION_LOST = 'sass-hrm:connection-lost';
export const HRM_CONNECTION_RESTORED = 'sass-hrm:connection-restored';
export const DEFAULT_API_TIMEOUT_MS = 25000;

let sessionEventToken: string | null = null;
let connectionUnavailable = false;

export async function hrmFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  const controller = new AbortController();
  let timedOut = false;
  const timeout = window.setTimeout(() => { timedOut = true; controller.abort(); }, DEFAULT_API_TIMEOUT_MS);
  const callerSignal = init.signal;
  const cancel = () => controller.abort();
  if (callerSignal?.aborted) controller.abort();
  else callerSignal?.addEventListener('abort', cancel, { once: true });
  try {
    const response = await fetch(input, { ...init, signal: controller.signal, cache: init.cache ?? 'no-store' });
    // Only a successful request confirms connectivity; 403 is a permission denial, not logout.
    if (response.ok && connectionUnavailable) {
      connectionUnavailable = false;
      window.dispatchEvent(new Event(HRM_CONNECTION_RESTORED));
    }
    const headers = new Headers(init.headers ?? (input instanceof Request ? input.headers : undefined));
    const authorization = headers.get('Authorization') || '';
    const currentToken = sessionStorage.getItem('sass_token');
    if (response.status === 401 && currentToken && authorization === `Bearer ${currentToken}`) {
      if (sessionEventToken !== currentToken) {
        sessionEventToken = currentToken;
        window.dispatchEvent(new Event(HRM_SESSION_EXPIRED));
      }
    } else if (response.ok && currentToken && sessionEventToken !== currentToken) {
      sessionEventToken = null;
    }
    return response;
  } catch (error) {
    if (callerSignal?.aborted && !timedOut) throw error;
    if (!connectionUnavailable) {
      connectionUnavailable = true;
      window.dispatchEvent(new Event(HRM_CONNECTION_LOST));
    }
    if (timedOut) throw new Error('The server took too long to respond. Check the API connection and use Refresh data.');
    throw new Error('Cannot connect to the SASS HRM API. Check Docker and the backend health, then use Refresh data.');
  } finally {
    window.clearTimeout(timeout);
    callerSignal?.removeEventListener('abort', cancel);
  }
}
