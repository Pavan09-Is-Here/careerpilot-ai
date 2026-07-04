"use client";

import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { COUNTRIES } from "@/components/profile/countries";

type CountryMultiSelectProps = {
  value: string;
  onChange: (next: string) => void;
  label?: string;
};

function parseSelected(value: string): string[] {
  const seen = new Map<string, string>();

  for (const item of value.split(",")) {
    const cleaned = item.trim();

    if (cleaned) {
      seen.set(cleaned.toLowerCase(), cleaned);
    }
  }

  return Array.from(seen.values());
}

export default function CountryMultiSelect({
  value,
  onChange,
  label = "Preferred locations",
}: CountryMultiSelectProps) {
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState(false);

  const containerRef = useRef<HTMLDivElement | null>(null);

  const selected = useMemo(
    () => parseSelected(value),
    [value],
  );

  const selectedKeys = useMemo(
    () =>
      new Set(
        selected.map((item) => item.toLowerCase()),
      ),
    [selected],
  );

  const options = useMemo(() => {
    const query = search.trim().toLowerCase();

    return COUNTRIES.filter((country) => {
      if (selectedKeys.has(country.toLowerCase())) {
        return false;
      }

      if (!query) {
        return true;
      }

      return country.toLowerCase().includes(query);
    });
  }, [search, selectedKeys]);

  useEffect(() => {
    function handleOutsideClick(event: MouseEvent): void {
      if (
        containerRef.current &&
        !containerRef.current.contains(
          event.target as Node,
        )
      ) {
        setOpen(false);
      }
    }

    document.addEventListener(
      "mousedown",
      handleOutsideClick,
    );

    return () =>
      document.removeEventListener(
        "mousedown",
        handleOutsideClick,
      );
  }, []);

  function commit(next: string[]): void {
    onChange(next.join(", "));
  }

  function addCountry(country: string): void {
    if (selectedKeys.has(country.toLowerCase())) {
      return;
    }

    commit([...selected, country]);
    setSearch("");
    setOpen(false);
  }

  function removeCountry(country: string): void {
    commit(
      selected.filter(
        (item) =>
          item.toLowerCase() !==
          country.toLowerCase(),
      ),
    );
  }

  function handleKeyDown(
    event: React.KeyboardEvent<HTMLInputElement>,
  ): void {
    if (event.key === "Escape") {
      setOpen(false);
      return;
    }

    if (event.key === "Enter") {
      event.preventDefault();

      if (options.length > 0) {
        addCountry(options[0]);
      }
    }
  }

  return (
    <div className="block" ref={containerRef}>
      <span className="mb-2 block text-sm font-medium text-slate-700">
        {label}
      </span>

      {selected.length > 0 && (
        <ul className="mb-2 flex flex-wrap gap-2">
          {selected.map((country) => (
            <li key={country}>
              <span className="cp-chip gap-1 pr-1.5">
                {country}
                <button
                  type="button"
                  onClick={() =>
                    removeCountry(country)
                  }
                  aria-label={`Remove ${country}`}
                  className="ml-1 inline-flex h-4 w-4 items-center justify-center rounded-full text-violet-700 transition hover:bg-violet-200 hover:text-violet-900"
                >
                  <svg
                    viewBox="0 0 12 12"
                    className="h-2.5 w-2.5"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    aria-hidden="true"
                  >
                    <path d="M3 3l6 6M9 3l-6 6" />
                  </svg>
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}

      <div className="relative">
        <input
          type="text"
          value={search}
          role="combobox"
          aria-expanded={open}
          aria-controls="country-options"
          aria-autocomplete="list"
          placeholder="Search and add a country"
          className="cp-input"
          onFocus={() => setOpen(true)}
          onChange={(event) => {
            setSearch(event.target.value);
            setOpen(true);
          }}
          onKeyDown={handleKeyDown}
        />

        {open && (
          <ul
            id="country-options"
            className="absolute z-20 mt-1 max-h-56 w-full overflow-y-auto rounded-lg border border-slate-300 bg-white py-1 shadow-lg"
          >
            {options.length === 0 ? (
              <li className="px-3 py-2 text-sm text-slate-500">
                No matching countries
              </li>
            ) : (
              options.map((country) => (
                <li key={country}>
                  <button
                    type="button"
                    onClick={() =>
                      addCountry(country)
                    }
                    className="flex w-full items-center px-3 py-2 text-left text-sm text-slate-700 transition hover:bg-violet-50 hover:text-violet-700"
                  >
                    {country}
                  </button>
                </li>
              ))
            )}
          </ul>
        )}
      </div>
    </div>
  );
}
