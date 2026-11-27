import { levelForScore, LevelThreshold } from './readiness-level';

const thresholds: LevelThreshold[] = [
  { level: 'Beginner', minScore: 0 },
  { level: 'Developing', minScore: 40 },
  { level: 'Ready', minScore: 65 },
  { level: 'Strong', minScore: 85 },
];

describe('levelForScore', () => {
  it('maps scores to levels from configured thresholds', () => {
    expect(levelForScore(10, thresholds)).toBe('Beginner');
    expect(levelForScore(65, thresholds)).toBe('Ready');
    expect(levelForScore(99, thresholds)).toBe('Strong');
  });
});
