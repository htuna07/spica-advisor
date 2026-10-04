import { database } from "@spica-devkit/database";

const DEFAULT_POLICIES = ["64a1f0c2e4b0a1b2c3d4e504"];

function toSpicaUser(legacyUser) {
  return {
    username: legacyUser.login,
    policies: DEFAULT_POLICIES,
    attributes: { legacy_id: legacyUser.id },
  };
}

export async function migrateLegacyUsers() {
  const db = await database();
  const legacyUsers = await db.collection("legacy_users").find({ migrated: { $ne: true } }).toArray();
  if (!legacyUsers.length) {
    return;
  }

  await db.collection("user").insertMany(legacyUsers.map(toSpicaUser));
  await db.collection("legacy_users").updateMany(
    { _id: { $in: legacyUsers.map(user => user._id) } },
    { $set: { migrated: true } }
  );
}
