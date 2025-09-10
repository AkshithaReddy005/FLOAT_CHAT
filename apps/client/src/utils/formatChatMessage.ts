// Utility to convert safe markdown bold (**text**) into HTML <strong>
// and to remove emojis and escape any HTML to avoid XSS.
export function formatChatMessage(input: string): string {
  // Defensive: ensure we always work with a string
  if (input == null) return '';
  const raw = String(input);

  // Remove only high-plane emoji characters while keeping basic punctuation
  // and ASCII characters intact. This targets common emoji codepoint ranges
  // and avoids accidentally removing parentheses, asterisks, or other ASCII.
  const stripEmojis = (s: string) =>
    s.replace(/([\u{1F300}-\u{1F5FF}]|[\u{1F600}-\u{1F64F}]|[\u{1F680}-\u{1F6FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}])/gu, '');

  const withoutEmojis = stripEmojis(raw);

  // Escape HTML to prevent injection. We will then convert **bold** to <strong> tags.
  const escapeHtml = (s: string) =>
    s
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');

  const escaped = escapeHtml(withoutEmojis);

  // Convert **bold** to <strong> — non-greedy so multiple bolds work.
  // We intentionally avoid any aggressive Unicode stripping here because it
  // previously removed valid characters in some responses.
  const withBold = escaped.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

  // Preserve line breaks
  const withBreaks = withBold.replace(/\r\n|\r|\n/g, '<br/>');

  return withBreaks;
}
