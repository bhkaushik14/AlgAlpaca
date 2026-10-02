const superscripts: Record<string, string> = { '2': '²', '3': '³', '4': '⁴' }

/** Display-only notation for the small set of syntax patterns we can render unambiguously. */
export function formatMathNotation(raw: string): string {
  const intervalUnion = /^Union\(Interval\.open\(-oo,\s*([^(),]+)\),\s*Interval\.open\(([^(),]+),\s*oo\)\)$/u.exec(raw.trim())
  if (intervalUnion) return `(−∞, ${intervalUnion[1].trim()}) ∪ (${intervalUnion[2].trim()}, ∞)`

  return raw
    .replace(/\bsqrt\(\s*(\d+(?:\.\d+)?)\s*\)/gu, '√$1')
    .replace(/\bAbs\(([^()]*)\)/gu, '|$1|')
    .replace(/([A-Za-z0-9)])\*\*([234])\b/gu, (_match, base: string, exponent: string) => `${base}${superscripts[exponent]}`)
    .replace(/(\d+)\s*\*\s*(√\d+(?:\.\d+)?)/gu, '$1$2')
    .replace(/(\d+)\s*\*\s*([A-Za-z])/gu, '$1$2')
    .replace(/\)\s*\*\s*\(/gu, ')(')
    .replace(/(?<!\*)\*(?!\*)/gu, '·')
    .replace(/-(?=\s*(?:\d|√|x|\())/gu, '−')
}
