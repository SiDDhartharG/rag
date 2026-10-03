import type { Strategy } from '../types'

const DOC_TOKENS = 1000
const TICKS = [0, 250, 500, 750, 1000]

interface Span {
  start: number
  end: number
}

/** Same windowing as the backend's "fixed" chunker: step by (size - overlap), stop when a window reaches the end. */
function chunkSpans(chunkTokens: number, overlap: number): Span[] {
  const step = chunkTokens - overlap
  if (step < 1 || chunkTokens < 1) return []
  const spans: Span[] = []
  for (let start = 0; start < DOC_TOKENS; start += step) {
    spans.push({ start, end: Math.min(start + chunkTokens, DOC_TOKENS) })
    if (start + chunkTokens >= DOC_TOKENS) break
  }
  return spans
}

interface Props {
  chunkTokens: number
  overlap: number
  strategy: Strategy
}

/** Draws a sample 1,000-token document cut at the current settings. Overlap shows as pink bands. */
export function ChunkRuler({ chunkTokens, overlap, strategy }: Props) {
  const usesOverlap = strategy === 'fixed'
  const effectiveOverlap = usesOverlap ? overlap : 0
  const spans = chunkSpans(chunkTokens, effectiveOverlap)
  const label =
    spans.length === 0
      ? 'Chunk size and overlap do not produce a valid layout'
      : `A 1,000-token document becomes ${spans.length} chunks of up to ${chunkTokens} tokens`

  return (
    <figure className="ruler">
      <svg
        className="ruler__svg"
        viewBox={`0 0 ${DOC_TOKENS} 56`}
        preserveAspectRatio="none"
        role="img"
        aria-label={label}
      >
        {spans.slice(0, -1).map((s, i) => {
          const next = spans[i + 1]
          return effectiveOverlap > 0 ? (
            <rect key={`o${i}`} className="ruler__overlap" x={next.start} y={0} width={s.end - next.start} height={56} />
          ) : null
        })}
        {spans.map((s, i) => (
          <rect
            key={i}
            className="ruler__chunk"
            x={s.start}
            y={i % 2 === 0 ? 6 : 31}
            width={s.end - s.start}
            height={19}
            rx={2}
          />
        ))}
      </svg>
      <div className="ruler__axis" aria-hidden="true">
        {TICKS.map((t) => (
          <span key={t} style={{ left: `${(t / DOC_TOKENS) * 100}%` }}>
            {t}
          </span>
        ))}
      </div>
      <figcaption className="ruler__caption">
        <strong>{spans.length > 0 ? `${spans.length} chunks` : 'No valid layout'}</strong> from a 1,000-token document.
        {usesOverlap
          ? effectiveOverlap > 0
            ? ` Pink is the ${effectiveOverlap} tokens each chunk shares with the next.`
            : ' No overlap: a sentence cut at a boundary is lost to both chunks.'
          : ` Upper bound: ${strategy} chunking ends chunks earlier, at natural breaks.`}
      </figcaption>
    </figure>
  )
}
