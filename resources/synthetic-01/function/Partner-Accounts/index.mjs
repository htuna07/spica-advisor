import { database, ObjectId } from "@spica-devkit/database";

export async function approvePartner(change) {
  const request = change.current;
  if (request.status !== "approved") {
    return;
  }

  const db = await database();
  await db.collection("user").updateOne(
    { _id: new ObjectId(request.user_id) },
    { $set: { policies: [process.env.PARTNER_POLICY_ID] } }
  );
}
