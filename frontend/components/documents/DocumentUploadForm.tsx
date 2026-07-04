"use client";

import {
  useRef,
  useState,
  type ChangeEvent,
  type FormEvent,
} from "react";

import { uploadDocument } from "@/lib/api";

import {
  ErrorNotice,
  SuccessNotice,
  formatBytes,
  isSupportedDocumentFile,
  supportedDocumentExtensions,
  supportedDocumentMimes,
} from "@/components/documents/DocumentPrimitives";

import type {
  CVDocument,
  DocumentType,
} from "@/types/document";

type DocumentUploadFormProps = {
  onUploaded: (document: CVDocument) => void;
};

export default function DocumentUploadForm({
  onUploaded,
}: DocumentUploadFormProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(
    null,
  );

  const [selectedFile, setSelectedFile] =
    useState<File | null>(null);
  const [documentType, setDocumentType] =
    useState<DocumentType>("original_cv");
  const [isPrimary, setIsPrimary] =
    useState(false);
  const [submitting, setSubmitting] =
    useState(false);
  const [errorMessage, setErrorMessage] =
    useState("");
  const [successMessage, setSuccessMessage] =
    useState("");

  function handleFileChange(
    event: ChangeEvent<HTMLInputElement>,
  ): void {
    const file = event.target.files?.[0] ?? null;
    setSelectedFile(file);
    setSuccessMessage("");

    if (!file) {
      setErrorMessage("");
      return;
    }

    setErrorMessage(
      isSupportedDocumentFile(file) ?? "",
    );
  }

  function resetForm(): void {
    setSelectedFile(null);
    setDocumentType("original_cv");
    setIsPrimary(false);

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    if (submitting) {
      return;
    }

    setSuccessMessage("");
    setErrorMessage("");

    if (!selectedFile) {
      setErrorMessage("Choose a PDF or DOCX file.");
      return;
    }

    const validationError =
      isSupportedDocumentFile(selectedFile);

    if (validationError) {
      setErrorMessage(validationError);
      return;
    }

    try {
      setSubmitting(true);

      const uploadedDocument = await uploadDocument({
        file: selectedFile,
        document_type: documentType,
        is_primary:
          documentType === "original_cv" && isPrimary,
      });

      resetForm();
      setSuccessMessage("Document uploaded.");
      onUploaded(uploadedDocument);
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Unable to upload document.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  const fileInputDescription =
    "document-upload-help";
  const errorId = "document-upload-error";

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
    >
      <div className="flex flex-col gap-5">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">
            Upload CV document
          </h2>
        </div>

        <div>
          <label
            htmlFor="cv-document-file"
            className="block text-sm font-medium text-slate-700"
          >
            PDF or DOCX file
          </label>
          <input
            ref={fileInputRef}
            id="cv-document-file"
            name="file"
            type="file"
            accept={[
              ...supportedDocumentExtensions,
              ...supportedDocumentMimes,
            ].join(",")}
            onChange={handleFileChange}
            aria-describedby={`${fileInputDescription} ${
              errorMessage ? errorId : ""
            }`}
            className="mt-2 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 file:mr-4 file:rounded-md file:border-0 file:bg-violet-600 file:px-3 file:py-2 file:text-sm file:font-semibold file:text-white focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-200"
          />
          <p
            id={fileInputDescription}
            className="mt-2 text-xs text-slate-500"
          >
            Backend validation remains authoritative.
          </p>
        </div>

        {selectedFile ? (
          <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
            <p className="font-medium">
              {selectedFile.name}
            </p>
            <p className="mt-1 text-slate-500">
              {formatBytes(selectedFile.size)}
            </p>
          </div>
        ) : null}

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label
              htmlFor="document-type"
              className="block text-sm font-medium text-slate-700"
            >
              Document type
            </label>
            <select
              id="document-type"
              value={documentType}
              onChange={(event) => {
                const nextType = event.target
                  .value as DocumentType;
                setDocumentType(nextType);

                if (nextType !== "original_cv") {
                  setIsPrimary(false);
                }
              }}
              className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-200"
            >
              <option value="original_cv">
                Original CV
              </option>
              <option value="cover_letter">
                Cover letter
              </option>
              <option value="supporting_document">
                Supporting document
              </option>
            </select>
          </div>

          <div className="flex items-end">
            <label className="flex w-full items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={isPrimary}
                disabled={documentType !== "original_cv"}
                onChange={(event) =>
                  setIsPrimary(event.target.checked)
                }
                className="h-4 w-4 rounded border-slate-300 bg-white text-violet-600 focus:ring-violet-500"
              />
              Mark as primary original CV
            </label>
          </div>
        </div>

        {errorMessage ? (
          <div id={errorId}>
            <ErrorNotice>{errorMessage}</ErrorNotice>
          </div>
        ) : null}

        {successMessage ? (
          <SuccessNotice>
            {successMessage}
          </SuccessNotice>
        ) : null}

        <div className="flex flex-col gap-3 sm:flex-row">
          <button
            type="submit"
            disabled={submitting}
            className="inline-flex justify-center rounded-lg bg-violet-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-300 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {submitting ? "Uploading..." : "Upload document"}
          </button>

          <button
            type="button"
            disabled={submitting}
            onClick={resetForm}
            className="inline-flex justify-center rounded-lg border border-slate-300 px-5 py-2.5 text-sm font-semibold text-slate-700 transition hover:border-violet-400 hover:text-violet-700 focus:outline-none focus:ring-2 focus:ring-slate-300 disabled:cursor-not-allowed disabled:text-slate-400"
          >
            Reset
          </button>
        </div>
      </div>
    </form>
  );
}
