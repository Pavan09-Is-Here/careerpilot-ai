"use client";

import {
  useEffect,
  useState,
  type FormEvent,
} from "react";

import {
  createProject,
  deleteProject,
  getProjectRecords,
  updateProject,
} from "@/lib/api";

import type {
  Project,
  ProjectInput,
} from "@/types/project";

type ProjectFormState = {
  name: string;
  role: string;
  project_type: string;
  description: string;
  start_date: string;
  end_date: string;
  is_current: boolean;
  project_url: string;
  github_url: string;
  technologies: string;
  features: string;
  achievements: string;
  verified: boolean;
};

const emptyProjectForm: ProjectFormState = {
  name: "",
  role: "",
  project_type: "",
  description: "",
  start_date: "",
  end_date: "",
  is_current: false,
  project_url: "",
  github_url: "",
  technologies: "",
  features: "",
  achievements: "",
  verified: false,
};

function optionalText(value: string): string | null {
  const cleanedValue = value.trim();

  return cleanedValue || null;
}

function splitCommaValues(value: string): string[] {
  const uniqueValues = new Map<string, string>();

  for (const item of value.split(",")) {
    const cleanedItem = item.trim();

    if (cleanedItem) {
      uniqueValues.set(
        cleanedItem.toLowerCase(),
        cleanedItem,
      );
    }
  }

  return Array.from(uniqueValues.values());
}

function splitLineValues(value: string): string[] {
  const uniqueValues = new Map<string, string>();

  for (const item of value.split("\n")) {
    const cleanedItem = item.trim();

    if (cleanedItem) {
      uniqueValues.set(
        cleanedItem.toLowerCase(),
        cleanedItem,
      );
    }
  }

  return Array.from(uniqueValues.values());
}

function formToPayload(
  form: ProjectFormState,
): ProjectInput {
  return {
    name: form.name.trim(),
    role: optionalText(form.role),
    project_type: optionalText(form.project_type),
    description: form.description.trim(),

    start_date: form.start_date
      ? form.start_date
      : null,

    end_date:
      form.is_current || !form.end_date
        ? null
        : form.end_date,

    is_current: form.is_current,

    project_url: optionalText(
      form.project_url,
    ),

    github_url: optionalText(
      form.github_url,
    ),

    technologies: splitCommaValues(
      form.technologies,
    ),

    features: splitLineValues(
      form.features,
    ),

    achievements: splitLineValues(
      form.achievements,
    ),

    verified: form.verified,
  };
}

function projectToForm(
  project: Project,
): ProjectFormState {
  return {
    name: project.name,
    role: project.role ?? "",
    project_type: project.project_type ?? "",
    description: project.description,
    start_date: project.start_date ?? "",
    end_date: project.end_date ?? "",
    is_current: project.is_current,
    project_url: project.project_url ?? "",
    github_url: project.github_url ?? "",
    technologies: project.technologies.join(", "),
    features: project.features.join("\n"),
    achievements: project.achievements.join("\n"),
    verified: project.verified,
  };
}

function formatDate(value: string | null): string {
  if (!value) {
    return "Not specified";
  }

  const date = new Date(`${value}T00:00:00`);

  return date.toLocaleDateString(undefined, {
    month: "short",
    year: "numeric",
  });
}

export default function ProjectManager() {
  const [records, setRecords] = useState<Project[]>(
    [],
  );

  const [form, setForm] =
    useState<ProjectFormState>(emptyProjectForm);

  const [editingId, setEditingId] =
    useState<number | null>(null);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [deletingId, setDeletingId] =
    useState<number | null>(null);

  const [successMessage, setSuccessMessage] =
    useState("");

  const [errorMessage, setErrorMessage] =
    useState("");

  useEffect(() => {
    void loadProjects();
  }, []);

  async function loadProjects(): Promise<void> {
    try {
      setLoading(true);
      setErrorMessage("");

      const projectRecords =
        await getProjectRecords();

      setRecords(projectRecords);
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Unable to load project records.",
      );
    } finally {
      setLoading(false);
    }
  }

  function updateField<
    K extends keyof ProjectFormState,
  >(
    field: K,
    value: ProjectFormState[K],
  ): void {
    setForm((currentForm) => ({
      ...currentForm,
      [field]: value,
    }));
  }

  function resetForm(): void {
    setForm(emptyProjectForm);
    setEditingId(null);
  }

  function beginEditing(project: Project): void {
    setForm(projectToForm(project));
    setEditingId(project.id);
    setSuccessMessage("");
    setErrorMessage("");

    document
      .getElementById("project-form")
      ?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
  }

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    setSuccessMessage("");
    setErrorMessage("");

    if (!form.name.trim()) {
      setErrorMessage(
        "Project name is required.",
      );
      return;
    }

    if (form.description.trim().length < 10) {
      setErrorMessage(
        "Project description must contain at least 10 characters.",
      );
      return;
    }

    if (
      !form.is_current &&
      form.start_date &&
      form.end_date &&
      form.end_date < form.start_date
    ) {
      setErrorMessage(
        "End date cannot be before start date.",
      );
      return;
    }

    if (
      form.project_url.trim() &&
      !form.project_url.startsWith("http://") &&
      !form.project_url.startsWith("https://")
    ) {
      setErrorMessage(
        "Project URL must start with http:// or https://.",
      );
      return;
    }

    if (
      form.github_url.trim() &&
      !form.github_url.startsWith("http://") &&
      !form.github_url.startsWith("https://")
    ) {
      setErrorMessage(
        "GitHub URL must start with http:// or https://.",
      );
      return;
    }

    try {
      setSaving(true);

      if (editingId === null) {
        await createProject(
          formToPayload(form),
        );

        setSuccessMessage(
          "Project added successfully.",
        );
      } else {
        await updateProject(
          editingId,
          formToPayload(form),
        );

        setSuccessMessage(
          "Project updated successfully.",
        );
      }

      resetForm();
      await loadProjects();
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Unable to save project.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(
    projectId: number,
  ): Promise<void> {
    const confirmed = window.confirm(
      "Delete this project record?",
    );

    if (!confirmed) {
      return;
    }

    try {
      setDeletingId(projectId);
      setSuccessMessage("");
      setErrorMessage("");

      await deleteProject(projectId);

      if (editingId === projectId) {
        resetForm();
      }

      setSuccessMessage(
        "Project deleted successfully.",
      );

      await loadProjects();
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Unable to delete project.",
      );
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <section className="mt-12">
      <div className="mb-6">
        <p className="text-sm font-semibold uppercase tracking-[0.25em] text-blue-400">
          Verified facts vault
        </p>

        <h2 className="mt-3 text-3xl font-bold">
          Projects
        </h2>

        <p className="mt-3 max-w-3xl leading-7 text-slate-400">
          Store genuine AI, machine learning,
          full-stack, academic, freelance, and
          personal projects.
        </p>
      </div>

      {successMessage && (
        <div className="mb-6 rounded-xl border border-emerald-800 bg-emerald-950/50 p-4 text-emerald-300">
          {successMessage}
        </div>
      )}

      {errorMessage && (
        <div className="mb-6 rounded-xl border border-red-900 bg-red-950/50 p-4 text-red-300">
          {errorMessage}
        </div>
      )}

      <div className="grid gap-8 xl:grid-cols-[1.1fr_0.9fr]">
        <form
          id="project-form"
          onSubmit={(event) =>
            void handleSubmit(event)
          }
          className="rounded-2xl border border-slate-800 bg-slate-900 p-6"
        >
          <div className="mb-6 flex items-center justify-between gap-4">
            <div>
              <h3 className="text-xl font-semibold">
                {editingId === null
                  ? "Add project"
                  : "Edit project"}
              </h3>

              <p className="mt-2 text-sm text-slate-400">
                Enter one feature or achievement
                per line.
              </p>
            </div>

            {editingId !== null && (
              <button
                type="button"
                onClick={resetForm}
                className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:border-slate-500"
              >
                Cancel editing
              </button>
            )}
          </div>

          <div className="space-y-5">
            <TextField
              label="Project name *"
              value={form.name}
              required
              placeholder="LearnForge AI"
              onChange={(value) =>
                updateField("name", value)
              }
            />

            <div className="grid gap-5 md:grid-cols-2">
              <TextField
                label="Your role"
                value={form.role}
                placeholder="AI & Full Stack Developer"
                onChange={(value) =>
                  updateField("role", value)
                }
              />

              <TextField
                label="Project type"
                value={form.project_type}
                placeholder="AI Education Platform"
                onChange={(value) =>
                  updateField(
                    "project_type",
                    value,
                  )
                }
              />
            </div>

            <TextAreaField
              label="Project description *"
              value={form.description}
              placeholder="Explain what the project does, why it was created, and your contribution."
              required
              onChange={(value) =>
                updateField(
                  "description",
                  value,
                )
              }
            />

            <div className="grid gap-5 md:grid-cols-2">
              <TextField
                label="Start date"
                type="date"
                value={form.start_date}
                onChange={(value) =>
                  updateField(
                    "start_date",
                    value,
                  )
                }
              />

              <TextField
                label="End date"
                type="date"
                value={form.end_date}
                disabled={form.is_current}
                onChange={(value) =>
                  updateField("end_date", value)
                }
              />
            </div>

            <CheckboxField
              label="I am currently working on this project"
              checked={form.is_current}
              onChange={(checked) => {
                updateField(
                  "is_current",
                  checked,
                );

                if (checked) {
                  updateField("end_date", "");
                }
              }}
            />

            <div className="grid gap-5 md:grid-cols-2">
              <TextField
                label="Project URL"
                type="url"
                value={form.project_url}
                placeholder="https://project.example.com"
                onChange={(value) =>
                  updateField(
                    "project_url",
                    value,
                  )
                }
              />

              <TextField
                label="GitHub URL"
                type="url"
                value={form.github_url}
                placeholder="https://github.com/..."
                onChange={(value) =>
                  updateField(
                    "github_url",
                    value,
                  )
                }
              />
            </div>

            <TextField
              label="Technologies"
              value={form.technologies}
              placeholder="Python, FastAPI, Next.js, RAG"
              onChange={(value) =>
                updateField(
                  "technologies",
                  value,
                )
              }
            />

            <TextAreaField
              label="Features"
              value={form.features}
              placeholder={
                "Retrieval-augmented answers\nConversation memory\nPDF generation"
              }
              onChange={(value) =>
                updateField(
                  "features",
                  value,
                )
              }
            />

            <TextAreaField
              label="Achievements"
              value={form.achievements}
              placeholder={
                "Built a working full-stack AI application\nIntegrated persistent storage"
              }
              onChange={(value) =>
                updateField(
                  "achievements",
                  value,
                )
              }
            />

            <CheckboxField
              label="I confirm this project information is accurate"
              checked={form.verified}
              onChange={(checked) =>
                updateField(
                  "verified",
                  checked,
                )
              }
            />

            <button
              type="submit"
              disabled={saving}
              className="w-full rounded-xl bg-blue-600 px-6 py-3 font-semibold transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saving
                ? "Saving..."
                : editingId === null
                  ? "Add project"
                  : "Update project"}
            </button>
          </div>
        </form>

        <div className="space-y-5">
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h3 className="text-xl font-semibold">
              Saved projects
            </h3>

            <p className="mt-2 text-sm text-slate-400">
              {records.length}{" "}
              {records.length === 1
                ? "project"
                : "projects"}
            </p>
          </div>

          {loading && (
            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 text-slate-400">
              Loading projects...
            </div>
          )}

          {!loading && records.length === 0 && (
            <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-900/60 p-8 text-center">
              <p className="font-medium">
                No projects added
              </p>

              <p className="mt-2 text-sm text-slate-400">
                Add verified personal, academic,
                freelance, or professional projects.
              </p>
            </div>
          )}

          {!loading &&
            records.map((project) => (
              <article
                key={project.id}
                className="rounded-2xl border border-slate-800 bg-slate-900 p-6"
              >
                <div className="flex flex-col justify-between gap-4 sm:flex-row">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-lg font-semibold">
                        {project.name}
                      </h3>

                      <VerificationBadge
                        verified={project.verified}
                      />
                    </div>

                    {project.role && (
                      <p className="mt-2 font-medium text-blue-300">
                        {project.role}
                      </p>
                    )}

                    {project.project_type && (
                      <p className="mt-1 text-sm text-slate-400">
                        {project.project_type}
                      </p>
                    )}

                    {(project.start_date ||
                      project.end_date ||
                      project.is_current) && (
                      <p className="mt-2 text-sm text-slate-400">
                        {formatDate(
                          project.start_date,
                        )}{" "}
                        —{" "}
                        {project.is_current
                          ? "Present"
                          : formatDate(
                              project.end_date,
                            )}
                      </p>
                    )}
                  </div>

                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() =>
                        beginEditing(project)
                      }
                      className="rounded-lg border border-slate-700 px-3 py-2 text-sm hover:border-slate-500"
                    >
                      Edit
                    </button>

                    <button
                      type="button"
                      disabled={
                        deletingId === project.id
                      }
                      onClick={() =>
                        void handleDelete(project.id)
                      }
                      className="rounded-lg border border-red-900 px-3 py-2 text-sm text-red-300 hover:bg-red-950 disabled:opacity-50"
                    >
                      {deletingId === project.id
                        ? "Deleting..."
                        : "Delete"}
                    </button>
                  </div>
                </div>

                <p className="mt-5 leading-7 text-slate-300">
                  {project.description}
                </p>

                {project.technologies.length >
                  0 && (
                  <div className="mt-5 flex flex-wrap gap-2">
                    {project.technologies.map(
                      (technology) => (
                        <span
                          key={technology}
                          className="rounded-full border border-slate-700 bg-slate-950 px-3 py-1 text-xs text-slate-300"
                        >
                          {technology}
                        </span>
                      ),
                    )}
                  </div>
                )}

                {project.features.length > 0 && (
                  <ProjectList
                    title="Features"
                    values={project.features}
                  />
                )}

                {project.achievements.length >
                  0 && (
                  <ProjectList
                    title="Achievements"
                    values={project.achievements}
                  />
                )}

                {(project.project_url ||
                  project.github_url) && (
                  <div className="mt-5 flex flex-wrap gap-3">
                    {project.project_url && (
                      <a
                        href={project.project_url}
                        target="_blank"
                        rel="noreferrer"
                        className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-blue-300 hover:border-blue-500"
                      >
                        Open project
                      </a>
                    )}

                    {project.github_url && (
                      <a
                        href={project.github_url}
                        target="_blank"
                        rel="noreferrer"
                        className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-blue-300 hover:border-blue-500"
                      >
                        Open GitHub
                      </a>
                    )}
                  </div>
                )}
              </article>
            ))}
        </div>
      </div>
    </section>
  );
}

type TextFieldProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: "text" | "date" | "url";
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
};

function TextField({
  label,
  value,
  onChange,
  type = "text",
  placeholder,
  required = false,
  disabled = false,
}: TextFieldProps) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-medium text-slate-300">
        {label}
      </span>

      <input
        type={type}
        value={value}
        required={required}
        disabled={disabled}
        placeholder={placeholder}
        onChange={(event) =>
          onChange(event.target.value)
        }
        className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition placeholder:text-slate-600 focus:border-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
      />
    </label>
  );
}

type TextAreaFieldProps = {
  label: string;
  value: string;
  placeholder?: string;
  required?: boolean;
  onChange: (value: string) => void;
};

function TextAreaField({
  label,
  value,
  placeholder,
  required = false,
  onChange,
}: TextAreaFieldProps) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-medium text-slate-300">
        {label}
      </span>

      <textarea
        value={value}
        rows={4}
        required={required}
        placeholder={placeholder}
        onChange={(event) =>
          onChange(event.target.value)
        }
        className="w-full resize-y rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition placeholder:text-slate-600 focus:border-blue-500"
      />
    </label>
  );
}

type CheckboxFieldProps = {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
};

function CheckboxField({
  label,
  checked,
  onChange,
}: CheckboxFieldProps) {
  return (
    <label className="flex cursor-pointer items-start gap-3">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) =>
          onChange(event.target.checked)
        }
        className="mt-1 h-4 w-4"
      />

      <span className="text-sm leading-6 text-slate-300">
        {label}
      </span>
    </label>
  );
}

function VerificationBadge({
  verified,
}: {
  verified: boolean;
}) {
  return (
    <span
      className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${
        verified
          ? "border-emerald-800 bg-emerald-950 text-emerald-300"
          : "border-amber-800 bg-amber-950 text-amber-300"
      }`}
    >
      {verified ? "Verified" : "Not verified"}
    </span>
  );
}

function ProjectList({
  title,
  values,
}: {
  title: string;
  values: string[];
}) {
  return (
    <div className="mt-5">
      <p className="text-sm font-semibold text-slate-200">
        {title}
      </p>

      <ul className="mt-2 space-y-2 text-sm leading-6 text-slate-400">
        {values.map((value) => (
          <li
            key={value}
            className="flex gap-2"
          >
            <span>•</span>
            <span>{value}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}