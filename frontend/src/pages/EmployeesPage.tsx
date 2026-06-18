import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Ban, CheckCircle2, PlayCircle } from "lucide-react";
import { apiFetch } from "../api";
import { currencyInputToDecimal, dateText, formatCurrencyInput, money, statusText } from "../format";
import type { Employee, EmployeeStatus, SalaryExpenseGeneration } from "../types";

const today = new Date().toISOString().slice(0, 10);
const currentMonth = today.slice(0, 7);

export function EmployeesPage() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    name: "",
    position: "",
    salary_amount: "0,00",
    contract_start_date: today,
    contract_end_date: "",
    status: "active" as EmployeeStatus,
    notes: "",
  });
  const [generationMonth, setGenerationMonth] = useState(currentMonth);

  const employees = useQuery({
    queryKey: ["employees"],
    queryFn: () => apiFetch<Employee[]>("/employees"),
  });

  const create = useMutation({
    mutationFn: () =>
      apiFetch<Employee>("/employees", {
        method: "POST",
        body: JSON.stringify({
          name: form.name,
          position: form.position || null,
          salary_amount: currencyInputToDecimal(form.salary_amount),
          contract_start_date: form.contract_start_date,
          contract_end_date: form.contract_end_date || null,
          status: form.status,
          notes: form.notes || null,
        }),
      }),
    onSuccess: async () => {
      setForm({
        name: "",
        position: "",
        salary_amount: "0,00",
        contract_start_date: today,
        contract_end_date: "",
        status: "active",
        notes: "",
      });
      await queryClient.invalidateQueries({ queryKey: ["employees"] });
    },
  });

  const updateStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: EmployeeStatus }) =>
      apiFetch<Employee>(`/employees/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["employees"] }),
  });

  const generate = useMutation({
    mutationFn: () =>
      apiFetch<SalaryExpenseGeneration>("/employees/salary-expenses/generate", {
        method: "POST",
        body: JSON.stringify({ reference_month: `${generationMonth}-01` }),
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["transactions"] });
      await queryClient.invalidateQueries({ queryKey: ["payables"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      await queryClient.invalidateQueries({ queryKey: ["categories"] });
    },
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    create.mutate();
  }

  return (
    <section className="space-y-5">
      <form className="panel grid gap-4 lg:grid-cols-4" onSubmit={onSubmit}>
        <h2 className="panel-title lg:col-span-4">Novo funcionario</h2>
        <label className="field lg:col-span-2" htmlFor="employee-name">
          Nome
          <input
            id="employee-name"
            required
            minLength={2}
            value={form.name}
            onChange={(event) => setForm({ ...form, name: event.target.value })}
          />
        </label>
        <label className="field" htmlFor="employee-position">
          Cargo
          <input
            id="employee-position"
            value={form.position}
            onChange={(event) => setForm({ ...form, position: event.target.value })}
          />
        </label>
        <label className="field" htmlFor="employee-salary">
          Salario mensal
          <input
            id="employee-salary"
            required
            inputMode="numeric"
            value={form.salary_amount}
            onChange={(event) => setForm({ ...form, salary_amount: formatCurrencyInput(event.target.value) })}
          />
        </label>
        <label className="field" htmlFor="employee-start">
          Inicio do contrato
          <input
            id="employee-start"
            required
            type="date"
            value={form.contract_start_date}
            onChange={(event) => setForm({ ...form, contract_start_date: event.target.value })}
          />
        </label>
        <label className="field" htmlFor="employee-end">
          Fim do contrato
          <input
            id="employee-end"
            type="date"
            value={form.contract_end_date}
            onChange={(event) => setForm({ ...form, contract_end_date: event.target.value })}
          />
        </label>
        <label className="field" htmlFor="employee-status">
          Status
          <select
            id="employee-status"
            value={form.status}
            onChange={(event) => setForm({ ...form, status: event.target.value as EmployeeStatus })}
          >
            <option value="active">Ativo</option>
            <option value="inactive">Inativo</option>
            <option value="ended">Encerrado</option>
          </select>
        </label>
        <label className="field" htmlFor="employee-notes">
          Observacoes
          <input
            id="employee-notes"
            value={form.notes}
            onChange={(event) => setForm({ ...form, notes: event.target.value })}
          />
        </label>
        <div className="flex items-end">
          <button className="btn-primary w-full" disabled={create.isPending}>
            Salvar
          </button>
        </div>
        {create.error && <div className="alert-error lg:col-span-4">{create.error.message}</div>}
      </form>

      <div className="panel">
        <div className="table-header">
          <div>
            <h2 className="panel-title">Despesas salariais</h2>
            <p className="section-subtitle">Geracao manual de contas a pagar do mes.</p>
          </div>
          <div className="grid w-full gap-2 sm:w-auto sm:grid-cols-[180px_auto]">
            <input
              type="month"
              value={generationMonth}
              onChange={(event) => setGenerationMonth(event.target.value)}
            />
            <button
              className="btn-primary"
              disabled={generate.isPending || !generationMonth}
              onClick={() => generate.mutate()}
            >
              <PlayCircle className="h-4 w-4" />
              Gerar
            </button>
          </div>
        </div>
        {generate.error && <div className="mt-4 alert-error">{generate.error.message}</div>}
        {generate.data && (
          <div className="mt-4 alert-warning">
            Gerados: {generate.data.created_count}. Ignorados por duplicidade:{" "}
            {generate.data.skipped_count}.
          </div>
        )}
      </div>

      <div className="panel">
        <div className="table-header">
          <h2 className="panel-title">Funcionarios</h2>
          {employees.isFetching && <span className="text-sm text-muted">Atualizando...</span>}
        </div>
        {employees.isError && <div className="alert-error">{employees.error.message}</div>}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Nome</th>
                <th>Cargo</th>
                <th>Status</th>
                <th>Inicio</th>
                <th>Fim</th>
                <th className="text-right">Salario</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {(employees.data ?? []).map((employee) => (
                <tr key={employee.id}>
                  <td>{employee.name}</td>
                  <td>{employee.position || "-"}</td>
                  <td>{statusText(employee.status)}</td>
                  <td>{dateText(employee.contract_start_date)}</td>
                  <td>{dateText(employee.contract_end_date)}</td>
                  <td className="text-right">{money(employee.salary_amount)}</td>
                  <td className="text-right">
                    <div className="inline-flex gap-2">
                      {employee.status !== "active" && (
                        <button
                          className="icon-btn"
                          title="Ativar"
                          onClick={() => updateStatus.mutate({ id: employee.id, status: "active" })}
                        >
                          <CheckCircle2 className="h-4 w-4" />
                        </button>
                      )}
                      {employee.status === "active" && (
                        <button
                          className="icon-btn"
                          title="Inativar"
                          onClick={() =>
                            updateStatus.mutate({ id: employee.id, status: "inactive" })
                          }
                        >
                          <Ban className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
