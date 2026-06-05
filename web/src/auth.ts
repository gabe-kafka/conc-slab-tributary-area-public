import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
import NeonAdapter from "@auth/neon-adapter";
import { hasDatabase, pool } from "@/lib/db";

const authSecret = process.env.AUTH_SECRET;
const googleClientId = process.env.AUTH_GOOGLE_ID;
const googleClientSecret = process.env.AUTH_GOOGLE_SECRET;

export const hasAuthSecret = Boolean(authSecret);
export const hasGoogleProvider = Boolean(googleClientId && googleClientSecret);
export const hasAuthDatabase = hasDatabase;
export const authIsConfigured = Boolean(hasAuthSecret && hasGoogleProvider);

export const { handlers, auth, signIn, signOut } = NextAuth({
  adapter: pool ? NeonAdapter(pool) : undefined,
  providers: authIsConfigured
    ? [
        Google({
          clientId: googleClientId!,
          clientSecret: googleClientSecret!,
        }),
      ]
    : [],
  secret: authSecret ?? "login-disabled-development-secret",
  pages: {
    error: "/sign-in",
    signIn: "/sign-in",
  },
  session: {
    strategy: pool ? "database" : "jwt",
  },
  trustHost: true,
});

export async function getOptionalSession() {
  if (!authIsConfigured) {
    return null;
  }

  try {
    return await auth();
  } catch (error) {
    console.error("Auth session lookup failed", error);
    return null;
  }
}
