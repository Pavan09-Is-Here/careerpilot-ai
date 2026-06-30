"use client";

import {
  useState,
  type FormEvent,
} from "react";

import { generateVerifiedMasterCV } from "@/lib/api";

import {
  ErrorNotice,
  SuccessNotice,
  isMasterGenerationParent,
} from "@/components/documents/DocumentPrimitives";

import type {
  CVMasterGenerationResponse,
  CVVersion,
} from "@/types/cvVersion";

type MasterGenerationPanelProps = {
  parentVersion: CVVersion;
  onGenerated: (
    response: CVMasterGenerationResponse,
  ) => void;
};

function createIdempotencyKey(): string {
  if (typeof crypto.randomUUID === "function") {
    return `master-${crypto.randomUUID()}`;
  }

  return `master-${Date.now().toString(36)}-${Math.random()
    .toString(36)
    .slice(2)}`;
}

export default function MasterGenerationPanel({
  parentVersion,
  onGenerated,
}: MasterGenerationPanelProps) {
  const [displayName, setDisplayName] =
    useState("");
  const [description, setDescription] =
    useState("");
  const [isPrimary, setIsPrimary] =
    useState(false);
  const [activeKey, setActiveKey] = useState<
    string | null
  >(null);
  const [errorMessage, setErrorMessage] =
    useState("");
  const [successMessage, setSuccessMessage] =
    useState("");

  if (!isMasterGenerationParent(parentVersion)) {
    return null;
  }

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    if (activeKey !== null) {
      return;
    }

    const idempotencyKey = createIdempotencyKey();
    setActiveKey(idempotencyKey);
    setErrorMessage("");
    setSuccessMessage("");

    try {
      const response =
        await generateVerifiedMasterCV(
          parentVersion.id,
          {
            display_name:
              displayName.trim() || null,
            description:
              description.trim() || null,
            idempotency_key: idempotencyKey,
            is_primary: isPrimary,
          },
        );

      setSuccessMessage(
        response.created
          ? "Verified master CV generated."
          : "Existing verified master CV returned.",
      );
      setDisplayName("");
      setDescription("");
      setIsPrimary(false);
      onGenerated(response);
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Unable to generate verified master CV.",
      );
    } finally {
      setActiveKey(null);
    }
  }

  const generating = activeKey !== null;

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-lg border border-emerald-500/30 bg-emerald-950/20 p-5"
    >
      <div className="flex flex-col gap-4">
        <div>
          <h3 className="text-lg font-semibold text-white">
            Generate Verified Master CV
          </h3>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label
              htmlFor="master-display-name"
              className="block text-sm font-medium text-slate-200"
            >
              Display name
            </label>
            <input
              id="master-display-name"
              value={displayName}
              onChange={(event) =>
                setDisplayName(event.target.value)
              }
              maxLength={250}
              className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-emerald-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/40"
            />
          </div>

          <label className="flex items-end gap-3 rounded-lg border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-slate-200">
            <input
              type="checkbox"
              checked={isPrimary}
              onChange={(event) =>
                setIsPrimary(event.target.checked)
              }
              className="h-4 w-4 rounded border-slate-600 bg-slate-950 text-emerald-600 focus:ring-emerald-500"
            />
            Mark generated version primary
          </label>
        </div>

        <div>
          <label
            htmlFor="master-description"
            className="block text-sm font-medium text-slate-200"
          >
            Description
          </label>
          <textarea
            id="master-description"
            value={description}
            onChange={(event) =>
              setDescription(event.target.value)
            }
            rows={3}
            maxLength={1000}
            className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-emerald-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/40"
          />
        </div>

        {errorMessage ? (
          <ErrorNotice>{errorMessage}</ErrorNotice>
        ) : null}
        {successMessage ? (
          <SuccessNotice>
            {successMessage}
          </SuccessNotice>
        ) : null}

        <button
          type="submit"
          disabled={generating}
          className="inline-flex w-fit rounded-lg bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-300 disabled:cursor-not-allowed disabled:bg-slate-700"
        >
          {generating
            ? "Generating..."
            : "Generate Verified Master CV"}
        </button>
      </div>
    </form>
  );
}
