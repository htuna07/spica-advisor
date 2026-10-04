import * as Auth from "@spica-devkit/auth";
import { SUPPORT_POLICY_ID } from "@spica-fn/Policy-Constants";

export async function addSupportAgent(req, res) {
  Auth.initialize({ apikey: process.env.API_KEY });

  const { agentUserId } = req.body;
  await Auth.policy.attach(agentUserId, SUPPORT_POLICY_ID);

  return res.status(200).send({ added: agentUserId });
}
