import axios from "axios";

const PASSPORT_URL = `${process.env.__INTERNAL__SPICA__PUBLIC_URL__}/passport`;
const ADMIN_POLICY = "64a1f0c2e4b0a1b2c3d4e502";

export async function promoteToAdmin(req, res) {
  const { userId } = req.body;

  await axios.post(
    `${PASSPORT_URL}/user/${userId}/policy/${ADMIN_POLICY}`,
    {},
    { headers: { Authorization: `APIKEY ${process.env.ADMIN_API_KEY}` } }
  );

  return res.status(200).send({ promoted: userId });
}
