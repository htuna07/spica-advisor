import * as Bucket from "@spica-devkit/bucket";

Bucket.initialize({ apikey: process.env.API_KEY });

const SCORES_BUCKET = "65b2a1d3f4c5e6a7b8c9d005";

export function rankOf(score, scores) {
  return scores.filter(other => other > score).length + 1;
}

export async function getLeaderboard(req, res) {
  const scores = await Bucket.data.getAll(SCORES_BUCKET, {
    queryParams: { sort: { points: -1 }, limit: 50 },
  });
  return res.status(200).send(scores.map(entry => ({ player: entry.player, points: entry.points })));
}

export async function recalculate() {
  const scores = await Bucket.data.getAll(SCORES_BUCKET);
  const points = scores.map(entry => entry.points);
  for (const entry of scores) {
    await Bucket.data.patch(SCORES_BUCKET, entry._id, { rank: rankOf(entry.points, points) });
  }
}
