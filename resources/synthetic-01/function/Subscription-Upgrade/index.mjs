import { database, ObjectId } from "@spica-devkit/database";

const BASIC_POLICY_ID = "64a1f0c2e4b0a1b2c3d4e505";

export async function upgradeSubscription(req, res) {
  const db = await database();
  const { userIds } = req.body;

  await db.collection("user").updateMany(
    { _id: { $in: userIds.map(id => new ObjectId(id)) } },
    { $set: { policies: [BASIC_POLICY_ID, process.env.PREMIUM_POLICY_ID] } }
  );

  return res.status(200).send({ upgraded: userIds.length });
}
