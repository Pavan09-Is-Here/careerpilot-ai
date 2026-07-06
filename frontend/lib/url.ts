/**
 * Returns the given URL only when it parses as an absolute
 * http: or https: URL. Anything else (javascript:, data:,
 * relative paths, malformed values) yields undefined so the
 * caller can render plain text or omit the link entirely.
 */
export function safeExternalHref(
  url: string | null | undefined,
): string | undefined {
  if (!url) {
    return undefined;
  }

  try {
    const parsed = new URL(url);

    if (
      parsed.protocol === "http:" ||
      parsed.protocol === "https:"
    ) {
      return url;
    }
  } catch {
    // Not a parseable absolute URL.
  }

  return undefined;
}
