/**
 * useTableControls — Sprint 5 shared hook
 *
 * Provides debounced search, status filter, column sort, and
 * client-side pagination for any list-based module.
 *
 * Usage:
 *   const ctrl = useTableControls(data, {
 *     searchFields: ["name", "id", "ward"],
 *     filterField:  "status",
 *     sortDefault:  { field: "id", dir: "asc" },
 *     pageSize:     8,
 *   });
 *
 * Returns:
 *   search / setSearch       — raw search string (for controlled input)
 *   activeFilter / setFilter — current status filter ("All" or a status value)
 *   sort / toggleSort        — { field, dir } and toggle function
 *   page / setPage           — current page (1-based)
 *   paginated                — the current page's rows
 *   filtered                 — all rows after search + filter (pre-pagination)
 *   totalPages               — total number of pages
 *   total                    — count of rows after search + filter
 */
import { useState, useMemo, useCallback, useEffect } from "react";

/* Debounce the search string to avoid filtering on every keystroke */
function useDebounce(value, delay = 220) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);
  return debounced;
}

export function useTableControls(data, {
  searchFields = [],
  filterField  = "status",
  sortDefault  = { field: null, dir: "asc" },
  pageSize     = 8,
  storageKey   = "",
} = {}) {
  const [search,       setSearch]       = useState("");
  const [activeFilter, setFilter]       = useState("All");
  
  const [sort, setSort] = useState(() => {
    if (storageKey) {
      const saved = localStorage.getItem(`medidispense_sort_${storageKey}`);
      if (saved) {
        try {
          return JSON.parse(saved);
        } catch (e) {
          console.error("Error parsing saved sort:", e);
        }
      }
    }
    return sortDefault;
  });

  /* Sync sort changes to localStorage */
  useEffect(() => {
    if (storageKey) {
      localStorage.setItem(`medidispense_sort_${storageKey}`, JSON.stringify(sort));
    }
  }, [sort, storageKey]);

  const [page,         setPage]         = useState(1);

  const debouncedSearch = useDebounce(search);

  /* Reset to page 1 whenever filter/search/sort changes */
  useEffect(() => { setPage(1); }, [debouncedSearch, activeFilter, sort.field, sort.dir]);

  const filtered = useMemo(() => {
    let result = Array.isArray(data) ? data : [];

    /* Status filter */
    if (activeFilter !== "All" && filterField) {
      result = result.filter(item => item[filterField] === activeFilter);
    }

    /* Search — checked across all searchFields */
    if (debouncedSearch) {
      const q = debouncedSearch.toLowerCase();
      result = result.filter(item =>
        searchFields.some(f => String(item[f] ?? "").toLowerCase().includes(q))
      );
    }

    /* Sort */
    if (sort.field) {
      result = [...result].sort((a, b) => {
        const av = String(a[sort.field] ?? "").toLowerCase();
        const bv = String(b[sort.field] ?? "").toLowerCase();
        /* Numeric sort for numeric-looking values */
        const an = parseFloat(av);
        const bn = parseFloat(bv);
        const cmp = !isNaN(an) && !isNaN(bn)
          ? an - bn
          : av.localeCompare(bv);
        return sort.dir === "asc" ? cmp : -cmp;
      });
    }

    return result;
  }, [data, debouncedSearch, activeFilter, sort, searchFields, filterField]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));

  const safePage = Math.min(page, totalPages);

  const paginated = useMemo(() => {
    const start = (safePage - 1) * pageSize;
    return filtered.slice(start, start + pageSize);
  }, [filtered, safePage, pageSize]);

  const toggleSort = useCallback((field) => {
    setSort(prev =>
      prev.field === field && prev.dir === "asc"
        ? { field, dir: "desc" }
        : { field, dir: "asc" }
    );
  }, []);

  return {
    /* Controlled inputs */
    search, setSearch,
    activeFilter, setFilter,
    sort, toggleSort,

    /* Pagination */
    page: safePage, setPage,
    totalPages,

    /* Data slices */
    filtered,
    paginated,
    total: filtered.length,
  };
}
