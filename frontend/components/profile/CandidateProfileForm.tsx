"use client";

import Link from "next/link";
import {
  useEffect,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";

import EducationManager from "@/components/profile/EducationManager";
import ExperienceManager from "@/components/profile/ExperienceManager";
import ProjectManager from "@/components/profile/ProjectManager";
import SkillManager from "@/components/profile/SkillManager";
import CertificationManager from "@/components/profile/CertificationManager";
import CountryMultiSelect from "@/components/profile/CountryMultiSelect";
import WorkModeSelector from "@/components/profile/WorkModeSelector";

import {
  getCandidateProfile,
  saveCandidateProfile,
  verifyAllProfileFacts,
} from "@/lib/api";

import type {
  CandidateProfile,
  CandidateProfileInput,
} from "@/types/candidate";

type ProfileFormState = {
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

type ProfileTab =
  | "profile"
  | "education"
  | "experience"
  | "projects"
  | "skills"
  | "certifications";

const PROFILE_TABS: { id: ProfileTab; label: string }[] = [
  { id: "profile", label: "Profile details" },
  { id: "education", label: "Education" },
  { id: "experience", label: "Work experience" },
  { id: "projects", label: "Projects" },
  { id: "skills", label: "Skills" },
  { id: "certifications", label: "Certifications" },
];

const initialForm: ProfileFormState = {
  full_name: "",
  email: "",
  phone: "",
  location: "",
  professional_title: "",
  professional_summary: "",
  linkedin_url: "",
  github_url: "",
  portfolio_url: "",
  work_authorization: "",
  requires_sponsorship: false,
  willing_to_relocate: false,
  preferred_work_modes: "",
  target_roles: "",
  preferred_locations: "",
  minimum_salary: "",
  salary_currency: "GBP",
  minimum_match_score: "85",
  auto_apply_enabled: false,
  facts_verified: false,
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

function profileToForm(
  profile: CandidateProfile,
): ProfileFormState {
  return {
    full_name: profile.full_name,
    email: profile.email,
    phone: profile.phone ?? "",
    location: profile.location ?? "",
    professional_title:
      profile.professional_title ?? "",
    professional_summary:
      profile.professional_summary ?? "",
    linkedin_url: profile.linkedin_url ?? "",
    github_url: profile.github_url ?? "",
    portfolio_url: profile.portfolio_url ?? "",
    work_authorization:
      profile.work_authorization ?? "",
    requires_sponsorship:
      profile.requires_sponsorship,
    willing_to_relocate:
      profile.willing_to_relocate,
    preferred_work_modes:
      profile.preferred_work_modes.join(", "),
    target_roles: profile.target_roles.join(", "),
    preferred_locations:
      profile.preferred_locations.join(", "),
    minimum_salary:
      profile.minimum_salary?.toString() ?? "",
    salary_currency: profile.salary_currency,
    minimum_match_score:
      profile.minimum_match_score.toString(),
    auto_apply_enabled:
      profile.auto_apply_enabled,
    facts_verified: profile.facts_verified,
  };
}

function formToPayload(
  form: ProfileFormState,
): CandidateProfileInput {
  return {
    full_name: form.full_name.trim(),
    email: form.email.trim(),
    phone: optionalText(form.phone),
    location: optionalText(form.location),

    professional_title: optionalText(
      form.professional_title,
    ),

    professional_summary: optionalText(
      form.professional_summary,
    ),

    linkedin_url: optionalText(
      form.linkedin_url,
    ),

    github_url: optionalText(
      form.github_url,
    ),

    portfolio_url: optionalText(
      form.portfolio_url,
    ),

    work_authorization: optionalText(
      form.work_authorization,
    ),

    requires_sponsorship:
      form.requires_sponsorship,

    willing_to_relocate:
      form.willing_to_relocate,

    preferred_work_modes: splitCommaValues(
      form.preferred_work_modes,
    ),

    target_roles: splitCommaValues(
      form.target_roles,
    ),

    preferred_locations: splitCommaValues(
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

    auto_apply_enabled:
      form.auto_apply_enabled,
  };
}

export default function CandidateProfileForm() {
  const [form, setForm] =
    useState<ProfileFormState>(initialForm);

  const [loading, setLoading] =
    useState(true);

  const [saving, setSaving] =
    useState(false);

  const [successMessage, setSuccessMessage] =
    useState("");

  const [errorMessage, setErrorMessage] =
    useState("");

  const [lastSaved, setLastSaved] =
    useState<string | null>(null);

  const [verifying, setVerifying] = useState(false);

  const [activeTab, setActiveTab] = useState<ProfileTab>("profile");

  async function handleVerifyAll(): Promise<void> {
    setSuccessMessage("");
    setErrorMessage("");
    setVerifying(true);
    try {
      const result = await verifyAllProfileFacts();

      // Re-fetch the profile in place so the verification state
      // reflects the server, without a full page reload that
      // would discard unsaved edits. Section managers re-fetch
      // their own records when their tab is opened.
      const profile = await getCandidateProfile();

      setForm((previous) => ({
        ...previous,
        facts_verified:
          profile?.facts_verified ?? true,
      }));

      if (profile) {
        setLastSaved(profile.updated_at);
      }

      setSuccessMessage(
        `Verified ${result.total} record${
          result.total === 1 ? "" : "s"
        }.`,
      );
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Unable to verify records.",
      );
    } finally {
      setVerifying(false);
    }
  }

  useEffect(() => {
    async function loadProfile(): Promise<void> {
      try {
        setLoading(true);
        setErrorMessage("");

        const profile =
          await getCandidateProfile();

        if (profile) {
          setForm(profileToForm(profile));
          setLastSaved(profile.updated_at);
        }
      } catch (error) {
        setErrorMessage(
          error instanceof Error
            ? error.message
            : "Unable to load candidate profile.",
        );
      } finally {
        setLoading(false);
      }
    }

    void loadProfile();
  }, []);

  function updateField<
    K extends keyof ProfileFormState,
  >(
    field: K,
    value: ProfileFormState[K],
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
      setErrorMessage(
        "Full name is required.",
      );
      return;
    }

    if (!form.email.trim()) {
      setErrorMessage(
        "Email address is required.",
      );
      return;
    }

    const minimumMatchScore = Number(
      form.minimum_match_score,
    );

    if (
      Number.isNaN(minimumMatchScore) ||
      minimumMatchScore < 85 ||
      minimumMatchScore > 100
    ) {
      setErrorMessage(
        "Minimum match score must be between 85 and 100.",
      );
      return;
    }

    const minimumSalary =
      form.minimum_salary.trim() === ""
        ? null
        : Number(form.minimum_salary);

    if (
      minimumSalary !== null &&
      (
        Number.isNaN(minimumSalary) ||
        minimumSalary < 0
      )
    ) {
      setErrorMessage(
        "Minimum salary must be a valid positive number.",
      );
      return;
    }

    if (
      form.auto_apply_enabled &&
      !form.facts_verified
    ) {
      setErrorMessage(
        "Verify your information before enabling automatic applications.",
      );
      return;
    }

    try {
      setSaving(true);

      const savedProfile =
        await saveCandidateProfile(
          formToPayload(form),
        );

      setForm(
        profileToForm(savedProfile),
      );

      setLastSaved(
        savedProfile.updated_at,
      );

      setSuccessMessage(
        "Candidate profile saved successfully.",
      );
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Unable to save candidate profile.",
      );
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50 text-slate-900">
        <p className="text-slate-600">
          Loading candidate profile...
        </p>
      </main>
    );
  }

  return (
    <main className="cp-page">
      <div className="mx-auto max-w-6xl">
        <header className="mb-8">
          <Link
            href="/"
            className="text-sm font-medium text-violet-600 transition hover:text-violet-700"
          >
            ← Back to dashboard
          </Link>

          <div className="mt-4 flex flex-col justify-between gap-5 sm:flex-row sm:items-center">
            <div>
              <h1 className="text-3xl font-bold sm:text-4xl">
                Candidate Profile
              </h1>

              <p className="mt-3 max-w-3xl leading-7 text-slate-500">
                This verified information will be
                used for job matching, CV tailoring,
                salary suggestions and applications.
              </p>
            </div>

            <div className="flex flex-col items-start gap-3 sm:items-end">
              <ProfileVerificationBadge
                verified={form.facts_verified}
              />
              <button
                type="button"
                onClick={() => void handleVerifyAll()}
                disabled={verifying}
                className="cp-btn-primary px-4 py-2 text-sm"
              >
                {verifying ? "Verifying…" : "Verify all details"}
              </button>
            </div>
          </div>
        </header>

        <nav className="mb-6 flex flex-wrap gap-2">
          {PROFILE_TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                activeTab === tab.id
                  ? "bg-violet-600 text-white"
                  : "border border-slate-300 bg-white text-slate-700 hover:border-violet-400 hover:text-violet-700"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        {successMessage && (
          <MessageBox type="success">
            {successMessage}
          </MessageBox>
        )}

        {errorMessage && (
          <MessageBox type="error">
            {errorMessage}
          </MessageBox>
        )}

        <form
          onSubmit={(event) =>
            void handleSubmit(event)
          }
          className={`space-y-8 ${activeTab === "profile" ? "" : "hidden"}`}
        >
          <FormSection
            title="Personal details"
            description="Basic information used in job applications."
          >
            <div className="grid gap-5 md:grid-cols-2">
              <TextField
                label="Full name"
                value={form.full_name}
                required
                onChange={(value) =>
                  updateField(
                    "full_name",
                    value,
                  )
                }
              />

              <TextField
                label="Email address"
                type="email"
                value={form.email}
                required
                onChange={(value) =>
                  updateField(
                    "email",
                    value,
                  )
                }
              />

              <TextField
                label="Phone number"
                value={form.phone}
                placeholder="+44..."
                onChange={(value) =>
                  updateField(
                    "phone",
                    value,
                  )
                }
              />

              <TextField
                label="Current location"
                value={form.location}
                placeholder="United Kingdom"
                onChange={(value) =>
                  updateField(
                    "location",
                    value,
                  )
                }
              />
            </div>
          </FormSection>

          <FormSection
            title="Professional identity"
            description="Your main professional title and summary."
          >
            <div className="space-y-5">
              <TextField
                label="Professional title"
                value={
                  form.professional_title
                }
                placeholder="AI & ML Engineer"
                onChange={(value) =>
                  updateField(
                    "professional_title",
                    value,
                  )
                }
              />

              <TextAreaField
                label="Professional summary"
                value={
                  form.professional_summary
                }
                placeholder="Describe your experience, strengths and career goals."
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
            description="These links may be included in CVs and job applications."
          >
            <div className="grid gap-5 md:grid-cols-2">
              <TextField
                label="LinkedIn URL"
                type="url"
                value={form.linkedin_url}
                placeholder="https://linkedin.com/in/..."
                onChange={(value) =>
                  updateField(
                    "linkedin_url",
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

              <TextField
                label="Portfolio URL"
                type="url"
                value={form.portfolio_url}
                placeholder="https://..."
                onChange={(value) =>
                  updateField(
                    "portfolio_url",
                    value,
                  )
                }
              />
            </div>
          </FormSection>

          <FormSection
            title="Job preferences"
            description="Add multiple target roles separated by commas, then pick your preferred locations and work modes."
          >
            <div className="space-y-5">
              <TextAreaField
                label="Target roles"
                value={form.target_roles}
                placeholder="AI Engineer, Machine Learning Engineer"
                onChange={(value) =>
                  updateField(
                    "target_roles",
                    value,
                  )
                }
              />

              <CountryMultiSelect
                label="Preferred locations"
                value={
                  form.preferred_locations
                }
                onChange={(value) =>
                  updateField(
                    "preferred_locations",
                    value,
                  )
                }
              />

              <WorkModeSelector
                label="Preferred work modes"
                value={
                  form.preferred_work_modes
                }
                onChange={(value) =>
                  updateField(
                    "preferred_work_modes",
                    value,
                  )
                }
              />

              <CheckboxField
                label="I am willing to relocate"
                checked={
                  form.willing_to_relocate
                }
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
            description="This information must always remain accurate and truthful."
          >
            <div className="space-y-5">
              <TextAreaField
                label="Work authorisation details"
                value={
                  form.work_authorization
                }
                placeholder="Describe your current right-to-work status."
                helperText="Your right-to-work status in plain words (for example, a citizen, a visa holder, or requiring a permit). Used only as you write it; never inferred."
                onChange={(value) =>
                  updateField(
                    "work_authorization",
                    value,
                  )
                }
              />

              <div>
                <CheckboxField
                  label="I require employment sponsorship"
                  checked={
                    form.requires_sponsorship
                  }
                  onChange={(checked) =>
                    updateField(
                      "requires_sponsorship",
                      checked,
                    )
                  }
                />
                <p className="mt-1.5 text-xs cp-muted">
                  Tick this if you would need an employer to sponsor a
                  work visa. It informs eligibility checks and
                  application answers.
                </p>
              </div>
            </div>
          </FormSection>

          <FormSection
            title="Salary and matching"
            description="These rules control job filtering and automatic application decisions."
          >
            <div className="grid gap-5 md:grid-cols-3">
              <TextField
                label="Minimum salary"
                type="number"
                value={form.minimum_salary}
                placeholder="35000"
                min="0"
                onChange={(value) =>
                  updateField(
                    "minimum_salary",
                    value,
                  )
                }
              />

              <TextField
                label="Salary currency"
                value={
                  form.salary_currency
                }
                placeholder="GBP"
                onChange={(value) =>
                  updateField(
                    "salary_currency",
                    value,
                  )
                }
              />

              <TextField
                label="Minimum match score"
                type="number"
                min="85"
                max="100"
                value={
                  form.minimum_match_score
                }
                helperText="Only jobs scoring at or above this percentage (85–100) are treated as matches for filtering and automatic decisions."
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
              <CheckboxField
                label="I have checked these details and confirm they are accurate"
                checked={
                  form.facts_verified
                }
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

              <CheckboxField
                label="Enable automatic applications for eligible 85–100% matches"
                checked={
                  form.auto_apply_enabled
                }
                disabled={
                  !form.facts_verified
                }
                onChange={(checked) =>
                  updateField(
                    "auto_apply_enabled",
                    checked,
                  )
                }
              />
            </div>
          </FormSection>

          <div className="flex flex-col justify-between gap-4 cp-card sm:flex-row sm:items-center">
            <div>
              <p className="font-medium text-slate-900">
                Candidate facts vault
              </p>

              <p className="mt-1 text-sm text-slate-500">
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
              className="cp-btn-primary px-7 disabled:cursor-not-allowed"
            >
              {saving
                ? "Saving..."
                : "Save profile"}
            </button>
          </div>
        </form>

        {activeTab === "education" && <EducationManager />}
        {activeTab === "experience" && <ExperienceManager />}
        {activeTab === "projects" && <ProjectManager />}
        {activeTab === "skills" && <SkillManager />}
        {activeTab === "certifications" && <CertificationManager />}
      </div>
    </main>
  );
}

type FormSectionProps = {
  title: string;
  description: string;
  children: ReactNode;
};

function FormSection({
  title,
  description,
  children,
}: FormSectionProps) {
  return (
    <section className="cp-card">
      <h2 className="text-xl font-semibold text-slate-900">
        {title}
      </h2>

      <p className="mt-2 mb-6 text-sm leading-6 text-slate-500">
        {description}
      </p>

      {children}
    </section>
  );
}

type TextFieldProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?:
    | "text"
    | "email"
    | "url"
    | "number";
  placeholder?: string;
  required?: boolean;
  min?: string;
  max?: string;
  helperText?: string;
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
  helperText,
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
        placeholder={placeholder}
        onChange={(event) =>
          onChange(event.target.value)
        }
        className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-violet-500 focus:ring-2 focus:ring-violet-200"
      />

      {helperText ? (
        <span className="mt-1.5 block text-xs cp-muted">
          {helperText}
        </span>
      ) : null}
    </label>
  );
}

type TextAreaFieldProps = {
  label: string;
  value: string;
  placeholder?: string;
  onChange: (value: string) => void;
  helperText?: string;
};

function TextAreaField({
  label,
  value,
  placeholder,
  onChange,
  helperText,
}: TextAreaFieldProps) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-medium text-slate-700">
        {label}
      </span>

      <textarea
        value={value}
        rows={4}
        placeholder={placeholder}
        onChange={(event) =>
          onChange(event.target.value)
        }
        className="w-full resize-y rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-violet-500 focus:ring-2 focus:ring-violet-200"
      />

      {helperText ? (
        <span className="mt-1.5 block text-xs cp-muted">
          {helperText}
        </span>
      ) : null}
    </label>
  );
}

type CheckboxFieldProps = {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
};

function CheckboxField({
  label,
  checked,
  onChange,
  disabled = false,
}: CheckboxFieldProps) {
  return (
    <label
      className={`flex items-start gap-3 ${
        disabled
          ? "cursor-not-allowed opacity-50"
          : "cursor-pointer"
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

      <span className="text-sm leading-6 text-slate-600">
        {label}
      </span>
    </label>
  );
}

function ProfileVerificationBadge({
  verified,
}: {
  verified: boolean;
}) {
  return (
    <span
      className={`rounded-full border px-4 py-2 text-sm font-semibold ${
        verified
          ? "border-emerald-200 bg-emerald-50 text-emerald-700"
          : "border-amber-200 bg-amber-50 text-amber-700"
      }`}
    >
      {verified
        ? "Profile verified"
        : "Verification required"}
    </span>
  );
}

function MessageBox({
  type,
  children,
}: {
  type: "success" | "error";
  children: ReactNode;
}) {
  const className =
    type === "success"
      ? "border-emerald-200 bg-emerald-50 text-emerald-700"
      : "border-red-200 bg-red-50 text-red-700";

  return (
    <div
      className={`mb-6 rounded-xl border p-4 ${className}`}
    >
      {children}
    </div>
  );
}
