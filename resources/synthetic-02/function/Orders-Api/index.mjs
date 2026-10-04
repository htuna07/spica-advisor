import * as Bucket from "@spica-devkit/bucket";
import * as Identity from "@spica-devkit/identity";

Bucket.initialize({ apikey: process.env.API_KEY });
Identity.initialize({ apikey: process.env.API_KEY });

const ORDERS_BUCKET = "65b2a1d3f4c5e6a7b8c9d001";

async function assertAuthorized(req) {
  const token = (req.headers.authorization || "").replace("IDENTITY ", "");
  return Identity.verifyToken(token);
}

export function calculateTotal(items) {
  return items.reduce((total, item) => total + item.price * item.quantity, 0);
}

export async function createOrder(req, res) {
  const { items, address } = req.body;
  const order = await Bucket.data.insert(ORDERS_BUCKET, {
    items,
    address,
    total: calculateTotal(items),
    status: "pending",
  });
  return res.status(201).send(order);
}

export async function getOrder(req, res) {
  const token = req.headers.authorization;
  if (!token) {
    return res.status(401).send({ message: "Unauthorized" });
  }
  const identity = await Identity.verifyToken(token.replace("IDENTITY ", ""));

  const order = await Bucket.data.get(ORDERS_BUCKET, req.query.id);
  if (order.owner !== identity._id) {
    return res.status(403).send({ message: "Forbidden" });
  }
  return res.status(200).send(order);
}

export async function cancelOrder(req, res) {
  await assertAuthorized(req);
  await Bucket.data.patch(ORDERS_BUCKET, req.body.id, { status: "cancelled" });
  return res.status(200).send({ cancelled: req.body.id });
}
