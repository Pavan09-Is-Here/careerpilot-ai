"use client";

import {
  useEffect,
  useState,
  type FormEvent,
} from "react";

import {
  createCertification,
  deleteCertification,
  getCertificationRecords,
  updateCertification,
} from "@/lib/api";

import type {
  Certification,
  CertificationInput,
} from "@/types/certification";

type CertificationFormState = {
  name: string;
  issuing_organization: string;
  credential_id: string;
  credential_url: string;
  issue_date: string;
  expiry_date: string;
  does_not_expire: boolean;
  description: string;
  skills: string;
  verified: boolean;
};

const emptyCertificationForm: CertificationFormState =
  {
    name: "",
    issuing_organization: "",
    credential_id: "",
    credential_url: "",
    issue_date: "",
    expiry_date: "",
    does_not_expire: false,
    description: "",
    skills: "",
    verified: false,
  };

function optionalText(
  value: string,
): string | null {
  const cleanedValue = value.trim();

  return cleanedValue || null;
}

function splitCommaValues(
  value: string,
): string[] {
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

function formToPayload(
  form: CertificationFormState,
): CertificationInput {
  return {
    name: form.name.trim(),

    issuing_organization:
      form.issuing_organization.trim(),

    credential_id: optionalText(
      form.credential_id,
    ),

    credential_url: optionalText(
      form.credential_url,
    ),

    issue_date: form.issue_date,

    expiry_date:
      form.does_not_expire ||
      !form.expiry_date
        ? null
        : form.expiry_date,

    does_not_expire:
      form.does_not_expire,

    description: optionalText(
      form.description,
    ),

    skills: splitCommaValues(form.skills),

    verified: form.verified,
  };
}

function certificationToForm(
  certification: Certification,
): CertificationFormState {
  return {
    name: certification.name,

    issuing_organization:
      certification.issuing_organization,

    credential_id:
      certification.credential_id ?? "",

    credential_url:
      certification.credential_url ?? "",

    issue_date: certification.issue_date,

    expiry_date:
      certification.expiry_date ?? "",

    does_not_expire:
      certification.does_not_expire,

    description:
      certification.description ?? "",

    skills: certification.skills.join(", "),

    verified: certification.verified,
  };
}

function formatDate(
  value: string | null,
): string {
  if (!value) {
    return "Not specified";
  }

  const date = new Date(
    `${value}T00:00:00`,
  );

  return date.toLocaleDateString(undefined, {
    month: "short",
    year: "numeric",
  });
}

function getExpiryStatus(
  certification: Certification,
): {
  label: string;
  className: string;
} {
  if (certification.does_not_expire) {
    return {
      label: "No expiry",
      className:
        "border-blue-800 bg-blue-950 text-blue-300",
    };
  }

  if (!certification.expiry_date) {
    return {
      label: "Expiry unknown",
      className:
        "border-slate-700 bg-slate-950 text-slate-300",
    };
  }

  const expiryDate = new Date(
    `${certification.expiry_date}T23:59:59`,
  );

  if (expiryDate.getTime() < Date.now()) {
    return {
      label: "Expired",
      className:
        "border-red-900 bg-red-950 text-red-300",
    };
  }

  return {
    label: "Active",
    className:
      "border-emerald-800 bg-emerald-950 text-emerald-300",
  };
}

export default function CertificationManager() {
  const [records, setRecords] = useState<
    Certification[]
  >([]);

  const [form, setForm] =
    useState<CertificationFormState>(
      emptyCertificationForm,
    );

  const [editingId, setEditingId] =
    useState<number | null>(null);

  const [loading, setLoading] =
    useState(true);

  const [saving, setSaving] =
    useState(false);

  const [deletingId, setDeletingId] =
    useState<number | null>(null);

  const [successMessage, setSuccessMessage] =
    useState("");

  const [errorMessage, setErrorMessage] =
    useState("");

  useEffect(() => {
    void loadCertifications();
  }, []);

  async function loadCertifications(): Promise<void> {
    try {
      setLoading(true);
      setErrorMessage("");

      const certificationRecords =
        await getCertificationRecords();

      setRecords(certificationRecords);
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Unable to load certifications.",
      );
    } finally {
      setLoading(false);
    }
  }

  function updateField<
    K extends keyof CertificationFormState,
  >(
    field: K,
    value: CertificationFormState[K],
  ): void {
    setForm((currentForm) => ({
      ...currentForm,
      [field]: value,
    }));
  }

  function resetForm(): void {
    setForm(emptyCertificationForm);
    setEditingId(null);
  }

  function beginEditing(
    certification: Certification,
  ): void {
    setForm(
      certificationToForm(certification),
    );

    setEditingId(certification.id);
    setSuccessMessage("");
    setErrorMessage("");

    document
      .getElementById(
        "certification-form",
      )
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
        "Certification name is required.",
      );
      return;
    }

    if (
      !form.issuing_organization.trim()
    ) {
      setErrorMessage(
        "Issuing organisation is required.",
      );
      return;
    }

    if (!form.issue_date) {
      setErrorMessage(
        "Issue date is required.",
      );
      return;
    }

    if (
      !form.does_not_expire &&
      form.expiry_date &&
      form.expiry_date < form.issue_date
    ) {
      setErrorMessage(
        "Expiry date cannot be before the issue date.",
      );
      return;
    }

    if (
      form.credential_url.trim() &&
      !form.credential_url.startsWith(
        "http://",
      ) &&
      !form.credential_url.startsWith(
        "https://",
      )
    ) {
      setErrorMessage(
        "Credential URL must start with http:// or https://.",
      );
      return;
    }

    try {
      setSaving(true);

      if (editingId === null) {
        await createCertification(
          formToPayload(form),
        );

        setSuccessMessage(
          "Certification added successfully.",
        );
      } else {
        await updateCertification(
          editingId,
          formToPayload(form),
        );

        setSuccessMessage(
          "Certification updated successfully.",
        );
      }

      resetForm();
      await loadCertifications();
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Unable to save certification.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(
    certificationId: number,
  ): Promise<void> {
    const confirmed = window.confirm(
      "Delete this certification?",
    );

    if (!confirmed) {
      return;
    }

    try {
      setDeletingId(certificationId);
      setSuccessMessage("");
      setErrorMessage("");

      await deleteCertification(
        certificationId,
      );

      if (
        editingId === certificationId
      ) {
        resetForm();
      }

      setSuccessMessage(
        "Certification deleted successfully.",
      );

      await loadCertifications();
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Unable to delete certification.",
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
          Certifications
        </h2>

        <p className="mt-3 max-w-3xl leading-7 text-slate-400">
          Add only genuine certifications,
          credentials, licences, and completed
          professional training.
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

      <div className="grid gap-8 xl:grid-cols-[1.05fr_0.95fr]">
        <form
          id="certification-form"
          onSubmit={(event) =>
            void handleSubmit(event)
          }
          className="rounded-2xl border border-slate-800 bg-slate-900 p-6"
        >
          <div className="mb-6 flex items-center justify-between gap-4">
            <div>
              <h3 className="text-xl font-semibold">
                {editingId === null
                  ? "Add certification"
                  : "Edit certification"}
              </h3>

              <p className="mt-2 text-sm text-slate-400">
                Store credential details exactly as
                shown by the issuing organisation.
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
              label="Certification name *"
              value={form.name}
              required
              placeholder="Certification name"
              onChange={(value) =>
                updateField("name", value)
              }
            />

            <TextField
              label="Issuing organisation *"
              value={
                form.issuing_organization
              }
              required
              placeholder="Issuing organisation"
              onChange={(value) =>
                updateField(
                  "issuing_organization",
                  value,
                )
              }
            />

            <TextField
              label="Credential ID"
              value={form.credential_id}
              placeholder="Credential identifier"
              onChange={(value) =>
                updateField(
                  "credential_id",
                  value,
                )
              }
            />

            <TextField
              label="Credential URL"
              type="url"
              value={form.credential_url}
              placeholder="https://..."
              onChange={(value) =>
                updateField(
                  "credential_url",
                  value,
                )
              }
            />

            <div className="grid gap-5 md:grid-cols-2">
              <TextField
                label="Issue date *"
                type="date"
                value={form.issue_date}
                required
                onChange={(value) =>
                  updateField(
                    "issue_date",
                    value,
                  )
                }
              />

              <TextField
                label="Expiry date"
                type="date"
                value={form.expiry_date}
                disabled={
                  form.does_not_expire
                }
                onChange={(value) =>
                  updateField(
                    "expiry_date",
                    value,
                  )
                }
              />
            </div>

            <CheckboxField
              label="This certification does not expire"
              checked={
                form.does_not_expire
              }
              onChange={(checked) => {
                updateField(
                  "does_not_expire",
                  checked,
                );

                if (checked) {
                  updateField(
                    "expiry_date",
                    "",
                  );
                }
              }}
            />

            <TextField
              label="Related skills"
              value={form.skills}
              placeholder="Python, Machine Learning, Data Analysis"
              onChange={(value) =>
                updateField(
                  "skills",
                  value,
                )
              }
            />

            <TextAreaField
              label="Description"
              value={form.description}
              placeholder="Describe the topics, assessment, practical work, or knowledge covered."
              onChange={(value) =>
                updateField(
                  "description",
                  value,
                )
              }
            />

            <CheckboxField
              label="I confirm that I genuinely earned this certification"
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
                  ? "Add certification"
                  : "Update certification"}
            </button>
          </div>
        </form>

        <div className="space-y-5">
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h3 className="text-xl font-semibold">
              Saved certifications
            </h3>

            <p className="mt-2 text-sm text-slate-400">
              {records.length}{" "}
              {records.length === 1
                ? "certification"
                : "certifications"}
            </p>

            <div className="mt-5 grid grid-cols-2 gap-3">
              <Statistic
                label="Verified"
                value={
                  records.filter(
                    (record) =>
                      record.verified,
                  ).length
                }
              />

              <Statistic
                label="Active"
                value={
                  records.filter(
                    (record) =>
                      getExpiryStatus(record)
                        .label !== "Expired",
                  ).length
                }
              />
            </div>
          </div>

          {loading && (
            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 text-slate-400">
              Loading certifications...
            </div>
          )}

          {!loading &&
            records.length === 0 && (
              <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-900/60 p-8 text-center">
                <p className="font-medium">
                  No certifications added
                </p>

                <p className="mt-2 text-sm text-slate-400">
                  Add only genuine completed
                  certifications and credentials.
                </p>
              </div>
            )}

          {!loading &&
            records.map(
              (certification) => {
                const expiryStatus =
                  getExpiryStatus(
                    certification,
                  );

                return (
                  <article
                    key={certification.id}
                    className="rounded-2xl border border-slate-800 bg-slate-900 p-6"
                  >
                    <div className="flex flex-col justify-between gap-4 sm:flex-row">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="text-lg font-semibold">
                            {
                              certification.name
                            }
                          </h3>

                          <VerificationBadge
                            verified={
                              certification.verified
                            }
                          />

                          <span
                            className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${expiryStatus.className}`}
                          >
                            {
                              expiryStatus.label
                            }
                          </span>
                        </div>

                        <p className="mt-2 font-medium text-blue-300">
                          {
                            certification.issuing_organization
                          }
                        </p>

                        <p className="mt-2 text-sm text-slate-400">
                          Issued{" "}
                          {formatDate(
                            certification.issue_date,
                          )}
                        </p>

                        {!certification.does_not_expire &&
                          certification.expiry_date && (
                            <p className="mt-1 text-sm text-slate-400">
                              Expires{" "}
                              {formatDate(
                                certification.expiry_date,
                              )}
                            </p>
                          )}

                        {certification.credential_id && (
                          <p className="mt-2 text-sm text-slate-400">
                            Credential ID:{" "}
                            {
                              certification.credential_id
                            }
                          </p>
                        )}
                      </div>

                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() =>
                            beginEditing(
                              certification,
                            )
                          }
                          className="rounded-lg border border-slate-700 px-3 py-2 text-sm hover:border-slate-500"
                        >
                          Edit
                        </button>

                        <button
                          type="button"
                          disabled={
                            deletingId ===
                            certification.id
                          }
                          onClick={() =>
                            void handleDelete(
                              certification.id,
                            )
                          }
                          className="rounded-lg border border-red-900 px-3 py-2 text-sm text-red-300 hover:bg-red-950 disabled:opacity-50"
                        >
                          {deletingId ===
                          certification.id
                            ? "Deleting..."
                            : "Delete"}
                        </button>
                      </div>
                    </div>

                    {certification.description && (
                      <p className="mt-5 text-sm leading-6 text-slate-300">
                        {
                          certification.description
                        }
                      </p>
                    )}

                    {certification.skills.length >
                      0 && (
                      <div className="mt-5 flex flex-wrap gap-2">
                        {certification.skills.map(
                          (skill) => (
                            <span
                              key={skill}
                              className="rounded-full border border-slate-700 bg-slate-950 px-3 py-1 text-xs text-slate-300"
                            >
                              {skill}
                            </span>
                          ),
                        )}
                      </div>
                    )}

                    {certification.credential_url && (
                      <a
                        href={
                          certification.credential_url
                        }
                        target="_blank"
                        rel="noreferrer"
                        className="mt-5 inline-block rounded-lg border border-slate-700 px-4 py-2 text-sm text-blue-300 hover:border-blue-500"
                      >
                        View credential
                      </a>
                    )}
                  </article>
                );
              },
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
  type?: "text" | "url" | "date";
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
        rows={5}
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
      {verified
        ? "Verified"
        : "Not verified"}
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
    <div className="rounded-xl border border-slate-800 bg-slate-950 p-3 text-center">
      <p className="text-xl font-bold">
        {value}
      </p>

      <p className="mt-1 text-xs text-slate-400">
        {label}
      </p>
    </div>
  );
}