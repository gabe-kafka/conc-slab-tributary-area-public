import { redirect } from "next/navigation";

export default function SsoCallbackPage() {
  redirect("/sign-in");
}
