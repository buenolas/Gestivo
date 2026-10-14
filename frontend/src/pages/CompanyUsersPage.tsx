import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Ban, CheckCircle2, KeyRound, Mail } from "lucide-react";
import { apiFetch } from "../api";
import type { CompanyUser } from "../types";

export function CompanyUsersPage() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ name: "", email: "" });
  const [resetUser, setResetUser] = useState<CompanyUser | null>(null);
  const [temporaryPassword, setTemporaryPassword] = useState("");
  const [invitationNotice, setInvitationNotice] = useState("");

  const users = useQuery({
    queryKey: ["company-users"],
    queryFn: () => apiFetch<CompanyUser[]>("/company-users"),
  });

  const create = useMutation({
    mutationFn: () =>
      apiFetch<CompanyUser>("/company-users", {
        method: "POST",
        body: JSON.stringify({ name: form.name, email: form.email }),
      }),
    onSuccess: async (user) => {
      setForm({ name: "", email: "" });
      setInvitationNotice(`Convite enviado para ${user.email}. O acesso será liberado depois da confirmação do e-mail e da criação de uma senha.`);
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["company-users"] }),
  });

  const resendInvitation = useMutation({
    mutationFn: (userId: string) =>
      apiFetch<{ message: string }>(`/company-users/${userId}/resend-invitation`, { method: "POST" }),
    onSuccess: async (response) => {
      setInvitationNotice(response.message);
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
          <h2 className="panel-title">Convidar usuário</h2>
          <p className="section-subtitle">
            Acesso limitado a lançamentos, categorias e contatos. Enviaremos um link para confirmar o e-mail e criar uma senha; o acesso só será ativado depois dessa confirmação.
          </p>
        </div>
        <label className="field" htmlFor="company-user-name">
          Nome
          <input id="company-user-name" required minLength={2} value={form.name} onChange={(event) => { setInvitationNotice(""); setForm({ ...form, name: event.target.value }); }} />
        </label>
        <label className="field" htmlFor="company-user-email">
          E-mail
          <input id="company-user-email" required type="email" value={form.email} onChange={(event) => { setInvitationNotice(""); setForm({ ...form, email: event.target.value }); }} />
        </label>
        <div className="flex items-end">
          <button className="btn-primary w-full" disabled={create.isPending}>{create.isPending ? "Enviando convite..." : "Enviar convite"}</button>
        </div>
        {create.error && <div className="alert-error lg:col-span-4">{create.error.message}</div>}
        {invitationNotice && <div className="lg:col-span-4 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-800" role="status">{invitationNotice}</div>}
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
        {resendInvitation.error && <div className="alert-error">{resendInvitation.error.message}</div>}
        <div className="table-wrap responsive-cards">
          <table aria-label="Usuários da empresa">
            <thead className="sr-only sm:not-sr-only">
              <tr>
                <th scope="col">Nome</th>
                <th scope="col">E-mail</th>
                <th scope="col">Perfil</th>
                <th scope="col">Status</th>
                <th scope="col">Senha</th>
                <th scope="col">Ações</th>
              </tr>
            </thead>
            <tbody>
              {(users.data ?? []).map((user) => (
                <tr key={user.id}>
                  <td data-label="Nome" data-primary="true">{user.name}</td>
                  <td data-label="E-mail">{user.email}</td>
                  <td data-label="Perfil">{user.role === "company_admin" ?"Administrador" : "Funcionário"}</td>
                  <td data-label="Status">{!user.email_verified_at ?"Aguardando confirmação" : user.is_active ?"Ativo" : "Bloqueado"}</td>
                  <td data-label="Senha">{!user.email_verified_at ?"Definida ao aceitar convite" : user.must_change_password ?"Troca pendente" : "Definida"}</td>
                  <td data-actions className="text-right">
                    {user.role === "user" && (
                      <div className="inline-flex gap-2">
                        {!user.email_verified_at ? (
                          <button className="icon-btn" type="button" title="Reenviar convite" aria-label={`Reenviar convite para ${user.email}`} disabled={resendInvitation.isPending} onClick={() => { setInvitationNotice(""); resendInvitation.mutate(user.id); }}>
                            <Mail className="h-4 w-4" />
                          </button>
                        ) : (
                          <>
                            <button className="icon-btn" type="button" title="Redefinir senha" aria-label={`Redefinir senha de ${user.name}`} onClick={() => setResetUser(user)}>
                              <KeyRound className="h-4 w-4" />
                            </button>
                            <button className="icon-btn" type="button" title={user.is_active ?"Bloquear usuário" : "Reativar usuário"} aria-label={`${user.is_active ?"Bloquear" : "Reativar"} usuário: ${user.name}`} onClick={() => updateStatus.mutate({ id: user.id, is_active: !user.is_active })}>
                              {user.is_active ?<Ban className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
                            </button>
                          </>
                        )}
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
