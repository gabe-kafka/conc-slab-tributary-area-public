import { get } from "@vercel/blob";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const blobUrl = searchParams.get("url");

  if (!blobUrl) {
    return new Response("Missing url parameter", { status: 400 });
  }

  const result = await get(blobUrl, { access: "private" });
  if (!result) {
    return new Response("Not found", { status: 404 });
  }

  return new Response(result.stream, {
    headers: {
      "Content-Type": result.blob.contentType || "application/octet-stream",
      "Content-Disposition":
        result.blob.contentDisposition || "attachment",
    },
  });
}
