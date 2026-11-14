import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Eye, EyeOff, Loader2 } from "lucide-react";
import { api } from "../lib/api";
import { useSession } from "../store/session";
import type { User } from "../lib/types";
import { BhuShaktiLogo, BhuShaktiLogoMark } from "../components/BhuShaktiLogo";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});
type FormValues = z.infer<typeof schema>;

interface LoginResponse {
  token: string;
  user: User;
  permissions: string[];
  expires_at: string;
}

export default function Login() {
  const navigate = useNavigate();
  const setSession = useSession((s) => s.setSession);
  const [error, setError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const { register, handleSubmit, setValue, formState } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
  });

  const accounts = useQuery({
    queryKey: ["demo-accounts"],
    queryFn: () => api<{ mode: string; accounts: Array<{ email: string; role: string }> }>("/api/v1/auth/demo-accounts"),
    retry: false,
  });

  const onSubmit = async (values: FormValues) => {
    setError(null);
    try {
      const result = await api<LoginResponse>("/api/v1/auth/login", { method: "POST", json: values });
      setSession(result.token, result.user, result.permissions);
      if (result.user.role === "citizen") {
        navigate("/citizen", { replace: true });
      } else {
        navigate("/", { replace: true });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed");
    }
  };

  return (
    <div className="grid min-h-full lg:grid-cols-[1.05fr_1fr]">
      <section className="relative hidden flex-col justify-between overflow-hidden bg-forest px-10 py-9 text-white lg:flex">
        <div className="absolute inset-0 opacity-[0.18]" aria-hidden>
          <svg viewBox="0 0 600 600" className="h-full w-full" preserveAspectRatio="xMidYMid slice">
            <path d="M0 470 L130 250 L215 380 L300 190 L420 400 L520 280 L600 430 L600 600 L0 600Z" fill="#ffffff" />
            <path d="M0 520 L120 340 L210 450 L330 270 L430 470 L540 350 L600 470 L600 600 L0 600Z" fill="#ffffff" opacity="0.6" />
          </svg>
        </div>
        <div className="relative">
          <div className="flex items-center gap-3">
            <BhuShaktiLogoMark size={44} className="shadow-lg shadow-black/20" />
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xl font-bold tracking-tight text-white">BHUSHAKTI</span>
                <span className="bg-white/20 border border-white/30 text-white text-[10px] font-black px-1.5 py-0.5 rounded-md tracking-wider">AI</span>
              </div>
              <div className="text-2xs uppercase tracking-[0.16em] text-white/70">North Eastern Region · India</div>
            </div>
          </div>
        </div>
        <div className="relative max-w-xl">
          <h1 className="text-3xl font-semibold leading-tight">
            We do not just identify where landslide risk exists.
          </h1>
          <p className="mt-3 text-sm leading-relaxed text-white/75">
            We explain why it is increasing, determine what is exposed, and help authorities decide where to
            act first.
          </p>
          <dl className="mt-7 grid gap-3 text-sm sm:grid-cols-2">
            {[
              ["SENSE", "Live rainfall, soil moisture and DEM terrain"],
              ["PREDICT", "Susceptibility + rainfall trigger, never a fake probability"],
              ["EXPLAIN", "Signed drivers with data provenance"],
              ["ACT", "Human-approved alerts, response and offline field reports"],
            ].map(([key, text]) => (
              <div key={key} className="rounded-lg border border-white/12 bg-white/5 px-3 py-2">
                <dt className="text-2xs font-semibold uppercase tracking-[0.14em] text-white/55">{key}</dt>
                <dd className="mt-0.5 text-xs leading-relaxed text-white/85">{text}</dd>
              </div>
            ))}
          </dl>
        </div>
        <p className="relative text-2xs leading-relaxed text-white/50">
          Decision support only. Hazard scores are uncalibrated prototype indices, not official warnings or
          predictions of a specific landslide.
        </p>
      </section>

      <section className="flex items-center justify-center px-4 py-8 sm:px-8">
        <div className="w-full max-w-md">
          <div className="mb-6 lg:hidden">
            <BhuShaktiLogo size={36} />
          </div>
          <h2 className="text-xl font-semibold">Authority sign-in</h2>
          <p className="mt-1 text-sm text-muted">Use your departmental account. District accounts see only their district.</p>

          <form className="mt-6 space-y-3" onSubmit={handleSubmit(onSubmit)} noValidate>
            <div>
              <label className="label" htmlFor="email">Official email</label>
              <input id="email" className="input" type="email" autoComplete="username" {...register("email")} aria-invalid={!!formState.errors.email} />
              {formState.errors.email ? <p className="mt-1 text-2xs text-critical">{formState.errors.email.message}</p> : null}
            </div>
            <div>
              <label className="label" htmlFor="password">Password</label>
              <div className="relative">
                <input id="password" className="input pr-10" type={showPassword ? "text" : "password"} autoComplete="current-password" {...register("password")} aria-invalid={!!formState.errors.password} />
                <button type="button" className="absolute inset-y-0 right-0 px-2 text-muted" onClick={() => setShowPassword((v) => !v)} aria-label={showPassword ? "Hide password" : "Show password"}>
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {formState.errors.password ? <p className="mt-1 text-2xs text-critical">{formState.errors.password.message}</p> : null}
            </div>
            {error ? <div role="alert" className="rounded-lg border border-critical/40 bg-critical/5 px-3 py-2 text-xs text-critical">{error}</div> : null}
            <button type="submit" className="btn btn-primary btn-lg w-full" disabled={formState.isSubmitting}>
              {formState.isSubmitting ? <Loader2 size={16} className="animate-spin" /> : null}
              Sign in <ArrowRight size={16} />
            </button>
          </form>

          {accounts.data ? (
            <div className="mt-7 rounded-xl border border-line bg-surface p-3">
              <div className="text-2xs font-semibold uppercase tracking-wide text-muted">Demonstration accounts</div>
              <p className="mt-1 text-2xs text-muted">Password: <span className="mono">BhuShakti#2026</span></p>
              <div className="mt-2 max-h-44 space-y-1 overflow-y-auto">
                {accounts.data.accounts.map((account) => (
                  <button
                    key={account.email}
                    type="button"
                    className="flex w-full items-center justify-between rounded-md border border-line bg-canvas px-2 py-1.5 text-left text-xs hover:bg-surface-2"
                    onClick={() => { setValue("email", account.email); setValue("password", "BhuShakti#2026"); }}
                  >
                    <span className="truncate">{account.email}</span>
                    <span className="ml-2 shrink-0 text-2xs text-muted">{account.role}</span>
                  </button>
                ))}
              </div>
              <p className="mt-2 text-2xs text-muted">Seeded demo accounts only; production uses departmental SSO.</p>
            </div>
          ) : null}

          <div className="mt-6 flex items-center justify-between text-xs">
            <Link to="/citizen" className="text-subtle underline-offset-2 hover:underline">Citizen risk check (no sign-in)</Link>
            <span className="text-muted">v0.9.0</span>
          </div>
        </div>
      </section>
    </div>
  );
}
