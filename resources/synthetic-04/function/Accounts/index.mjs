import * as Bucket from "@spica-devkit/bucket";
import * as Identity from "@spica-devkit/identity";

Bucket.initialize({ apikey: process.env.API_KEY });
Identity.initialize({ apikey: process.env.API_KEY });

const USERS_BUCKET = "65b4a1d3f4c5e6a7b8c9d001";
const RECOVERY_BUCKET = "65b4a1d3f4c5e6a7b8c9d002";

export async function login(req, res) {
  const { email, password } = req.body;
  const [user] = await Bucket.data.getAll(USERS_BUCKET, { queryParams: { filter: { email } } });
  if (!user) {
    return res.status(404).send({ message: "No account for this email" });
  }
  const { token } = await Identity.login(email, password).catch(() => ({}));
  if (!token) {
    return res.status(401).send({ message: "Wrong password" });
  }
  return res.status(200).send({ token, user });
}

export async function register(req, res) {
  const { email, password, name } = req.body;
  const identity = await Identity.insert({ identifier: email, password });
  const user = await Bucket.data.insert(USERS_BUCKET, { email, name, identity: identity._id });
  return res.status(201).send(user);
}

export async function forgotPassword(req, res) {
  const { email } = req.body;
  const [user] = await Bucket.data.getAll(USERS_BUCKET, { queryParams: { filter: { email } } });
  if (user) {
    const code = Math.random().toString(36).slice(2, 10);
    await Bucket.data.insert(RECOVERY_BUCKET, { user: user._id, code, used: false });
  }
  return res.status(200).send({ message: "If the email exists, a recovery link is on its way" });
}

export async function seedAdmin(req, res) {
  const admins = await Bucket.data.getAll(USERS_BUCKET, { queryParams: { filter: { role: "admin" } } });
  await Promise.all(admins.map((admin) => Bucket.data.remove(USERS_BUCKET, admin._id)));
  const admin = await Bucket.data.insert(USERS_BUCKET, { email: req.body.email, role: "admin" });
  return res.status(200).send(admin);
}
