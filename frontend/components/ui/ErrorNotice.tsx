import type { ReactNode } from "react";

type ErrorNoticeProps = {
  children: ReactNode;
  className?: string;
};

/**
 * Red cp-style error notice for failed requests. Use for inline error
 * feedback on list and form pages.
 */
export default function ErrorNotice({
  children,
  className,
}: ErrorNoticeProps) {
  return (
    <div
      role="alert"
      className={`rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 ${
        className ?? ""
      }`}
    >
      {children}
    </div>
  );
}
