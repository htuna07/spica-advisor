const TAX_RATE = 0.2;

export function quote(req, res) {
  const { basePrice, quantity, discountPercent = 0 } = req.body;
  const subtotal = basePrice * quantity;
  const discounted = subtotal * (1 - discountPercent / 100);
  const total = Math.round(discounted * (1 + TAX_RATE) * 100) / 100;
  return res.status(200).send({ total });
}

export function validateCoupon(req, res) {
  const code = String(req.query.code || "");
  const valid = /^[A-Z]{4}-\d{4}$/.test(code);
  return res.status(200).send({ valid });
}

export function ping(req, res) {
  return res.status(200).send("pong");
}
