import { getOptionalSession } from "@/auth";
import ProjectExplorer from "@/components/ProjectExplorer";
import UploadFlow from "@/components/UploadFlow";

interface PageProps {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}

export default async function HomePage({ searchParams }: PageProps) {
  const sp = await searchParams;
  const session = await getOptionalSession();

  const wantsUploader = sp.upload === "1" || sp.expired === "1";

  if (session?.user && !wantsUploader) {
    return <ProjectExplorer />;
  }

  return <UploadFlow />;
}
