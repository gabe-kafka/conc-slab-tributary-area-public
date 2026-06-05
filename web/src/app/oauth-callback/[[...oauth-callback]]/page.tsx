import { redirect } from "next/navigation";

export default function OAuthCallbackRedirectPage() {
  redirect("/sign-in");
}
