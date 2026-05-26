import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, FileUp, Upload } from "lucide-react";
import { apiFetch } from "../api";
import { money, statusText } from "../format";
import type { ImportBatch } from "../types";

const mappingFields = [
  ["date_column", "Data"],
  ["description_column", "Descrição"],
  ["type_column", "Tipo"],
  ["amount_column", "Valor único"],
  ["income_amount_column", "Valor entrada"],
  ["expense_amount_column", "Valor saída"],
  ["due_date_column", "Vencimento"],
  ["notes_column", "Observações"],
] as const;

export function ImportsPage() {
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [batch, setBatch] = useState<ImportBatch | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});

  const headers = batch?.headers ?? [];
  const requiredReady = Boolean(mapping.date_column && mapping.description_column);
  const singleModeReady = Boolean(mapping.type_column && mapping.amount_column);
  const splitModeReady = Boolean(mapping.income_amount_column || mapping.expense_amount_column);
  const canValidate = Boolean(batch && requiredReady && (singleModeReady || splitModeReady));

  const upload = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error("Selecione um arquivo CSV ou XLSX.");
      const body = new FormData();
      body.append("file", file);
      return apiFetch<ImportBatch>("/imports/financial-transactions/upload", {
        method: "POST",
        body,
      });
    },
    onSuccess: (data) => {
      setBatch(data);
      setMapping({});
    },
  });

  const validate = useMutation({
    mutationFn: () =>
      apiFetch<ImportBatch>(`/imports/financial-transactions/${batch?.id}/validate`, {
        method: "POST",
        body: JSON.stringify({
          date_column: mapping.date_column,
          description_column: mapping.description_column,
          type_column: mapping.type_column || null,
          amount_column: mapping.amount_column || null,
          income_amount_column: mapping.income_amount_column || null,
          expense_amount_column: mapping.expense_amount_column || null,
          due_date_column: mapping.due_date_column || null,
          notes_column: mapping.notes_column || null,
        }),
      }),
    onSuccess: (data) => setBatch(data),
  });

  const confirm = useMutation({
    mutationFn: () =>
      apiFetch<{ batch: ImportBatch; created_transaction_ids: string[] }>(`/imports/financial-transactions/${batch?.id}/confirm`, {
        method: "POST",
      }),
    onSuccess: async (data) => {
      setBatch(data.batch);
      await queryClient.invalidateQueries();
    },
  });

  const columns = useMemo(
    () => (
      <>
        <option value="">Não mapear</option>
        {headers.map((header) => (
          <option key={header} value={header}>
            {header}
          </option>
        ))}
      </>
    ),
    [headers],
  );

  function onUpload(event: FormEvent) {
    event.preventDefault();
    upload.mutate();
  }

  return (
    <section className="space-y-5">
      <form className="panel space-y-4" onSubmit={onUpload}>
        <h2 className="panel-title">Enviar planilha</h2>
        <div className="grid gap-3 md:grid-cols-[1fr_auto]">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <label className="btn-secondary cursor-pointer" htmlFor="import-file">
              <FileUp className="h-4 w-4" />
              Selecionar arquivo
            </label>
            <input
              id="import-file"
              className="sr-only"
              type="file"
              accept=".csv,.xlsx"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
            <span className="text-sm text-muted">{file?.name ?? "Nenhum arquivo selecionado"}</span>
          </div>
          <button className="btn-primary" disabled={upload.isPending}>
            <Upload className="h-4 w-4" />
            Enviar
          </button>
        </div>
        {(upload.error || validate.error || confirm.error) && (
          <div className="alert-error">{upload.error?.message ?? validate.error?.message ?? confirm.error?.message}</div>
        )}
      </form>

      {batch && (
        <>
          <div className="panel">
            <div className="table-header">
              <div>
                <h2 className="panel-title">{batch.filename}</h2>
                <p className="section-subtitle">
                  Status: {statusText(batch.status)} · {batch.file_type.toUpperCase()}
                </p>
              </div>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>{headers.map((header) => <th key={header}>{header}</th>)}</tr>
                </thead>
                <tbody>
                  {batch.preview_rows.map((row, index) => (
                    <tr key={index}>
                      {headers.map((header) => <td key={header}>{row[header] ?? ""}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="panel space-y-4">
            <h2 className="panel-title">Mapeamento</h2>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {mappingFields.map(([field, label]) => (
                <label className="field" htmlFor={`mapping-${field}`} key={field}>
                  {label}
                  <select id={`mapping-${field}`} value={mapping[field] ?? ""} onChange={(event) => setMapping({ ...mapping, [field]: event.target.value })}>
                    {columns}
                  </select>
                </label>
              ))}
            </div>
            <div className="flex flex-wrap gap-3">
              <button className="btn-primary" disabled={!canValidate || validate.isPending} onClick={() => validate.mutate()}>
                Validar
              </button>
              <button
                className="btn-secondary"
                disabled={batch.status !== "validated" || confirm.isPending}
                onClick={() => confirm.mutate()}
              >
                <CheckCircle2 className="h-4 w-4" />
                Confirmar importação
              </button>
            </div>
          </div>

          {batch.summary && (
            <div className="grid gap-4 md:grid-cols-4">
              <div className="metric"><p>Total de linhas</p><strong>{batch.summary.total_rows}</strong></div>
              <div className="metric"><p>Linhas válidas</p><strong>{batch.summary.valid_rows}</strong></div>
              <div className="metric"><p>Entradas</p><strong>{money(batch.summary.income_total)}</strong></div>
              <div className="metric"><p>Saídas</p><strong>{money(batch.summary.expense_total)}</strong></div>
            </div>
          )}

          {(batch.validation_errors.length > 0 || batch.duplicate_warnings.length > 0) && (
            <div className="grid gap-5 lg:grid-cols-2">
              <div className="panel">
                <h2 className="panel-title">Erros de validação</h2>
                <ul className="mt-3 space-y-2 text-sm">
                  {batch.validation_errors.map((error, index) => (
                    <li className="alert-error" key={index}>
                      Linha {error.row_number}: {error.field} - {error.message}
                    </li>
                  ))}
                  {batch.validation_errors.length === 0 && <li className="text-muted">Nenhum erro.</li>}
                </ul>
              </div>
              <div className="panel">
                <h2 className="panel-title">Possíveis duplicidades</h2>
                <ul className="mt-3 space-y-2 text-sm">
                  {batch.duplicate_warnings.map((warning, index) => (
                    <li className="alert-warning" key={index}>
                      Linha {warning.row_number}: {warning.message}
                    </li>
                  ))}
                  {batch.duplicate_warnings.length === 0 && <li className="text-muted">Nenhum aviso.</li>}
                </ul>
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}
