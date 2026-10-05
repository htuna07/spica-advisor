import * as Bucket from "@spica-devkit/bucket";

Bucket.initialize({ apikey: process.env.API_KEY });

const USERS_BUCKET = "65b4a1d3f4c5e6a7b8c9d001";
const PROJECTS_BUCKET = "65b4a1d3f4c5e6a7b8c9d006";

export async function removeDummyData(req, res) {
  const anonymousUsers = await Bucket.data.getAll(USERS_BUCKET, { queryParams: { filter: { is_anonymous: true } } });
  for (const user of anonymousUsers) {
    const projects = await Bucket.data.getAll(PROJECTS_BUCKET, { queryParams: { filter: { owner: user._id } } });
    await Promise.all(projects.map((project) => Bucket.data.remove(PROJECTS_BUCKET, project._id)));
    await Bucket.data.remove(USERS_BUCKET, user._id);
  }
  return res.status(200).send({ removed: anonymousUsers.length });
}

export function health(req, res) {
  return res.status(200).send("OK");
}
