import * as Bucket from "@spica-devkit/bucket";
import axios from "axios";

Bucket.initialize({ apikey: process.env.API_KEY });

const FORMS_BUCKET = "65b4a1d3f4c5e6a7b8c9d004";
const VERIFICATION_BUCKET = "65b4a1d3f4c5e6a7b8c9d005";
const PROJECTS_BUCKET = "65b4a1d3f4c5e6a7b8c9d006";

async function verifyCaptcha(response) {
  const { data } = await axios.post("https://www.google.com/recaptcha/api/siteverify", null, {
    params: { secret: process.env.RECAPTCHA_SECRET, response },
  });
  return data.success === true;
}

export async function submitForm(req, res) {
  const { project, values, recaptchaResponse } = req.body;
  if (!(await verifyCaptcha(recaptchaResponse))) {
    return res.status(400).send({ message: "Captcha failed" });
  }
  const form = await Bucket.data.insert(FORMS_BUCKET, { project, values: JSON.stringify(values) });
  return res.status(201).send({ id: form._id });
}

export async function confirmDeletion(req, res) {
  const { email, code, project } = req.query;
  const [verification] = await Bucket.data.getAll(VERIFICATION_BUCKET, {
    queryParams: { filter: { email, code, used: false } },
  });
  if (!verification) {
    return res.status(400).send("This link is invalid or expired.");
  }
  await Bucket.data.patch(VERIFICATION_BUCKET, verification._id, { used: true });
  await Bucket.data.patch(PROJECTS_BUCKET, project, { deleted_at: new Date().toISOString() });
  return res.status(200).send("Your project is deleted.");
}

export async function exportForms(req, res) {
  const forms = await Bucket.data.getAll(FORMS_BUCKET, { queryParams: { filter: { project: req.query.project } } });
  return res.status(200).send(forms);
}

export async function onFormInsert(change) {
  const form = await Bucket.data.get(FORMS_BUCKET, change.current._id, { queryParams: { relation: ["project.owner"] } });
  await axios.post(process.env.MAILER_URL, { to: form.project.owner.email, subject: "New form submission" });
}
