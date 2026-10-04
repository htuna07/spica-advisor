import * as Storage from "@spica-devkit/storage";

Storage.initialize({ apikey: process.env.API_KEY });

export async function uploadAvatar(req, res) {
  const { name, contentType, base64 } = req.body;
  const [object] = await Storage.insertMany([
    { name: `avatars/${name}`, content: { data: Buffer.from(base64, "base64"), type: contentType } },
  ]);
  return res.status(201).send({ url: object.url });
}

export async function removeAvatar(req, res) {
  await Storage.remove(req.query.id);
  return res.status(204).send();
}
