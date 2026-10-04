import { database, ObjectId } from "@spica-devkit/database";

export async function setTeamPolicies(req, res) {
  const db = await database();

  await db.collection("teams").updateOne(
    { _id: new ObjectId(req.body.teamId) },
    { $set: { policies: ["64a1f0c2e4b0a1b2c3d4e507"] } }
  );

  return res.status(200).send({ ok: true });
}
