import { useId, useState } from "react";
import type { ReactNode } from "react";
import { ChevronDown, ListFilter } from "lucide-react";

type FilterDisclosureProps = {
  activeCount: number;
  hint: string;
  onClear: () => void;
  children: ReactNode;
};

export function FilterDisclosure({ activeCount, hint, onClear, children }: FilterDisclosureProps) {
  const [isOpen, setIsOpen] = useState(false);
  const panelId = useId();

  return (
    <div className="filter-disclosure">
      <div className="filter-disclosure-toolbar">
        <div className="filter-disclosure-actions">
          <button
            className="btn-secondary filter-toggle"
            type="button"
            aria-expanded={isOpen}
            aria-controls={panelId}
            onClick={() => setIsOpen((value) => !value)}
          >
            <ListFilter className="h-4 w-4" aria-hidden="true" />
            <span>Filtros</span>
            {activeCount > 0 && (
              <span className="filter-count">
                {activeCount} {activeCount === 1 ? "ativo" : "ativos"}
              </span>
            )}
            <ChevronDown
              className={`filter-chevron h-4 w-4${isOpen ? " is-open" : ""}`}
              aria-hidden="true"
            />
          </button>
          {activeCount > 0 && (
            <button className="btn-ghost" type="button" onClick={onClear}>
              Limpar filtros
            </button>
          )}
        </div>
        <p className="filter-disclosure-hint">{hint}</p>
      </div>
      <div id={panelId} className="filter-disclosure-panel" hidden={!isOpen}>
        {children}
      </div>
    </div>
  );
}
