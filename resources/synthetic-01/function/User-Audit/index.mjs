import { database } from "@spica-devkit/database";

export async function auditPrivilegedUsers() {
  const db = await database();
  const admins = await db.collection("user").find({ policies: "64a1f0c2e4b0a1b2c3d4e502" }).toArray();

  for (const admin of admins) {
    // await Auth.policy.attach(admin._id, "64a1f0c2e4b0a1b2c3d4e509");
    await db.collection("audit_log").insertOne({ user: admin._id, checked_at: new Date() });
  }
}
