import Link from "next/link";

type AuthUnavailableProps = {
  title: string;
};

export function AuthUnavailable({ title }: AuthUnavailableProps) {
  return (
    <div className="flex-1 flex items-center justify-center p-6">
      <div className="w-full max-w-md border border-border-panel bg-bg-surface p-4 space-y-3">
        <h1 className="text-sm font-semibold text-text-primary">{title}</h1>
        <p className="text-[12px] text-text-secondary">
          Login is not configured for this deployment yet.
        </p>
        <Link
          href="/"
          className="inline-flex h-7 items-center px-3 border border-border-panel text-[11px] uppercase tracking-wider text-text-secondary hover:text-text-primary hover:border-text-muted transition-colors"
        >
          Back
        </Link>
      </div>
    </div>
  );
}
