"use client";

import {
  useEffect,
  useState,
  type FormEvent,
} from "react";

import {
  createEducation,
  deleteEducation,
  getEducationRecords,
  updateEducation,
} from "@/lib/api";

import type {
  Education,
  EducationInput,
} from "@/types/education";

type EducationFormState = {
  institution: string;
  degree: string;
  field_of_study: string;
  start_date: string;
  end_date: string;
  grade: string;
  location: string;
  description: string;
  is_current: boolean;
  verified: boolean;
};

const emptyEducationForm: EducationFormState = {
  institution: "",
  degree: "",
  field_of_study: "",
  start_date: "",
  end_date: "",
  grade: "",
  location: "",
  description: "",
  is_current: false,
  verified: false,
};

function optionalText(value: string): string | null {
  const cleanedValue = value.trim();
  return cleanedValue || null;
}

function formToPayload(
  form: EducationFormState,
): EducationInput {
  return {
    institution: form.institution.trim(),
    degree: form.degree.trim(),
    field_of_study: optionalText(
      form.field_of_study,
    ),
    start_date: form.start_date,
    end_date:
      form.is_current || !form.end_date
        ? null
        : form.end_date,
    grade: optionalText(form.grade),
    location: optionalText(form.location),
    description: optionalText(form.description),
    is_current: form.is_current,
    verified: form.verified,
  };
}

function educationToForm(
  education: Education,
): EducationFormState {
  return {
    institution: education.institution,
    degree: education.degree,
    field_of_study:
      education.field_of_study ?? "",
    start_date: education.start_date,
    end_date: education.end_date ?? "",
    grade: education.grade ?? "",
    location: education.location ?? "",
    description: education.description ?? "",
    is_current: education.is_current,
    verified: education.verified,
  };
}

function formatDate(value: string | null): string {
  if (!value) {
    return "Present";
  }

  const date = new Date(`${value}T00:00:00`);

  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
  });
}

export default function EducationManager() {
  const [records, setRecords] = useState<Education[]>(
    [],
  );

  const [form, setForm] =
    useState<EducationFormState>(
      emptyEducationForm,
    );

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
    void loadEducation();
  }, []);

  async function loadEducation(): Promise<void> {
    try {
      setLoading(true);
      setErrorMessage("");

      const educationRecords =
        await getEducationRecords();

      setRecords(educationRecords);
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Unable to load education records.",
      );
    } finally {
      setLoading(false);
    }
  }

  function updateField<
    K extends keyof EducationFormState,
  >(
    field: K,
    value: EducationFormState[K],
  ): void {
    setForm((currentForm) => ({
      ...currentForm,
      [field]: value,
    }));
  }

  function resetForm(): void {
    setForm(emptyEducationForm);
    setEditingId(null);
  }

  function beginEditing(
    education: Education,
  ): void {
    setForm(educationToForm(education));
    setEditingId(education.id);
    setSuccessMessage("");
    setErrorMessage("");

    document
      .getElementById("education-form")
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

    if (!form.institution.trim()) {
      setErrorMessage(
        "Institution name is required.",
      );
      return;
    }

    if (!form.degree.trim()) {
      setErrorMessage("Degree is required.");
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
        await createEducation(
          formToPayload(form),
        );

        setSuccessMessage(
          "Education record added successfully.",
        );
      } else {
        await updateEducation(
          editingId,
          formToPayload(form),
        );

        setSuccessMessage(
          "Education record updated successfully.",
        );
      }

      resetForm();
      await loadEducation();
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Unable to save education record.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(
    educationId: number,
  ): Promise<void> {
    const confirmed = window.confirm(
      "Delete this education record?",
    );

    if (!confirmed) {
      return;
    }

    try {
      setDeletingId(educationId);
      setSuccessMessage("");
      setErrorMessage("");

      await deleteEducation(educationId);

      if (editingId === educationId) {
        resetForm();
      }

      setSuccessMessage(
        "Education record deleted successfully.",
      );

      await loadEducation();
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Unable to delete education record.",
      );
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <section className="mt-10">
      <div className="mb-6">
        <p className="text-sm font-semibold uppercase tracking-[0.25em] text-blue-400">
          Verified facts vault
        </p>

        <h2 className="mt-3 text-3xl font-bold">
          Education
        </h2>

        <p className="mt-3 max-w-3xl leading-7 text-slate-400">
          Add your education exactly as it should
          appear in CVs and application forms.
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
          id="education-form"
          onSubmit={(event) =>
            void handleSubmit(event)
          }
          className="rounded-2xl border border-slate-800 bg-slate-900 p-6"
        >
          <div className="mb-6 flex items-center justify-between gap-4">
            <div>
              <h3 className="text-xl font-semibold">
                {editingId === null
                  ? "Add education"
                  : "Edit education"}
              </h3>

              <p className="mt-2 text-sm text-slate-400">
                Fields marked with an asterisk are
                required.
              </p>
            </div>

            {editingId !== null && (
              <button
                type="button"
                onClick={resetForm}
                className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-medium text-slate-300 hover:border-slate-500"
              >
                Cancel editing
              </button>
            )}
          </div>

          <div className="space-y-5">
            <TextField
              label="Institution *"
              value={form.institution}
              placeholder="University or college name"
              required
              onChange={(value) =>
                updateField(
                  "institution",
                  value,
                )
              }
            />

            <TextField
              label="Degree *"
              value={form.degree}
              placeholder="Master of Science"
              required
              onChange={(value) =>
                updateField("degree", value)
              }
            />

            <TextField
              label="Field of study"
              value={form.field_of_study}
              placeholder="Artificial Intelligence"
              onChange={(value) =>
                updateField(
                  "field_of_study",
                  value,
                )
              }
            />

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
              label="I am currently studying here"
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
                label="Grade"
                value={form.grade}
                placeholder="Distinction, First Class or GPA"
                onChange={(value) =>
                  updateField("grade", value)
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

            <TextAreaField
              label="Description"
              value={form.description}
              placeholder="Relevant modules, achievements, dissertation or coursework."
              onChange={(value) =>
                updateField(
                  "description",
                  value,
                )
              }
            />

            <CheckboxField
              label="I confirm this education information is accurate"
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
                  ? "Add education"
                  : "Update education"}
            </button>
          </div>
        </form>

        <div className="space-y-5">
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h3 className="text-xl font-semibold">
              Saved education
            </h3>

            <p className="mt-2 text-sm text-slate-400">
              {records.length} education{" "}
              {records.length === 1
                ? "record"
                : "records"}
            </p>
          </div>

          {loading && (
            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 text-slate-400">
              Loading education records...
            </div>
          )}

          {!loading && records.length === 0 && (
            <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-900/60 p-8 text-center">
              <p className="font-medium">
                No education added yet
              </p>

              <p className="mt-2 text-sm text-slate-400">
                Add your university, college or
                relevant qualification.
              </p>
            </div>
          )}

          {!loading &&
            records.map((education) => (
              <article
                key={education.id}
                className="rounded-2xl border border-slate-800 bg-slate-900 p-6"
              >
                <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-lg font-semibold">
                        {education.degree}
                      </h3>

                      <VerificationBadge
                        verified={
                          education.verified
                        }
                      />
                    </div>

                    <p className="mt-2 font-medium text-blue-300">
                      {education.institution}
                    </p>

                    {education.field_of_study && (
                      <p className="mt-1 text-sm text-slate-300">
                        {
                          education.field_of_study
                        }
                      </p>
                    )}
                  </div>

                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() =>
                        beginEditing(education)
                      }
                      className="rounded-lg border border-slate-700 px-3 py-2 text-sm font-medium hover:border-slate-500"
                    >
                      Edit
                    </button>

                    <button
                      type="button"
                      disabled={
                        deletingId === education.id
                      }
                      onClick={() =>
                        void handleDelete(
                          education.id,
                        )
                      }
                      className="rounded-lg border border-red-900 px-3 py-2 text-sm font-medium text-red-300 hover:bg-red-950 disabled:opacity-50"
                    >
                      {deletingId === education.id
                        ? "Deleting..."
                        : "Delete"}
                    </button>
                  </div>
                </div>

                <div className="mt-5 grid gap-3 text-sm text-slate-400">
                  <p>
                    {formatDate(
                      education.start_date,
                    )}{" "}
                    —{" "}
                    {education.is_current
                      ? "Present"
                      : formatDate(
                          education.end_date,
                        )}
                  </p>

                  {education.location && (
                    <p>{education.location}</p>
                  )}

                  {education.grade && (
                    <p>
                      Grade: {education.grade}
                    </p>
                  )}

                  {education.description && (
                    <p className="leading-6 text-slate-300">
                      {education.description}
                    </p>
                  )}
                </div>
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
        className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition placeholder:text-slate-600 focus:border-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
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
        value={value}
        rows={4}
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
    <label className="flex items-start gap-3">
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