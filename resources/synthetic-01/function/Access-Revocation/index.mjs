import * as Auth from "@spica-devkit/auth";
import axios from "axios";

const SUSPENDED_ROLE_POLICY = "64a1f0c2e4b0a1b2c3d4e506";

export async function revokeAccess(req, res) {
  Auth.initialize({ apikey: process.env.API_KEY });

  const { userId } = req.body;
  await Auth.policy.detach(userId, process.env.PARTNER_POLICY_ID);
  await axios.delete(
    `${process.env.__INTERNAL__SPICA__PUBLIC_URL__}/passport/user/${userId}/policy/${SUSPENDED_ROLE_POLICY}`,
    { headers: { Authorization: `APIKEY ${process.env.API_KEY}` } }
  );

  return res.status(200).send({ revoked: userId });
}
