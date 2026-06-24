"use client";

import {
  useEffect,
  useState,
  type FormEvent,
} from "react";

import {
  createExperience,
  deleteExperience,
  getExperienceRecords,
  updateExperience,
} from "@/lib/api";

import type {
  Experience,
  ExperienceInput,
} from "@/types/experience";

type ExperienceFormState = {
  company: string;
  job_title: string;
  employment_type: string;
  location: string;
  start_date: string;
  end_date: string;
  is_current: boolean;
  description: string;
  responsibilities: string;
  achievements: string;
  technologies: string;
  verified: boolean;
};

const emptyForm: ExperienceFormState = {
  company: "",
  job_title: "",
  employment_type: "",
  location: "",
  start_date: "",
  end_date: "",
  is_current: false,
  description: "",
  responsibilities: "",
  achievements: "",
  technologies: "",
  verified: false,
};

function optionalText(value: string): string | null {
  const cleanedValue = value.trim();
  return cleanedValue || null;
}

function splitCommaValues(value: string): string[] {
  const values = value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

  return Array.from(new Set(values));
}

function splitLineValues(value: string): string[] {
  const values = value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);

  return Array.from(new Set(values));
}

function formToPayload(
  form: ExperienceFormState,
): ExperienceInput {
  return {
    company: form.company.trim(),
    job_title: form.job_title.trim(),
    employment_type: optionalText(
      form.employment_type,
    ),
    location: optionalText(form.location),
    start_date: form.start_date,
    end_date:
      form.is_current || !form.end_date
        ? null
        : form.end_date,
    is_current: form.is_current,
    description: optionalText(form.description),
    responsibilities: splitLineValues(
      form.responsibilities,
    ),
    achievements: splitLineValues(
      form.achievements,
    ),
    technologies: splitCommaValues(
      form.technologies,
    ),
    verified: form.verified,
  };
}

function recordToForm(
  experience: Experience,
): ExperienceFormState {
  return {
    company: experience.company,
    job_title: experience.job_title,
    employment_type:
      experience.employment_type ?? "",
    location: experience.location ?? "",
    start_date: experience.start_date,
    end_date: experience.end_date ?? "",
    is_current: experience.is_current,
    description: experience.description ?? "",
    responsibilities:
      experience.responsibilities.join("\n"),
    achievements:
      experience.achievements.join("\n"),
    technologies:
      experience.technologies.join(", "),
    verified: experience.verified,
  };
}

function formatDate(value: string | null): string {
  if (!value) {
    return "Present";
  }

  const date = new Date(`${value}T00:00:00`);

  return date.toLocaleDateString(undefined, {
    month: "short",
    year: "numeric",
  });
}

export default function ExperienceManager() {
  const [records, setRecords] = useState<
    Experience[]
  >([]);

  const [form, setForm] =
    useState<ExperienceFormState>(emptyForm);

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
    void loadRecords();
  }, []);

  async function loadRecords(): Promise<void> {
    try {
      setLoading(true);
      setErrorMessage("");

      const experienceRecords =
        await getExperienceRecords();

      setRecords(experienceRecords);
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Unable to load work experience.",
      );
    } finally {
      setLoading(false);
    }
  }

  function updateField<
    K extends keyof ExperienceFormState,
  >(
    field: K,
    value: ExperienceFormState[K],
  ): void {
    setForm((currentForm) => ({
      ...currentForm,
      [field]: value,
    }));
  }

  function resetForm(): void {
    setForm(emptyForm);
    setEditingId(null);
  }

  function beginEditing(
    experience: Experience,
  ): void {
    setForm(recordToForm(experience));
    setEditingId(experience.id);
    setSuccessMessage("");
    setErrorMessage("");

    document
      .getElementById("experience-form")
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

    if (!form.company.trim()) {
      setErrorMessage("Company name is required.");
      return;
    }

    if (!form.job_title.trim()) {
      setErrorMessage("Job title is required.");
      return;
    }

    if (!form.start_date) {
      setErrorMessage("Start date is required.");
      return;
    }

    if (
      !form.is_current &&
      form.end_date &&
      form.end_date < form.start_date
    ) {
      setErrorMessage(
        "End date cannot be before start date.",
      );
      return;
    }

    try {
      setSaving(true);

      if (editingId === null) {
        await createExperience(
          formToPayload(form),
        );

        setSuccessMessage(
          "Work experience added successfully.",
        );
      } else {
        await updateExperience(
          editingId,
          formToPayload(form),
        );

        setSuccessMessage(
          "Work experience updated successfully.",
        );
      }

      resetForm();
      await loadRecords();
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Unable to save work experience.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(
    experienceId: number,
  ): Promise<void> {
    const confirmed = window.confirm(
      "Delete this work experience record?",
    );

    if (!confirmed) {
      return;
    }

    try {
      setDeletingId(experienceId);
      setSuccessMessage("");
      setErrorMessage("");

      await deleteExperience(experienceId);

      if (editingId === experienceId) {
        resetForm();
      }

      setSuccessMessage(
        "Work experience deleted successfully.",
      );

      await loadRecords();
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Unable to delete work experience.",
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
          Work Experience
        </h2>

        <p className="mt-3 max-w-3xl leading-7 text-slate-400">
          Add only genuine employment, internships,
          freelance work and professional experience.
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
          id="experience-form"
          onSubmit={(event) =>
            void handleSubmit(event)
          }
          className="rounded-2xl border border-slate-800 bg-slate-900 p-6"
        >
          <div className="mb-6 flex items-center justify-between gap-4">
            <div>
              <h3 className="text-xl font-semibold">
                {editingId === null
                  ? "Add work experience"
                  : "Edit work experience"}
              </h3>

              <p className="mt-2 text-sm text-slate-400">
                Enter one responsibility or achievement
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
              label="Company *"
              value={form.company}
              required
              placeholder="Company name"
              onChange={(value) =>
                updateField("company", value)
              }
            />

            <TextField
              label="Job title *"
              value={form.job_title}
              required
              placeholder="AI Data Specialist"
              onChange={(value) =>
                updateField("job_title", value)
              }
            />

            <div className="grid gap-5 md:grid-cols-2">
              <TextField
                label="Employment type"
                value={form.employment_type}
                placeholder="Full-time, Internship"
                onChange={(value) =>
                  updateField(
                    "employment_type",
                    value,
                  )
                }
              />

              <TextField
                label="Location"
                value={form.location}
                placeholder="London, United Kingdom"
                onChange={(value) =>
                  updateField("location", value)
                }
              />
            </div>

            <div className="grid gap-5 md:grid-cols-2">
              <TextField
                label="Start date *"
                type="date"
                value={form.start_date}
                required
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
              label="I currently work here"
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

            <TextAreaField
              label="Professional description"
              value={form.description}
              placeholder="Brief overview of your role."
              onChange={(value) =>
                updateField("description", value)
              }
            />

            <TextAreaField
              label="Responsibilities"
              value={form.responsibilities}
              placeholder={
                "Managed AI training data\nReviewed technical outputs"
              }
              onChange={(value) =>
                updateField(
                  "responsibilities",
                  value,
                )
              }
            />

            <TextAreaField
              label="Achievements"
              value={form.achievements}
              placeholder={
                "Improved output quality\nLed a team of 35 annotators"
              }
              onChange={(value) =>
                updateField(
                  "achievements",
                  value,
                )
              }
            />

            <TextField
              label="Technologies"
              value={form.technologies}
              placeholder="Python, SQL, Machine Learning"
              onChange={(value) =>
                updateField(
                  "technologies",
                  value,
                )
              }
            />

            <CheckboxField
              label="I confirm this work experience is accurate"
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
                  ? "Add work experience"
                  : "Update work experience"}
            </button>
          </div>
        </form>

        <div className="space-y-5">
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h3 className="text-xl font-semibold">
              Saved experience
            </h3>

            <p className="mt-2 text-sm text-slate-400">
              {records.length} experience{" "}
              {records.length === 1
                ? "record"
                : "records"}
            </p>
          </div>

          {loading && (
            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 text-slate-400">
              Loading experience records...
            </div>
          )}

          {!loading && records.length === 0 && (
            <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-900/60 p-8 text-center">
              <p className="font-medium">
                No work experience added
              </p>

              <p className="mt-2 text-sm text-slate-400">
                Add employment, internships or
                verified freelance experience.
              </p>
            </div>
          )}

          {!loading &&
            records.map((experience) => (
              <article
                key={experience.id}
                className="rounded-2xl border border-slate-800 bg-slate-900 p-6"
              >
                <div className="flex flex-col justify-between gap-4 sm:flex-row">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-lg font-semibold">
                        {experience.job_title}
                      </h3>

                      <VerificationBadge
                        verified={
                          experience.verified
                        }
                      />
                    </div>

                    <p className="mt-2 font-medium text-blue-300">
                      {experience.company}
                    </p>

                    <p className="mt-2 text-sm text-slate-400">
                      {formatDate(
                        experience.start_date,
                      )}{" "}
                      —{" "}
                      {experience.is_current
                        ? "Present"
                        : formatDate(
                            experience.end_date,
                          )}
                    </p>

                    {experience.location && (
                      <p className="mt-1 text-sm text-slate-400">
                        {experience.location}
                      </p>
                    )}
                  </div>

                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() =>
                        beginEditing(experience)
                      }
                      className="rounded-lg border border-slate-700 px-3 py-2 text-sm hover:border-slate-500"
                    >
                      Edit
                    </button>

                    <button
                      type="button"
                      disabled={
                        deletingId === experience.id
                      }
                      onClick={() =>
                        void handleDelete(
                          experience.id,
                        )
                      }
                      className="rounded-lg border border-red-900 px-3 py-2 text-sm text-red-300 hover:bg-red-950 disabled:opacity-50"
                    >
                      {deletingId === experience.id
                        ? "Deleting..."
                        : "Delete"}
                    </button>
                  </div>
                </div>

                {experience.description && (
                  <p className="mt-5 leading-6 text-slate-300">
                    {experience.description}
                  </p>
                )}

                {experience.responsibilities.length >
                  0 && (
                  <RecordList
                    title="Responsibilities"
                    values={
                      experience.responsibilities
                    }
                  />
                )}

                {experience.achievements.length >
                  0 && (
                  <RecordList
                    title="Achievements"
                    values={
                      experience.achievements
                    }
                  />
                )}

                {experience.technologies.length >
                  0 && (
                  <div className="mt-5 flex flex-wrap gap-2">
                    {experience.technologies.map(
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
  type?: "text" | "date";
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
        className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition placeholder:text-slate-600 focus:border-blue-500 disabled:opacity-50"
      />
    </label>
  );
}

type TextAreaFieldProps = {
  label: string;
  value: string;
  placeholder?: string;
  onChange: (value: string) => void;
};

function TextAreaField({
  label,
  value,
  placeholder,
  onChange,
}: TextAreaFieldProps) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-medium text-slate-300">
        {label}
      </span>

      <textarea
        rows={4}
        value={value}
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

function RecordList({
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