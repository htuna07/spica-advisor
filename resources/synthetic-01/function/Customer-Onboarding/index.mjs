import * as Auth from "@spica-devkit/auth";
import * as Bucket from "@spica-devkit/bucket";

const CUSTOMER_POLICY = "64a1f0c2e4b0a1b2c3d4e501";
const CUSTOMERS_BUCKET = "64a1f0c2e4b0a1b2c3d4e601";

export async function onboardCustomer(req, res) {
  Auth.initialize({ apikey: process.env.API_KEY });
  Bucket.initialize({ apikey: process.env.API_KEY });

  const { username, password, email } = req.body;
  const user = await Auth.user.insert({ username, password });
  await Auth.policy.attach(user._id, CUSTOMER_POLICY);
  await Bucket.data.insert(CUSTOMERS_BUCKET, { user: user._id, email });

  return res.status(201).send({ user: user._id });
}
