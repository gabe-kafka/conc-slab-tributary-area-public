import { authIsConfigured, getOptionalSession, signIn } from "@/auth";
import { AuthUnavailable } from "@/components/AuthUnavailable";

export default async function SignInPage() {
  if (!authIsConfigured) {
    return <AuthUnavailable title="Login" />;
  }

  const session = await getOptionalSession();

  return (
    <div className="flex-1 flex items-center justify-center p-6">
      <div className="w-full max-w-md border border-border-panel bg-bg-surface p-4 space-y-4">
        <div className="space-y-1">
          <h1 className="text-sm font-semibold text-text-primary">Login</h1>
          <p className="text-[12px] text-text-secondary">
            {session?.user
              ? "You are signed in."
              : "Use your Google account to save and reopen work."}
          </p>
        </div>
        {session?.user ? null : (
          <form
            action={async () => {
              "use server";
              await signIn("google", { redirectTo: "/" });
            }}
          >
            <button
              type="submit"
              className="inline-flex h-7 items-center px-3 border border-border-panel text-[11px] uppercase tracking-wider text-text-secondary hover:text-text-primary hover:border-text-muted transition-colors"
            >
              Login
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
