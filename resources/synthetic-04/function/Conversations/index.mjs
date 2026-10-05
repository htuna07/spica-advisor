import * as Bucket from "@spica-devkit/bucket";
import * as Identity from "@spica-devkit/identity";

Bucket.initialize({ apikey: process.env.API_KEY });
Identity.initialize({ apikey: process.env.API_KEY });

const CONVERSATIONS_BUCKET = "65b4a1d3f4c5e6a7b8c9d003";

function log(event, details) {
  console.log(JSON.stringify({ event, ...details, at: new Date().toISOString() }));
}

async function authenticate(req) {
  const header = req.headers.authorization || "";
  if (!header.startsWith("IDENTITY ")) return null;
  return Identity.verifyToken(header.replace("IDENTITY ", "")).catch(() => null);
}

export async function getConversation(req, res) {
  const id = req.query.id;
  log("getConversation:enter", { id });
  const identity = await authenticate(req);
  if (!identity) {
    return res.status(401).send({ message: "Unauthorized" });
  }
  const conversation = await Bucket.data.get(CONVERSATIONS_BUCKET, id);
  if (!conversation || conversation.owner !== identity._id) {
    return res.status(404).send({ message: "Not found" });
  }
  return res.status(200).send(conversation);
}

export async function resumeConversation(req, res) {
  const bodyId = req.body && (req.body.id || req.body.conversation_id);
  if (bodyId && !req.query.id) {
    req.query = { ...req.query, id: bodyId };
  }
  return getConversation(req, res);
}

export async function chat(req, res) {
  const body = req.body || {};
  log("chat:enter", { messages: (body.messages || []).length, confirmed: (body.confirmed || []).length });
  const identity = await authenticate(req);
  if (!identity) {
    return res.status(401).send({ message: "Unauthorized" });
  }
  const conversation = await Bucket.data.insert(CONVERSATIONS_BUCKET, {
    owner: identity._id,
    messages: body.messages || [],
    confirmed: body.confirmed || [],
  });
  return res.status(200).send(conversation);
}

export async function confirmAction(req, res) {
  const { action_id, ...rest } = req.body || {};
  if (!action_id) {
    return res.status(400).send({ message: "action_id is required" });
  }
  const forwarded = { ...req, body: { ...rest, confirmed: [...(rest.confirmed || []), action_id] } };
  return chat(forwarded, res);
}

export async function purgeConversations() {
  const cutoff = new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString();
  const old = await Bucket.data.getAll(CONVERSATIONS_BUCKET, { queryParams: { filter: { created_at: { $lt: cutoff } } } });
  await Promise.all(old.map((conversation) => Bucket.data.remove(CONVERSATIONS_BUCKET, conversation._id)));
}
