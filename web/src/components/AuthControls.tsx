import Link from "next/link";
import { authIsConfigured, getOptionalSession, signIn, signOut } from "@/auth";

export async function AuthControls() {
  if (!authIsConfigured) {
    return (
      <Link
        href="/sign-in"
        className="h-5 px-2 inline-flex items-center border border-border-panel text-[10px] uppercase tracking-wider text-text-muted"
        title="Set Auth.js Google environment variables to enable login."
      >
        Login
      </Link>
    );
  }

  const session = await getOptionalSession();

  if (session?.user) {
    return (
      <form
        action={async () => {
          "use server";
          await signOut({ redirectTo: "/" });
        }}
        className="h-5 flex items-center"
      >
        <button
          type="submit"
          className="h-5 px-2 border border-border-panel text-[10px] uppercase tracking-wider text-text-secondary hover:text-text-primary hover:border-text-muted transition-colors"
        >
          Logout
        </button>
      </form>
    );
  }

  return (
    <form
      action={async () => {
        "use server";
        await signIn("google", { redirectTo: "/" });
      }}
      className="h-5 flex items-center"
    >
      <button
        type="submit"
        className="h-5 px-2 border border-border-panel text-[10px] uppercase tracking-wider text-text-secondary hover:text-text-primary hover:border-text-muted transition-colors"
      >
        Login
      </button>
    </form>
  );
}
