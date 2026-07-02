import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function readSource(relativePath) {
  return readFile(
    new URL(`../${relativePath}`, import.meta.url),
    "utf8",
  );
}

test("dashboard links to job discovery and saved jobs", async () => {
  const dashboardSource = await readSource("app/page.tsx");

  assert.match(dashboardSource, /["']\/jobs["']/);
  assert.match(dashboardSource, /["']\/saved-jobs["']/);
});

test("jobs route renders the discovery component", async () => {
  const source = await readSource("app/jobs/page.tsx");

  assert.match(source, /import JobDiscoveryPage/);
  assert.match(source, /<JobDiscoveryPage \/>/);
});

test("job detail route awaits params and passes a numeric id", async () => {
  const source = await readSource(
    "app/jobs/[jobId]/page.tsx",
  );

  assert.match(source, /await params/);
  assert.match(source, /Number\(jobId\)/);
});

test("saved jobs route renders the saved jobs component", async () => {
  const source = await readSource(
    "app/saved-jobs/page.tsx",
  );

  assert.match(source, /import SavedJobsPage/);
  assert.match(source, /<SavedJobsPage \/>/);
});

test("job discovery has no provider setup or credential UI", async () => {
  const source = await readSource(
    "components/jobs/JobDiscoveryPage.tsx",
  );

  assert.doesNotMatch(
    source,
    /credential|api[_-]?key|secret|access[_-]token/i,
  );
  assert.doesNotMatch(source, /setInterval|setTimeout\(.*load/);
});

test("job detail renders provider text without dangerous HTML", async () => {
  const source = await readSource(
    "components/jobs/JobDetailPage.tsx",
  );

  assert.doesNotMatch(source, /dangerouslySetInnerHTML/);
  assert.match(source, /rel="noopener noreferrer"/);
});

test("saved jobs page archives instead of deleting", async () => {
  const source = await readSource(
    "components/jobs/SavedJobsPage.tsx",
  );

  assert.doesNotMatch(source, /DELETE|deleteSavedJob/);
  assert.match(source, /archived/);
});

test("job api functions validate ids and use bounded pages", async () => {
  const source = await readSource("lib/api.ts");

  assert.match(source, /getJobs/);
  assert.match(source, /getJobDuplicates/);
  assert.match(source, /updateSavedJob/);
  assert.match(
    source,
    /assertPositiveIntegerId\(jobId, "job id"\)/,
  );
});
