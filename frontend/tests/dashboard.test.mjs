import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("dashboard links to profile management", async () => {
  const dashboardSource = await readFile(
    new URL("../app/page.tsx", import.meta.url),
    "utf8",
  );

  assert.match(dashboardSource, /href="\/profile"/);
  assert.doesNotMatch(
    dashboardSource,
    /saveCandidateProfile|getCandidateProfile/,
  );
});

test("profile route renders the shared profile form", async () => {
  const profilePageSource = await readFile(
    new URL("../app/profile/page.tsx", import.meta.url),
    "utf8",
  );

  assert.match(
    profilePageSource,
    /import CandidateProfileForm/,
  );
  assert.match(
    profilePageSource,
    /<CandidateProfileForm \/>/,
  );
});

test("empty profile form does not seed candidate-specific facts", async () => {
  const profileFormSource = await readFile(
    new URL(
      "../components/profile/CandidateProfileForm.tsx",
      import.meta.url,
    ),
    "utf8",
  );

  assert.match(profileFormSource, /full_name:\s*""/);
  assert.match(profileFormSource, /email:\s*""/);
  assert.match(profileFormSource, /linkedin_url:\s*""/);
  assert.match(profileFormSource, /github_url:\s*""/);
  assert.match(profileFormSource, /portfolio_url:\s*""/);
  assert.match(profileFormSource, /target_roles:\s*""/);
});
