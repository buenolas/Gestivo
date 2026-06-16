import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Ban, CheckCircle2, KeyRound } from "lucide-react";
import { apiFetch } from "../api";
import type { CompanyUser } from "../types";

export function CompanyUsersPage() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ name: "", email: "", temporary_password: "" });
  const [resetUser, setResetUser] = useState<CompanyUser | null>(null);
  const [temporaryPassword, setTemporaryPassword] = useState("");

  const users = useQuery({
    queryKey: ["company-users"],
    queryFn: () => apiFetch<CompanyUser[]>("/company-users"),
  });

  const create = useMutation({
    mutationFn: () =>
      apiFetch<CompanyUser>("/company-users", {
        method: "POST",
        body: JSON.stringify(form),
      }),
    onSuccess: async () => {
      setForm({ name: "", email: "", temporary_password: "" });
      await queryClient.invalidateQueries({ queryKey: ["company-users"] });
    },
  });

  const updateStatus = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      apiFetch<CompanyUser>(`/company-users/${id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ is_active }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["company-users"] }),
  });

  const resetPassword = useMutation({
    mutationFn: () =>
      apiFetch<CompanyUser>(`/company-users/${resetUser!.id}/reset-password`, {
        method: "POST",
        body: JSON.stringify({ temporary_password: temporaryPassword }),
      }),
    onSuccess: async () => {
      setResetUser(null);
      setTemporaryPassword("");
      await queryClient.invalidateQueries({ queryKey: ["company-users"] });
    },
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    create.mutate();
  }

  return (
    <section className="space-y-5">
      <form className="panel grid gap-4 lg:grid-cols-4" onSubmit={onSubmit}>
        <div className="lg:col-span-4">
          <h2 className="panel-title">Novo usuario</h2>
          <p className="section-subtitle">
            Acesso limitado a lancamentos, categorias e contatos.
          </p>
        </div>
        <label className="field" htmlFor="company-user-name">
          Nome
          <input id="company-user-name" required minLength={2} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
        </label>
        <label className="field" htmlFor="company-user-email">
          E-mail
          <input id="company-user-email" required type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
        </label>
        <label className="field" htmlFor="company-user-password">
          Senha temporaria
          <input id="company-user-password" required minLength={8} type="password" value={form.temporary_password} onChange={(event) => setForm({ ...form, temporary_password: event.target.value })} />
        </label>
        <div className="flex items-end">
          <button className="btn-primary w-full" disabled={create.isPending}>Criar usuario</button>
        </div>
        {create.error && <div className="alert-error lg:col-span-4">{create.error.message}</div>}
      </form>

      {resetUser && (
        <form className="panel flex flex-col gap-4 md:flex-row md:items-end" onSubmit={(event) => { event.preventDefault(); resetPassword.mutate(); }}>
          <label className="field flex-1" htmlFor="reset-temporary-password">
            Nova senha temporaria para {resetUser.name}
            <input id="reset-temporary-password" required minLength={8} type="password" value={temporaryPassword} onChange={(event) => setTemporaryPassword(event.target.value)} />
          </label>
          <button className="btn-primary" disabled={resetPassword.isPending}>Redefinir</button>
          <button className="btn-ghost" type="button" onClick={() => setResetUser(null)}>Cancelar</button>
          {resetPassword.error && <div className="alert-error">{resetPassword.error.message}</div>}
        </form>
      )}

      <div className="panel">
        <div className="table-header">
          <h2 className="panel-title">Usuarios da empresa</h2>
          {users.isFetching && <span className="text-sm text-muted">Atualizando...</span>}
        </div>
        {users.isError && <div className="alert-error">{users.error.message}</div>}
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Nome</th><th>E-mail</th><th>Perfil</th><th>Status</th><th>Senha</th><th></th></tr>
            </thead>
            <tbody>
              {(users.data ?? []).map((user) => (
                <tr key={user.id}>
                  <td>{user.name}</td>
                  <td>{user.email}</td>
                  <td>{user.role === "company_admin" ?"Administrador" : "Funcionario"}</td>
                  <td>{user.is_active ?"Ativo" : "Bloqueado"}</td>
                  <td>{user.must_change_password ?"Troca pendente" : "Definida"}</td>
                  <td className="text-right">
                    {user.role === "user" && (
                      <div className="inline-flex gap-2">
                        <button className="icon-btn" title="Redefinir senha" onClick={() => setResetUser(user)}>
                          <KeyRound className="h-4 w-4" />
                        </button>
                        <button className="icon-btn" title={user.is_active ?"Bloquear" : "Reativar"} onClick={() => updateStatus.mutate({ id: user.id, is_active: !user.is_active })}>
                          {user.is_active ?<Ban className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
                        </button>
                      </div>
                    )}
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
