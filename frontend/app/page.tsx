import Link from "next/link";

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

export default function DashboardPage() {
  return (
    <main className="min-h-screen bg-slate-950 px-5 py-10 text-white">
      <div className="mx-auto max-w-6xl">
        <header className="mb-10 flex flex-col justify-between gap-6 sm:flex-row sm:items-end">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.25em] text-blue-400">
              CareerPilot AI
            </p>

            <h1 className="mt-3 text-3xl font-bold sm:text-4xl">
              Dashboard
            </h1>

            <p className="mt-3 max-w-3xl leading-7 text-slate-400">
              Manage verified career facts before using
              them in CVs, matching, and applications.
            </p>
          </div>

          <Link
            href="/profile"
            className="inline-flex rounded-xl bg-blue-600 px-6 py-3 font-semibold transition hover:bg-blue-500"
          >
            Open profile management
          </Link>
        </header>

        <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
            <div>
              <h2 className="text-xl font-semibold">
                Candidate facts vault
              </h2>

              <p className="mt-2 text-sm leading-6 text-slate-400">
                Profile, education, experience, projects,
                skills, and certifications are managed from
                the existing profile workspace.
              </p>
            </div>

            <Link
              href="/profile"
              className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-medium text-blue-300 transition hover:border-blue-500"
            >
              View workspace
            </Link>
          </div>

          <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {profileSections.map((section) => (
              <Link
                key={section}
                href="/profile"
                className="rounded-xl border border-slate-800 bg-slate-950 p-4 text-sm font-medium text-slate-200 transition hover:border-blue-500 hover:text-blue-300"
              >
                {section}
              </Link>
            ))}
          </div>
        </section>

        <section className="mt-6 rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
            <div>
              <h2 className="text-xl font-semibold">
                CV documents
              </h2>

              <p className="mt-2 text-sm leading-6 text-slate-400">
                Upload CV files, review extraction and
                section detection, compare claims to
                verified facts, and manage generated CV
                versions.
              </p>
            </div>

            <Link
              href="/documents"
              className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-medium text-blue-300 transition hover:border-blue-500"
            >
              Open documents
            </Link>
          </div>

          <div className="mt-6 grid gap-3 sm:grid-cols-2">
            {documentSections.map((section) => (
              <Link
                key={section.href}
                href={section.href}
                className="rounded-xl border border-slate-800 bg-slate-950 p-4 text-sm font-medium text-slate-200 transition hover:border-blue-500 hover:text-blue-300"
              >
                {section.label}
              </Link>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
