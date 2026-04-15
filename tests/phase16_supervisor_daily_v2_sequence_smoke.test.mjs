import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';

const repo = process.cwd();

test('daily supervisor sequence runs scoring v2 before recommendations and policy', () => {
  const orchestration = readFileSync(path.join(repo, 'packages/supervisor/orchestration/run_supervisor_cycle.py'), 'utf8');
  const scoringIdx = orchestration.indexOf("StepDef('build_scores_v2'");
  const recommendationsIdx = orchestration.indexOf("StepDef('generate_recommendations'");
  const policyIdx = orchestration.indexOf("StepDef('evaluate_policy'");

  assert.equal(scoringIdx !== -1, true, 'build_scores_v2 step missing from daily sequence');
  assert.equal(recommendationsIdx !== -1, true, 'generate_recommendations step missing from daily sequence');
  assert.equal(policyIdx !== -1, true, 'evaluate_policy step missing from daily sequence');
  assert.equal(scoringIdx < recommendationsIdx, true, 'build_scores_v2 should run before generate_recommendations');
  assert.equal(recommendationsIdx < policyIdx, true, 'generate_recommendations should run before evaluate_policy');
});
