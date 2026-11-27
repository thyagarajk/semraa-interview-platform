/** Levels shown to students and colleges. Thresholds are configurable data, not code. */
export type ReadinessLevel = 'Beginner' | 'Developing' | 'Ready' | 'Strong';

export interface LevelThreshold {
  readonly level: ReadinessLevel;
  readonly minScore: number;
}

/** Picks the level for a score out of 100, using thresholds supplied by the server. */
export function levelForScore(
  score: number,
  thresholds: readonly LevelThreshold[],
): ReadinessLevel | undefined {
  return [...thresholds].sort((a, b) => b.minScore - a.minScore).find((t) => score >= t.minScore)
    ?.level;
}
