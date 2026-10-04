import * as Bucket from "@spica-devkit/bucket";
import * as Identity from "@spica-devkit/identity";

Bucket.initialize({ apikey: process.env.API_KEY });
Identity.initialize({ apikey: process.env.API_KEY });

const CACHE_BUCKET = "65b2a1d3f4c5e6a7b8c9d006";

async function authenticate(req) {
  const token = (req.headers.authorization || "").replace("IDENTITY ", "");
  return Identity.verifyToken(token);
}

export async function purgeCache(req, res) {
  if (req.headers.authorization !== `APIKEY ${process.env.ADMIN_API_KEY}`) {
    return res.status(401).send({ message: "Unauthorized" });
  }
  const entries = await Bucket.data.getAll(CACHE_BUCKET);
  await Promise.all(entries.map(entry => Bucket.data.remove(CACHE_BUCKET, entry._id)));
  return res.status(200).send({ purged: entries.length });
}

export async function deleteUser(req, res) {
  const identity = await authenticate(req);
  if (identity.attributes?.role !== "admin") {
    return res.status(403).send({ message: "Forbidden" });
  }
  await Identity.remove(req.body.identityId);
  return res.status(204).send();
}
