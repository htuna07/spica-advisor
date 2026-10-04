const VENDOR_REQUESTS_BUCKET = "64a1f0c2e4b0a1b2c3d4e602";

async function fetchApprovedVendors(baseUrl) {
  const filter = encodeURIComponent(JSON.stringify({ status: "approved", synced: false }));
  const response = await fetch(`${baseUrl}/bucket/${VENDOR_REQUESTS_BUCKET}/data?filter=${filter}`, {
    headers: { Authorization: `APIKEY ${process.env.API_KEY}` },
  });
  return response.json();
}

export async function syncVendors() {
  const baseUrl = process.env.__INTERNAL__SPICA__PUBLIC_URL__;
  const vendors = await fetchApprovedVendors(baseUrl);

  for (const vendor of vendors) {
    await fetch(`${baseUrl}/passport/user/${vendor.user_id}/policy/${process.env.VENDOR_POLICY_ID}`, {
      method: "POST",
      headers: { Authorization: `APIKEY ${process.env.API_KEY}` },
    });
  }
}
