"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import {
  getCandidateProfile,
  saveCandidateProfile,
} from "@/lib/api";

import type {
  CandidateProfile,
  CandidateProfileInput,
} from "@/types/candidate";

type ProfileForm = {
  full_name: string;
  email: string;
  phone: string;
  location: string;
  professional_title: string;
  professional_summary: string;
  linkedin_url: string;
  github_url: string;
  portfolio_url: string;
  work_authorization: string;
  requires_sponsorship: boolean;
  willing_to_relocate: boolean;
  preferred_work_modes: string;
  target_roles: string;
  preferred_locations: string;
  minimum_salary: string;
  salary_currency: string;
  minimum_match_score: string;
  auto_apply_enabled: boolean;
  facts_verified: boolean;
};

const initialForm: ProfileForm = {
  full_name: "",
  email: "",
  phone: "",
  location: "United Kingdom",
  professional_title: "AI & ML Engineer",
  professional_summary: "",
  linkedin_url: "https://www.linkedin.com/in/pavan-alakunta",
  github_url: "https://github.com/Pavan09-Is-Here",
  portfolio_url:
    "https://pavan-portfolio-phi-rouge.vercel.app",
  work_authorization: "",
  requires_sponsorship: false,
  willing_to_relocate: true,
  preferred_work_modes: "Remote, Hybrid",
  target_roles:
    "AI Engineer, Machine Learning Engineer, AI Software Engineer, Data Science Intern",
  preferred_locations: "United Kingdom, London",
  minimum_salary: "35000",
  salary_currency: "GBP",
  minimum_match_score: "85",
  auto_apply_enabled: false,
  facts_verified: false,
};

function optionalValue(value: string): string | null {
  const cleanedValue = value.trim();
  return cleanedValue === "" ? null : cleanedValue;
}

function splitCommaSeparatedValues(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

function candidateToForm(
  candidate: CandidateProfile,
): ProfileForm {
  return {
    full_name: candidate.full_name,
    email: candidate.email,
    phone: candidate.phone ?? "",
    location: candidate.location ?? "",
    professional_title:
      candidate.professional_title ?? "",
    professional_summary:
      candidate.professional_summary ?? "",
    linkedin_url: candidate.linkedin_url ?? "",
    github_url: candidate.github_url ?? "",
    portfolio_url: candidate.portfolio_url ?? "",
    work_authorization:
      candidate.work_authorization ?? "",
    requires_sponsorship:
      candidate.requires_sponsorship,
    willing_to_relocate:
      candidate.willing_to_relocate,
    preferred_work_modes:
      candidate.preferred_work_modes.join(", "),
    target_roles: candidate.target_roles.join(", "),
    preferred_locations:
      candidate.preferred_locations.join(", "),
    minimum_salary:
      candidate.minimum_salary?.toString() ?? "",
    salary_currency: candidate.salary_currency,
    minimum_match_score:
      candidate.minimum_match_score.toString(),
    auto_apply_enabled:
      candidate.auto_apply_enabled,
    facts_verified: candidate.facts_verified,
  };
}

function formToCandidate(
  form: ProfileForm,
): CandidateProfileInput {
  return {
    full_name: form.full_name.trim(),
    email: form.email.trim(),
    phone: optionalValue(form.phone),
    location: optionalValue(form.location),
    professional_title: optionalValue(
      form.professional_title,
    ),
    professional_summary: optionalValue(
      form.professional_summary,
    ),
    linkedin_url: optionalValue(form.linkedin_url),
    github_url: optionalValue(form.github_url),
    portfolio_url: optionalValue(form.portfolio_url),
    work_authorization: optionalValue(
      form.work_authorization,
    ),
    requires_sponsorship: form.requires_sponsorship,
    willing_to_relocate: form.willing_to_relocate,
    preferred_work_modes: splitCommaSeparatedValues(
      form.preferred_work_modes,
    ),
    target_roles: splitCommaSeparatedValues(
      form.target_roles,
    ),
    preferred_locations: splitCommaSeparatedValues(
      form.preferred_locations,
    ),
    minimum_salary:
      form.minimum_salary.trim() === ""
        ? null
        : Number(form.minimum_salary),
    salary_currency:
      form.salary_currency.trim().toUpperCase() ||
      "GBP",
    minimum_match_score: Number(
      form.minimum_match_score,
    ),
    auto_apply_enabled: form.auto_apply_enabled,
    facts_verified: form.facts_verified,
  };
}

export default function CandidateProfilePage() {
  const [form, setForm] =
    useState<ProfileForm>(initialForm);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [successMessage, setSuccessMessage] =
    useState("");
  const [errorMessage, setErrorMessage] =
    useState("");
  const [lastSaved, setLastSaved] =
    useState<string | null>(null);

  useEffect(() => {
    async function loadProfile(): Promise<void> {
      try {
        setLoading(true);
        setErrorMessage("");

        const candidate = await getCandidateProfile();

        if (candidate) {
          setForm(candidateToForm(candidate));
          setLastSaved(candidate.updated_at);
        }
      } catch (error) {
        setErrorMessage(
          error instanceof Error
            ? error.message
            : "Unable to load the candidate profile.",
        );
      } finally {
        setLoading(false);
      }
    }

    void loadProfile();
  }, []);

  function updateField<K extends keyof ProfileForm>(
    field: K,
    value: ProfileForm[K],
  ): void {
    setForm((currentForm) => ({
      ...currentForm,
      [field]: value,
    }));
  }

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    setSuccessMessage("");
    setErrorMessage("");

    if (!form.full_name.trim()) {
      setErrorMessage("Full name is required.");
      return;
    }

    if (!form.email.trim()) {
      setErrorMessage("Email address is required.");
      return;
    }

    const matchScore = Number(
      form.minimum_match_score,
    );

    if (
      Number.isNaN(matchScore) ||
      matchScore < 85 ||
      matchScore > 100
    ) {
      setErrorMessage(
        "Minimum match score must be between 85 and 100.",
      );
      return;
    }

    if (
      form.auto_apply_enabled &&
      !form.facts_verified
    ) {
      setErrorMessage(
        "Verify your profile before enabling automatic applications.",
      );
      return;
    }

    try {
      setSaving(true);

      const savedCandidate =
        await saveCandidateProfile(
          formToCandidate(form),
        );

      setForm(candidateToForm(savedCandidate));
      setLastSaved(savedCandidate.updated_at);
      setSuccessMessage(
        "Candidate profile saved successfully.",
      );
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Unable to save the candidate profile.",
      );
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 text-white">
        <p className="text-slate-300">
          Loading candidate profile...
        </p>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 px-5 py-10 text-white">
      <div className="mx-auto max-w-6xl">
        <header className="mb-8">
          <Link
            href="/"
            className="text-sm font-medium text-blue-400 hover:text-blue-300"
          >
            ← Back to dashboard
          </Link>

          <div className="mt-4 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
            <div>
              <h1 className="text-3xl font-bold sm:text-4xl">
                Candidate Profile
              </h1>

              <p className="mt-3 max-w-3xl leading-7 text-slate-400">
                This information will be used for job
                matching, CV tailoring, salary
                recommendations and applications.
              </p>
            </div>

            <span
              className={`rounded-full border px-4 py-2 text-sm font-semibold ${
                form.facts_verified
                  ? "border-emerald-800 bg-emerald-950 text-emerald-300"
                  : "border-amber-800 bg-amber-950 text-amber-300"
              }`}
            >
              {form.facts_verified
                ? "Profile verified"
                : "Verification required"}
            </span>
          </div>
        </header>

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

        <form
          onSubmit={(event) =>
            void handleSubmit(event)
          }
          className="space-y-8"
        >
          <FormSection
            title="Personal details"
            description="Basic details used in job applications."
          >
            <div className="grid gap-5 md:grid-cols-2">
              <TextInput
                label="Full name"
                value={form.full_name}
                required
                onChange={(value) =>
                  updateField("full_name", value)
                }
              />

              <TextInput
                label="Email address"
                type="email"
                value={form.email}
                required
                onChange={(value) =>
                  updateField("email", value)
                }
              />

              <TextInput
                label="Phone number"
                value={form.phone}
                onChange={(value) =>
                  updateField("phone", value)
                }
              />

              <TextInput
                label="Current location"
                value={form.location}
                onChange={(value) =>
                  updateField("location", value)
                }
              />
            </div>
          </FormSection>

          <FormSection
            title="Professional identity"
            description="Your professional title and summary."
          >
            <div className="space-y-5">
              <TextInput
                label="Professional title"
                value={form.professional_title}
                onChange={(value) =>
                  updateField(
                    "professional_title",
                    value,
                  )
                }
              />

              <TextArea
                label="Professional summary"
                value={form.professional_summary}
                onChange={(value) =>
                  updateField(
                    "professional_summary",
                    value,
                  )
                }
              />
            </div>
          </FormSection>

          <FormSection
            title="Professional links"
            description="Links included in CVs and applications."
          >
            <div className="grid gap-5 md:grid-cols-2">
              <TextInput
                label="LinkedIn URL"
                type="url"
                value={form.linkedin_url}
                onChange={(value) =>
                  updateField("linkedin_url", value)
                }
              />

              <TextInput
                label="GitHub URL"
                type="url"
                value={form.github_url}
                onChange={(value) =>
                  updateField("github_url", value)
                }
              />

              <TextInput
                label="Portfolio URL"
                type="url"
                value={form.portfolio_url}
                onChange={(value) =>
                  updateField("portfolio_url", value)
                }
              />
            </div>
          </FormSection>

          <FormSection
            title="Job preferences"
            description="Separate multiple values using commas."
          >
            <div className="space-y-5">
              <TextArea
                label="Target roles"
                value={form.target_roles}
                onChange={(value) =>
                  updateField("target_roles", value)
                }
              />

              <TextInput
                label="Preferred locations"
                value={form.preferred_locations}
                onChange={(value) =>
                  updateField(
                    "preferred_locations",
                    value,
                  )
                }
              />

              <TextInput
                label="Preferred work modes"
                value={form.preferred_work_modes}
                onChange={(value) =>
                  updateField(
                    "preferred_work_modes",
                    value,
                  )
                }
              />

              <CheckboxInput
                label="I am willing to relocate"
                checked={form.willing_to_relocate}
                onChange={(checked) =>
                  updateField(
                    "willing_to_relocate",
                    checked,
                  )
                }
              />
            </div>
          </FormSection>

          <FormSection
            title="Work authorisation"
            description="This information must always be accurate."
          >
            <div className="space-y-5">
              <TextArea
                label="Work authorisation details"
                value={form.work_authorization}
                onChange={(value) =>
                  updateField(
                    "work_authorization",
                    value,
                  )
                }
              />

              <CheckboxInput
                label="I require employment sponsorship"
                checked={form.requires_sponsorship}
                onChange={(checked) =>
                  updateField(
                    "requires_sponsorship",
                    checked,
                  )
                }
              />
            </div>
          </FormSection>

          <FormSection
            title="Salary and matching"
            description="Rules used to filter jobs and decide automatic applications."
          >
            <div className="grid gap-5 md:grid-cols-3">
              <TextInput
                label="Minimum salary"
                type="number"
                value={form.minimum_salary}
                onChange={(value) =>
                  updateField("minimum_salary", value)
                }
              />

              <TextInput
                label="Salary currency"
                value={form.salary_currency}
                onChange={(value) =>
                  updateField("salary_currency", value)
                }
              />

              <TextInput
                label="Minimum match score"
                type="number"
                min="85"
                max="100"
                value={form.minimum_match_score}
                onChange={(value) =>
                  updateField(
                    "minimum_match_score",
                    value,
                  )
                }
              />
            </div>
          </FormSection>

          <FormSection
            title="Verification and automation"
            description="Automatic applications require verified candidate information."
          >
            <div className="space-y-5">
              <CheckboxInput
                label="I have checked these details and confirm they are accurate"
                checked={form.facts_verified}
                onChange={(checked) => {
                  updateField(
                    "facts_verified",
                    checked,
                  );

                  if (!checked) {
                    updateField(
                      "auto_apply_enabled",
                      false,
                    );
                  }
                }}
              />

              <CheckboxInput
                label="Enable automatic applications for eligible matches"
                checked={form.auto_apply_enabled}
                disabled={!form.facts_verified}
                onChange={(checked) =>
                  updateField(
                    "auto_apply_enabled",
                    checked,
                  )
                }
              />
            </div>
          </FormSection>

          <div className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-slate-900 p-6 sm:flex-row sm:items-center">
            <div>
              <p className="font-medium">
                Candidate facts vault
              </p>

              <p className="mt-1 text-sm text-slate-400">
                {lastSaved
                  ? `Last saved: ${new Date(
                      lastSaved,
                    ).toLocaleString()}`
                  : "The profile has not been saved yet."}
              </p>
            </div>

            <button
              type="submit"
              disabled={saving}
              className="rounded-xl bg-blue-600 px-7 py-3 font-semibold transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saving
                ? "Saving..."
                : "Save profile"}
            </button>
          </div>
        </form>
      </div>
    </main>
  );
}

type FormSectionProps = {
  title: string;
  description: string;
  children: React.ReactNode;
};

function FormSection({
  title,
  description,
  children,
}: FormSectionProps) {
  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
      <h2 className="text-xl font-semibold">{title}</h2>

      <p className="mt-2 mb-6 text-sm leading-6 text-slate-400">
        {description}
      </p>

      {children}
    </section>
  );
}

type TextInputProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: "text" | "email" | "url" | "number";
  required?: boolean;
  min?: string;
  max?: string;
};

function TextInput({
  label,
  value,
  onChange,
  type = "text",
  required = false,
  min,
  max,
}: TextInputProps) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-medium text-slate-300">
        {label}
      </span>

      <input
        type={type}
        value={value}
        required={required}
        min={min}
        max={max}
        onChange={(event) =>
          onChange(event.target.value)
        }
        className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition focus:border-blue-500"
      />
    </label>
  );
}

type TextAreaProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
};

function TextArea({
  label,
  value,
  onChange,
}: TextAreaProps) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-medium text-slate-300">
        {label}
      </span>

      <textarea
        value={value}
        rows={4}
        onChange={(event) =>
          onChange(event.target.value)
        }
        className="w-full resize-y rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition focus:border-blue-500"
      />
    </label>
  );
}

type CheckboxInputProps = {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
};

function CheckboxInput({
  label,
  checked,
  onChange,
  disabled = false,
}: CheckboxInputProps) {
  return (
    <label
      className={`flex items-start gap-3 ${
        disabled ? "opacity-50" : ""
      }`}
    >
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
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