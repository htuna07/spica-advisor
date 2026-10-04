export const SUPPORT_POLICY_ID = "64a1f0c2e4b0a1b2c3d4e503";
export const READONLY_POLICY_ID = "64a1f0c2e4b0a1b2c3d4e510";

export function listPolicies(req, res) {
  return res.status(200).send({ support: SUPPORT_POLICY_ID, readonly: READONLY_POLICY_ID });
}
