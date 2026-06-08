/**
 * Robust error-message extractor for wallet / RPC / fetch errors.
 *
 * EIP-1193 provider errors are plain objects shaped like
 *   `{ code: number, message: string, data?: { message?: string } }`
 * and are NOT `Error` instances. Calling `String(e)` on them yields the
 * useless string "[object Object]". This helper walks the common shapes
 * (MetaMask, Rabby, Coinbase Wallet, viem, ethers, plain fetch) and
 * always returns a human-readable string.
 *
 * Use everywhere we render a user-facing error message — `setErr`,
 * toast text, status objects, etc. Never call `String(e)` directly on
 * caught errors that may have come from a wallet provider.
 */
export function errorMessage(e: unknown): string {
  if (e == null) return "Unknown error";
  if (typeof e === "string") return e;
  if (e instanceof Error) return e.message || e.name || "Error";

  if (typeof e === "object") {
    const obj = e as {
      message?: unknown;
      reason?: unknown;
      shortMessage?: unknown;
      data?: { message?: unknown };
      error?: { message?: unknown };
      cause?: { message?: unknown };
      code?: unknown;
    };

    if (typeof obj.shortMessage === "string" && obj.shortMessage.length > 0) {
      return obj.shortMessage;
    }
    if (typeof obj.message === "string" && obj.message.length > 0) {
      return obj.message;
    }
    if (typeof obj.reason === "string" && obj.reason.length > 0) {
      return obj.reason;
    }
    if (typeof obj.data?.message === "string" && obj.data.message.length > 0) {
      return obj.data.message;
    }
    if (typeof obj.error?.message === "string" && obj.error.message.length > 0) {
      return obj.error.message;
    }
    if (typeof obj.cause?.message === "string" && obj.cause.message.length > 0) {
      return obj.cause.message;
    }
    if (typeof obj.code === "number" || typeof obj.code === "string") {
      return `Wallet error (code ${obj.code})`;
    }
    try {
      const s = JSON.stringify(e);
      if (s && s !== "{}" && s.length < 200) return s;
    } catch {
      // fall through
    }
  }
  return "Unknown error";
}
