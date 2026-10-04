import * as Bucket from "@spica-devkit/bucket";

Bucket.initialize({ apikey: process.env.API_KEY });

const SETTINGS_BUCKET = "65b2a1d3f4c5e6a7b8c9d004";

export async function statusCallback(req, res) {
  const settings = await Bucket.data.getAll(SETTINGS_BUCKET, {
    queryParams: { filter: { key: "expected_callback_status" } },
  });
  const expectedStatus = settings[0]?.value;
  console.log("status callback", req.body.status === expectedStatus ? "matched" : "unexpected");
  return res.status(200).send("received");
}

export async function forwardEvent(req, res) {
  await fetch("https://test-spica.example.com/api/fn-execute/echo", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req.body),
  });
  return res.status(202).send({ forwarded: true });
}
