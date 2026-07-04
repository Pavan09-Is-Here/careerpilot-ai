"use client";

import {
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from "react";

import {
  createSkill,
  deleteSkill,
  getSkillRecords,
  updateSkill,
} from "@/lib/api";

import type {
  Skill,
  SkillInput,
  SkillProficiency,
} from "@/types/skill";

type SkillFormState = {
  name: string;
  category: string;
  proficiency: SkillProficiency;
  years_experience: string;
  evidence: string;
  is_primary: boolean;
  verified: boolean;
};

const emptySkillForm: SkillFormState = {
  name: "",
  category: "",
  proficiency: "Intermediate",
  years_experience: "",
  evidence: "",
  is_primary: false,
  verified: false,
};

const proficiencyOptions: SkillProficiency[] = [
  "Beginner",
  "Intermediate",
  "Advanced",
  "Expert",
];

const categoryOptions = [
  "Programming Language",
  "Framework",
  "Machine Learning",
  "Artificial Intelligence",
  "Database",
  "Cloud",
  "DevOps",
  "Data Analysis",
  "Frontend",
  "Backend",
  "Soft Skill",
  "Tool",
  "Other",
];

function optionalText(value: string): string | null {
  const cleanedValue = value.trim();

  return cleanedValue || null;
}

function formToPayload(
  form: SkillFormState,
): SkillInput {
  return {
    name: form.name.trim(),
    category: optionalText(form.category),
    proficiency: form.proficiency,

    years_experience:
      form.years_experience.trim() === ""
        ? null
        : Number(form.years_experience),

    evidence: optionalText(form.evidence),
    is_primary: form.is_primary,
    verified: form.verified,
  };
}

function skillToForm(
  skill: Skill,
): SkillFormState {
  return {
    name: skill.name,
    category: skill.category ?? "",
    proficiency: skill.proficiency,
    years_experience:
      skill.years_experience?.toString() ?? "",
    evidence: skill.evidence ?? "",
    is_primary: skill.is_primary,
    verified: skill.verified,
  };
}

export default function SkillManager() {
  const [records, setRecords] = useState<Skill[]>(
    [],
  );

  const [form, setForm] =
    useState<SkillFormState>(emptySkillForm);

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

  const groupedSkills = useMemo(() => {
    const groups = new Map<string, Skill[]>();

    for (const skill of records) {
      const category =
        skill.category ?? "Uncategorised";

      const categorySkills =
        groups.get(category) ?? [];

      categorySkills.push(skill);
      groups.set(category, categorySkills);
    }

    return Array.from(groups.entries()).sort(
      ([categoryA], [categoryB]) =>
        categoryA.localeCompare(categoryB),
    );
  }, [records]);

  useEffect(() => {
    void loadSkills();
  }, []);

  async function loadSkills(): Promise<void> {
    try {
      setLoading(true);
      setErrorMessage("");

      const skillRecords =
        await getSkillRecords();

      setRecords(skillRecords);
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Unable to load skills.",
      );
    } finally {
      setLoading(false);
    }
  }

  function updateField<
    K extends keyof SkillFormState,
  >(
    field: K,
    value: SkillFormState[K],
  ): void {
    setForm((currentForm) => ({
      ...currentForm,
      [field]: value,
    }));
  }

  function resetForm(): void {
    setForm(emptySkillForm);
    setEditingId(null);
  }

  function beginEditing(skill: Skill): void {
    setForm(skillToForm(skill));
    setEditingId(skill.id);
    setSuccessMessage("");
    setErrorMessage("");

    document
      .getElementById("skill-form")
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
        "Skill name is required.",
      );
      return;
    }

    const yearsExperience =
      form.years_experience.trim() === ""
        ? null
        : Number(form.years_experience);

    if (
      yearsExperience !== null &&
      (
        Number.isNaN(yearsExperience) ||
        yearsExperience < 0 ||
        yearsExperience > 50
      )
    ) {
      setErrorMessage(
        "Years of experience must be between 0 and 50.",
      );
      return;
    }

    try {
      setSaving(true);

      if (editingId === null) {
        await createSkill(
          formToPayload(form),
        );

        setSuccessMessage(
          "Skill added successfully.",
        );
      } else {
        await updateSkill(
          editingId,
          formToPayload(form),
        );

        setSuccessMessage(
          "Skill updated successfully.",
        );
      }

      resetForm();
      await loadSkills();
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Unable to save skill.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(
    skillId: number,
  ): Promise<void> {
    const confirmed = window.confirm(
      "Delete this skill?",
    );

    if (!confirmed) {
      return;
    }

    try {
      setDeletingId(skillId);
      setSuccessMessage("");
      setErrorMessage("");

      await deleteSkill(skillId);

      if (editingId === skillId) {
        resetForm();
      }

      setSuccessMessage(
        "Skill deleted successfully.",
      );

      await loadSkills();
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Unable to delete skill.",
      );
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <section className="mt-12">
      <div className="mb-6">
        <p className="cp-eyebrow">
          Verified facts vault
        </p>

        <h2 className="mt-3 text-3xl font-bold text-slate-900">
          Skills
        </h2>

        <p className="mt-3 max-w-3xl leading-7 text-slate-500">
          Add genuine skills with evidence from your
          education, experience, and projects.
        </p>
      </div>

      {successMessage && (
        <div className="mb-6 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-emerald-700">
          {successMessage}
        </div>
      )}

      {errorMessage && (
        <div className="mb-6 rounded-xl border border-red-200 bg-red-50 p-4 text-red-700">
          {errorMessage}
        </div>
      )}

      <div className="grid gap-8 xl:grid-cols-[1.05fr_0.95fr]">
        <form
          id="skill-form"
          onSubmit={(event) =>
            void handleSubmit(event)
          }
          className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
        >
          <div className="mb-6 flex items-center justify-between gap-4">
            <div>
              <h3 className="text-xl font-semibold">
                {editingId === null
                  ? "Add skill"
                  : "Edit skill"}
              </h3>

              <p className="mt-2 text-sm text-slate-500">
                Add evidence showing where you used
                this skill.
              </p>
            </div>

            {editingId !== null && (
              <button
                type="button"
                onClick={resetForm}
                className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-600 transition hover:border-violet-400 hover:text-violet-700"
              >
                Cancel editing
              </button>
            )}
          </div>

          <div className="space-y-5">
            <TextField
              label="Skill name *"
              value={form.name}
              required
              placeholder="Python"
              onChange={(value) =>
                updateField("name", value)
              }
            />

            <SelectField
              label="Category"
              value={form.category}
              options={categoryOptions}
              emptyLabel="Select category"
              onChange={(value) =>
                updateField("category", value)
              }
            />

            <SelectField
              label="Proficiency"
              value={form.proficiency}
              options={proficiencyOptions}
              onChange={(value) =>
                updateField(
                  "proficiency",
                  value as SkillProficiency,
                )
              }
            />

            <TextField
              label="Years of experience"
              type="number"
              value={form.years_experience}
              placeholder="2"
              min="0"
              max="50"
              step="0.5"
              onChange={(value) =>
                updateField(
                  "years_experience",
                  value,
                )
              }
            />

            <TextAreaField
              label="Evidence"
              value={form.evidence}
              placeholder="Explain where and how you used this skill, such as projects, employment, coursework, or certifications."
              onChange={(value) =>
                updateField("evidence", value)
              }
            />

            <CheckboxField
              label="This is one of my primary skills"
              checked={form.is_primary}
              onChange={(checked) =>
                updateField(
                  "is_primary",
                  checked,
                )
              }
            />

            <CheckboxField
              label="I confirm that I genuinely possess this skill"
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
              className="w-full rounded-xl bg-violet-600 px-6 py-3 font-semibold text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saving
                ? "Saving..."
                : editingId === null
                  ? "Add skill"
                  : "Update skill"}
            </button>
          </div>
        </form>

        <div className="space-y-5">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-xl font-semibold">
              Saved skills
            </h3>

            <p className="mt-2 text-sm text-slate-500">
              {records.length}{" "}
              {records.length === 1
                ? "skill"
                : "skills"}
            </p>

            <div className="mt-5 grid grid-cols-3 gap-3">
              <Statistic
                label="Primary"
                value={
                  records.filter(
                    (skill) => skill.is_primary,
                  ).length
                }
              />

              <Statistic
                label="Verified"
                value={
                  records.filter(
                    (skill) => skill.verified,
                  ).length
                }
              />

              <Statistic
                label="Categories"
                value={groupedSkills.length}
              />
            </div>
          </div>

          {loading && (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 text-slate-500 shadow-sm">
              Loading skills...
            </div>
          )}

          {!loading && records.length === 0 && (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center">
              <p className="font-medium text-slate-900">
                No skills added
              </p>

              <p className="mt-2 text-sm text-slate-500">
                Add your verified programming,
                technical, AI, and professional skills.
              </p>
            </div>
          )}

          {!loading &&
            groupedSkills.map(
              ([category, skills]) => (
                <section
                  key={category}
                  className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
                >
                  <h3 className="font-semibold text-slate-800">
                    {category}
                  </h3>

                  <div className="mt-4 space-y-4">
                    {skills.map((skill) => (
                      <article
                        key={skill.id}
                        className="rounded-xl border border-slate-200 bg-white p-4"
                      >
                        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
                          <div>
                            <div className="flex flex-wrap items-center gap-2">
                              <h4 className="font-semibold">
                                {skill.name}
                              </h4>

                              {skill.is_primary && (
                                <span className="rounded-full border border-violet-200 bg-violet-50 px-2.5 py-1 text-xs font-semibold text-violet-700">
                                  Primary
                                </span>
                              )}

                              <VerificationBadge
                                verified={
                                  skill.verified
                                }
                              />
                            </div>

                            <p className="mt-2 text-sm text-slate-500">
                              {skill.proficiency}
                              {skill.years_experience !==
                                null &&
                                ` · ${skill.years_experience} years`}
                            </p>
                          </div>

                          <div className="flex gap-2">
                            <button
                              type="button"
                              onClick={() =>
                                beginEditing(skill)
                              }
                              className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 transition hover:border-violet-400 hover:text-violet-700"
                            >
                              Edit
                            </button>

                            <button
                              type="button"
                              disabled={
                                deletingId ===
                                skill.id
                              }
                              onClick={() =>
                                void handleDelete(
                                  skill.id,
                                )
                              }
                              className="rounded-lg border border-red-200 px-3 py-2 text-sm text-red-700 transition hover:bg-red-50 disabled:opacity-50"
                            >
                              {deletingId ===
                              skill.id
                                ? "Deleting..."
                                : "Delete"}
                            </button>
                          </div>
                        </div>

                        {skill.evidence && (
                          <p className="mt-4 text-sm leading-6 text-slate-600">
                            {skill.evidence}
                          </p>
                        )}
                      </article>
                    ))}
                  </div>
                </section>
              ),
            )}
        </div>
      </div>
    </section>
  );
}

type TextFieldProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: "text" | "number";
  placeholder?: string;
  required?: boolean;
  min?: string;
  max?: string;
  step?: string;
};

function TextField({
  label,
  value,
  onChange,
  type = "text",
  placeholder,
  required = false,
  min,
  max,
  step,
}: TextFieldProps) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-medium text-slate-700">
        {label}
      </span>

      <input
        type={type}
        value={value}
        required={required}
        min={min}
        max={max}
        step={step}
        placeholder={placeholder}
        onChange={(event) =>
          onChange(event.target.value)
        }
        className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-violet-500 focus:ring-2 focus:ring-violet-200"
      />
    </label>
  );
}

type SelectFieldProps = {
  label: string;
  value: string;
  options: readonly string[];
  onChange: (value: string) => void;
  emptyLabel?: string;
};

function SelectField({
  label,
  value,
  options,
  onChange,
  emptyLabel,
}: SelectFieldProps) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-medium text-slate-700">
        {label}
      </span>

      <select
        value={value}
        onChange={(event) =>
          onChange(event.target.value)
        }
        className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-900 outline-none transition focus:border-violet-500 focus:ring-2 focus:ring-violet-200"
      >
        {emptyLabel && (
          <option value="">
            {emptyLabel}
          </option>
        )}

        {options.map((option) => (
          <option
            key={option}
            value={option}
          >
            {option}
          </option>
        ))}
      </select>
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
      <span className="mb-2 block text-sm font-medium text-slate-700">
        {label}
      </span>

      <textarea
        value={value}
        rows={5}
        placeholder={placeholder}
        onChange={(event) =>
          onChange(event.target.value)
        }
        className="w-full resize-y rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-violet-500 focus:ring-2 focus:ring-violet-200"
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

      <span className="text-sm leading-6 text-slate-600">
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
          ? "border-emerald-200 bg-emerald-50 text-emerald-700"
          : "border-amber-200 bg-amber-50 text-amber-700"
      }`}
    >
      {verified ? "Verified" : "Not verified"}
    </span>
  );
}

function Statistic({
  label,
  value,
}: {
  label: string;
  value: number;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-center">
      <p className="text-xl font-bold">
        {value}
      </p>

      <p className="mt-1 text-xs text-slate-500">
        {label}
      </p>
    </div>
  );
}