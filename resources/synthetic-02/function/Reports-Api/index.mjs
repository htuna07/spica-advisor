import * as Bucket from "@spica-devkit/bucket";
import * as Identity from "@spica-devkit/identity";

Bucket.initialize({ apikey: process.env.API_KEY });
Identity.initialize({ apikey: process.env.API_KEY });

const DOWNLOADS_BUCKET = "65b2a1d3f4c5e6a7b8c9d002";
const REPORTS_BUCKET = "65b2a1d3f4c5e6a7b8c9d003";

export async function trackDownload(req, res) {
  await Bucket.data.insert(DOWNLOADS_BUCKET, {
    report: req.query.id,
    downloaded_at: new Date().toISOString(),
  });

  const token = req.headers.authorization;
  if (!token) {
    return res.status(401).send({ message: "Unauthorized" });
  }
  await Identity.verifyToken(token.replace("IDENTITY ", ""));

  const report = await Bucket.data.get(REPORTS_BUCKET, req.query.id);
  return res.status(200).send(report);
}

export function reportHealth(req, res) {
  return res.status(200).send({ status: "ok" });
}
