import * as Bucket from "@spica-devkit/bucket";
import * as Identity from "@spica-devkit/identity";

Bucket.initialize({ apikey: process.env.API_KEY });
Identity.initialize({ apikey: process.env.API_KEY });

const INVITATIONS_BUCKET = "65b4a1d3f4c5e6a7b8c9d007";

async function decodeToken(req) {
  const token = (req.headers.authorization || "").replace("IDENTITY ", "");
  const identity = await Identity.verifyToken(token).catch(() => null);
  if (!identity) {
    throw Object.assign(new Error("Unauthorized"), { status: 401 });
  }
  return identity;
}

export async function revoke(req, res) {
  try {
    const identity = await decodeToken(req);
    const invitation = await Bucket.data.get(INVITATIONS_BUCKET, req.query.id);
    if (!invitation || invitation.inviter !== identity._id) {
      return res.status(404).send({ message: "Invitation not found" });
    }
    await Bucket.data.patch(INVITATIONS_BUCKET, invitation._id, { status: "revoked" });
    return res.status(200).send({ revoked: true });
  } catch (error) {
    return res.status(error.status || 500).send({ message: error.message });
  }
}

export async function revokeV1(req, res) {
  return revoke(req, res);
}
