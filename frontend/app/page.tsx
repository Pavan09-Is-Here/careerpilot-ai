import Link from "next/link";

import GettingStarted from "@/components/dashboard/GettingStarted";

const profileSections = [
  "Candidate profile",
  "Education",
  "Work experience",
  "Projects",
  "Skills",
  "Certifications",
];

const documentSections = [
  {
    label: "Document management",
    href: "/documents",
  },
  {
    label: "CV version history",
    href: "/cv-versions",
  },
];

const jobSections = [
  {
    label: "Job discovery",
    href: "/jobs",
  },
  {
    label: "Connect a company board",
    href: "/job-sources",
  },
  {
    label: "Saved jobs",
    href: "/saved-jobs",
  },
];

const automationSections = [
  {
    label: "Application answers",
    href: "/application-answers",
  },
  {
    label: "Applications",
    href: "/applications",
  },
  {
    label: "Notifications",
    href: "/notifications",
  },
];

type SectionLink = { label: string; href: string };

function SectionCard({
  title,
  description,
  actionLabel,
  actionHref,
  links,
  columns = "sm:grid-cols-2",
}: {
  title: string;
  description: string;
  actionLabel: string;
  actionHref: string;
  links: SectionLink[];
  columns?: string;
}) {
  return (
    <section className="cp-card mt-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">{title}</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 cp-muted">
            {description}
          </p>
        </div>
        <Link
          href={actionHref}
          className="shrink-0 rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-violet-700 transition hover:border-violet-400 hover:bg-violet-50"
        >
          {actionLabel}
        </Link>
      </div>
      <div className={`mt-6 grid gap-3 ${columns}`}>
        {links.map((link) => (
          <Link key={link.href + link.label} href={link.href} className="cp-tile">
            {link.label}
          </Link>
        ))}
      </div>
    </section>
  );
}

export default function DashboardPage() {
  return (
    <main className="cp-page">
      <div className="mx-auto max-w-6xl">
        <header className="mb-10 flex flex-col justify-between gap-6 sm:flex-row sm:items-end">
          <div>
            <p className="cp-eyebrow">CareerPilot AI</p>
            <h1 className="mt-3 text-3xl font-bold text-slate-900 sm:text-4xl">
              Dashboard
            </h1>
            <p className="mt-3 max-w-3xl leading-7 cp-muted">
              Manage verified career facts before using them in CVs,
              matching, and applications.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <Link href="/auth" className="cp-btn-outline">
              Account
            </Link>
            <Link href="/profile" className="cp-btn-primary">
              Open profile management
            </Link>
          </div>
        </header>

        <div className="mb-6">
          <GettingStarted />
        </div>

        <section className="cp-card border-violet-200 bg-violet-50/60">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
            <div>
              <h2 className="text-xl font-semibold text-slate-900">
                Start from your CV
              </h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 cp-muted">
                Upload your CV and we fill in your profile, education,
                projects, and skills. You review everything before it is
                saved.
              </p>
            </div>
            <Link href="/documents" className="cp-btn-primary shrink-0">
              Upload CV
            </Link>
          </div>
        </section>

        <SectionCard
          title="Candidate facts vault"
          description="Profile, education, experience, projects, skills, and certifications are managed from the profile workspace."
          actionLabel="View workspace"
          actionHref="/profile"
          links={profileSections.map((label) => ({ label, href: "/profile" }))}
          columns="sm:grid-cols-2 lg:grid-cols-3"
        />

        <SectionCard
          title="CV documents"
          description="Upload CV files, review extraction and section detection, compare claims to verified facts, and manage generated CV versions."
          actionLabel="Open documents"
          actionHref="/documents"
          links={documentSections}
        />

        <SectionCard
          title="Job discovery"
          description="Browse jobs from approved, compliance-reviewed sources and manage your saved-job review workflow."
          actionLabel="Open job discovery"
          actionHref="/jobs"
          links={jobSections}
        />

        <SectionCard
          title="Automation and alerts"
          description="The pipeline tailors CVs and prepares applications for the latest matching jobs, then notifies you. Submission always stays a human step — nothing is auto-submitted."
          actionLabel="Open applications"
          actionHref="/applications"
          links={automationSections}
        />
      </div>
    </main>
  );
}
